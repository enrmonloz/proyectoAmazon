"""Tests de la capa de localizacion continua y comparacion de candidatos.

Uso: ``python tests/test_location_solver.py``
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.data_loader import DEPOT_NAME, SECONDARY_HUB_NAME, load_dataset
from src.location_solver import (
    CandidateType,
    DISTANCE_SOURCE_GEOMETRIC,
    DISTANCE_SOURCE_OD,
    LocationMethod,
    LocationEvaluationMode,
    LocationSolver,
    TIME_SOURCE_UNAVAILABLE,
    TIME_SOURCE_OD,
    build_auto_location_candidates,
    build_full_location_comparison,
    select_auto_new_location,
)


DATA_DIR = ROOT / "data"


def _load_dataset_once():
    return load_dataset(
        poblacion_path=str(DATA_DIR / "poblacion.csv"),
        rutas_path=str(DATA_DIR / "rutasDistTiempo.csv"),
    )


def _solver_and_candidates():
    ds = _load_dataset_once()
    solver = LocationSolver(ds)
    method_result = solver.solve(LocationMethod.MIN_TOTAL_DISTANCE)
    candidates = solver.build_default_candidates(method_result)
    return ds, solver, method_result, candidates


def _assert_raises_contains(fn, expected_text: str) -> None:
    try:
        fn()
    except ValueError as exc:
        if expected_text not in str(exc):
            raise AssertionError(
                f"Error inesperado. Esperado texto '{expected_text}', obtenido: {exc}"
            )
        print(f"  OK error esperado: {expected_text}")
        return
    raise AssertionError(f"Deberia fallar con: {expected_text}")


def test_default_candidates_are_built() -> None:
    print("test_default_candidates_are_built")
    _, _, _, candidates = _solver_and_candidates()

    names = {candidate.name for candidate in candidates}
    if DEPOT_NAME not in names:
        raise AssertionError("SVQ1 debe aparecer como candidato existente")
    if SECONDARY_HUB_NAME not in names:
        raise AssertionError("DQA4 debe aparecer como referencia operativa")

    by_type = {candidate.candidate_type: candidate for candidate in candidates}
    for expected_type in (
        CandidateType.EXISTING_HUB,
        CandidateType.OPERATIONAL_REFERENCE,
        CandidateType.MATHEMATICAL_REFERENCE,
        CandidateType.HEURISTIC_INTERMEDIATE,
    ):
        if expected_type not in by_type:
            raise AssertionError(f"Falta candidato de tipo {expected_type.value}")

    if by_type[CandidateType.MATHEMATICAL_REFERENCE].node_index is not None:
        raise AssertionError("El optimo continuo no debe tener node_index")
    if DEPOT_NAME in names and SECONDARY_HUB_NAME in names:
        if by_type[CandidateType.HEURISTIC_INTERMEDIATE].node_index is not None:
            raise AssertionError(
                "El candidato intermedio debe ser el punto medio sin node_index cuando SVQ1 y DQA4 existen"
            )
    elif by_type[CandidateType.HEURISTIC_INTERMEDIATE].node_index is None:
        raise AssertionError("El candidato intermedio debe proyectarse a un nodo de demanda")
    if "referencia operativa" not in by_type[CandidateType.OPERATIONAL_REFERENCE].description.lower():
        raise AssertionError("DQA4 debe documentarse como referencia operativa")
    print("  OK candidatos base construidos")


def test_candidate_evaluation_metrics_are_sortable() -> None:
    print("test_candidate_evaluation_metrics_are_sortable")
    _, solver, _, candidates = _solver_and_candidates()

    comparison = solver.evaluate_candidates(candidates)
    if len(comparison.evaluations) != len(candidates):
        raise AssertionError("Debe evaluarse cada candidato recibido")

    for evaluation in comparison.evaluations:
        if evaluation.weighted_mean_distance_km <= 0:
            raise AssertionError("La distancia media ponderada debe ser positiva")
        if evaluation.weighted_total_distance_km <= 0:
            raise AssertionError("La distancia total ponderada debe ser positiva")
        if evaluation.max_distance_km <= 0:
            raise AssertionError("La distancia maxima debe ser positiva")

    ordered = sorted(
        comparison.evaluations,
        key=lambda item: item.weighted_mean_distance_km,
    )
    if comparison.best_by_distance != ordered[0]:
        raise AssertionError("best_by_distance debe coincidir con la evaluacion ordenada")
    if comparison.best_by_time is not None:
        raise AssertionError("El modo geometrico no debe exponer mejor candidato por tiempo")
    print("  OK metricas calculadas y ordenables")


def test_weights_validation_and_defaults() -> None:
    print("test_weights_validation_and_defaults")
    ds, solver, _, candidates = _solver_and_candidates()

    default_result = solver.evaluate_candidates(candidates)
    explicit_population = solver.evaluate_candidates(candidates, weights=ds.poblacion)
    for default_eval, explicit_eval in zip(
        default_result.evaluations,
        explicit_population.evaluations,
    ):
        if abs(default_eval.weighted_mean_distance_km - explicit_eval.weighted_mean_distance_km) > 1e-9:
            raise AssertionError("Los pesos por defecto deben coincidir con la poblacion")

    demand_weights = np.ones(int(np.count_nonzero(ds.poblacion > 0)))
    custom_result = solver.evaluate_candidates(candidates, weights=demand_weights)
    if len(custom_result.evaluations) != len(candidates):
        raise AssertionError("Los pesos externos por demanda deben funcionar")

    _assert_raises_contains(
        lambda: solver.evaluate_candidates(candidates, weights=np.ones(3)),
        "longitud compatible",
    )

    negative_weights = ds.poblacion.astype(float)
    negative_weights[np.where(ds.poblacion > 0)[0][0]] = -1.0
    _assert_raises_contains(
        lambda: solver.evaluate_candidates(candidates, weights=negative_weights),
        "no negativos",
    )
    print("  OK validacion de pesos")


def test_auto_new_location_uses_all_methods_and_references() -> None:
    print("test_auto_new_location_uses_all_methods_and_references")
    ds = _load_dataset_once()
    selection = select_auto_new_location(ds)

    if len(selection.method_results) != len(LocationMethod):
        raise AssertionError("Debe calcular todos los metodos de localizacion")

    candidates = build_auto_location_candidates(ds, selection.method_results)
    names = {candidate.name for candidate in candidates}
    if DEPOT_NAME not in names or SECONDARY_HUB_NAME not in names:
        raise AssertionError("La seleccion automatica debe comparar SVQ1 y DQA4")
    if f"Punto medio {DEPOT_NAME}-{SECONDARY_HUB_NAME}" not in names:
        raise AssertionError("La seleccion automatica debe incluir el punto medio")

    continuous_count = sum(
        1
        for candidate in candidates
        if candidate.candidate_type == CandidateType.MATHEMATICAL_REFERENCE
    )
    if continuous_count != len(LocationMethod):
        raise AssertionError("Debe haber una referencia continua por metodo")

    ordered = sorted(
        selection.comparison.evaluations,
        key=lambda item: (
            item.weighted_mean_distance_km,
            item.max_distance_km,
            item.candidate.name,
        ),
    )
    if selection.selected != ordered[0]:
        raise AssertionError("La nueva ubicacion debe ser el mejor candidato por distancia")
    print("  OK seleccion automatica completa y determinista")


def test_continuous_candidate_uses_geometric_without_time() -> None:
    print("test_continuous_candidate_uses_geometric_without_time")
    _, solver, _, candidates = _solver_and_candidates()
    continuous = [
        candidate
        for candidate in candidates
        if candidate.candidate_type == CandidateType.MATHEMATICAL_REFERENCE
    ][0]

    comparison = solver.evaluate_candidates([continuous])
    evaluation = comparison.evaluations[0]
    if evaluation.distance_source != DISTANCE_SOURCE_GEOMETRIC:
        raise AssertionError("El candidato continuo debe usar distancia geometrica comun")
    if evaluation.weighted_mean_time_min is not None or evaluation.max_time_min is not None:
        raise AssertionError("El candidato continuo no debe tener tiempo OD")
    if evaluation.time_source != TIME_SOURCE_UNAVAILABLE:
        raise AssertionError("El tiempo del candidato continuo debe marcarse no disponible")
    if "Modo geometrico" not in evaluation.notes:
        raise AssertionError("Debe explicar que la evaluacion usa modo geometrico")
    print("  OK candidato continuo evaluado con geometria comun")


def test_default_evaluation_is_geometric_only() -> None:
    print("test_default_evaluation_is_geometric_only")
    _, solver, _, candidates = _solver_and_candidates()
    comparison = solver.evaluate_candidates(candidates)
    for evaluation in comparison.evaluations:
        if evaluation.distance_source != DISTANCE_SOURCE_GEOMETRIC:
            raise AssertionError("El modo por defecto debe usar distancia geometrica")
        if evaluation.time_source != TIME_SOURCE_UNAVAILABLE:
            raise AssertionError("El modo por defecto no debe usar tiempos OD")
    print("  OK modo por defecto geometrico")


def test_od_matrix_mode_is_explicit() -> None:
    print("test_od_matrix_mode_is_explicit")
    _, solver, _, candidates = _solver_and_candidates()
    comparison = solver.evaluate_candidates(
        candidates,
        mode=LocationEvaluationMode.OD_MATRIX,
    )
    existing = next(
        item for item in comparison.evaluations if item.candidate.name == DEPOT_NAME
    )
    if existing.distance_source != DISTANCE_SOURCE_OD:
        raise AssertionError("El modo OD debe usar matriz OD para candidatos con node_index")
    if existing.time_source != TIME_SOURCE_OD:
        raise AssertionError("El modo OD debe usar matriz de tiempos")
    print("  OK modo OD explicito")


def test_integrated_comparison_contains_methods_and_candidates() -> None:
    print("test_integrated_comparison_contains_methods_and_candidates")
    ds = _load_dataset_once()
    frame = build_full_location_comparison(ds)
    names = set(frame["Nombre"].tolist())
    for method in LocationMethod:
        expected = f"Optimo continuo ({method.value})"
        if expected not in names:
            raise AssertionError(f"Falta la tecnica {expected} en la tabla integrada")
    if DEPOT_NAME not in names or SECONDARY_HUB_NAME not in names:
        raise AssertionError("La tabla integrada debe incluir SVQ1 y DQA4")
    midpoint = f"Punto medio {DEPOT_NAME}-{SECONDARY_HUB_NAME}"
    if midpoint not in names:
        raise AssertionError("La tabla integrada debe incluir el punto medio")
    if float(frame.iloc[0]["Delta vs mejor (%)"]) != 0.0:
        raise AssertionError("El mejor debe tener delta 0%")
    print("  OK tabla integrada completa")


def test_existing_location_methods_remain_compatible() -> None:
    print("test_existing_location_methods_remain_compatible")
    ds = _load_dataset_once()
    solver = LocationSolver(ds)
    for method in LocationMethod:
        result = solver.solve(method)
        if result.nearest_municipality not in ds.names:
            raise AssertionError(f"{method.value}: municipio cercano invalido")
        if result.weighted_distance <= 0:
            raise AssertionError(f"{method.value}: distancia ponderada no positiva")

    comparison_df = solver.compare_solutions()
    if len(comparison_df) != len(LocationMethod):
        raise AssertionError("compare_solutions debe mantener una fila por metodo")
    print("  OK metodos existentes compatibles")


def main() -> None:
    test_default_candidates_are_built()
    test_candidate_evaluation_metrics_are_sortable()
    test_weights_validation_and_defaults()
    test_auto_new_location_uses_all_methods_and_references()
    test_continuous_candidate_uses_geometric_without_time()
    test_default_evaluation_is_geometric_only()
    test_od_matrix_mode_is_explicit()
    test_integrated_comparison_contains_methods_and_candidates()
    test_existing_location_methods_remain_compatible()
    print("\nTodos los tests de localizacion OK")


if __name__ == "__main__":
    main()
