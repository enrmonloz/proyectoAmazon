"""Tests del puente inicial entre rutas/logistica y economia."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app import _resolve_operational_dataset
from src.data_loader import DEPOT_NAME, SECONDARY_HUB_NAME, Dataset, dataset_with_depot
from src.economics_model import (
    DEFAULT_OPTIONS,
    OPERATIONAL_OPTIONS,
    CurrentCostParams,
    FinanceParams,
    OPERATIONAL_OPTION_CURRENT,
    OPERATIONAL_OPTION_INTERMEDIATE,
    OPERATIONAL_OPTION_SVQ1_EXPANDED,
    AdditionalCostParams,
    VehicleCostParams,
    compute_economic_result,
    dqa4_current_cost,
    estimate_dqa4_liberable_cost,
    estimate_operational_cost_bridge,
    estimate_transfer_saving,
    summarize_pipeline_operations,
)


def approx(actual: float, expected: float, tolerance: float, msg: str) -> None:
    if abs(actual - expected) > tolerance:
        raise AssertionError(f"{msg}: esperado {expected}, obtenido {actual}")
    print(f"  OK {msg}")


def assert_raises_valueerror(fn, msg: str) -> None:
    try:
        fn()
    except ValueError:
        print(f"  OK {msg}")
        return
    raise AssertionError(f"Deberia fallar: {msg}")


def _fake_pipeline_result(depot_index: int = 0):
    dataset = SimpleNamespace(
        names=["SVQ1", "DQA4", "Nodo A"],
        depot_index=depot_index,
    )
    return SimpleNamespace(
        dataset=dataset,
        packages=np.array([0, 20, 30]),
        total_routes=8,
        vrp_route_count=5,
        dedicated_route_count=3,
        trailer_route_count=1,
        van_dedicated_route_count=2,
        total_distance_km=640.5,
        total_time_min=1_230.0,
        vrp=SimpleNamespace(diesel_count=4, electric_count=1),
    )


def test_operational_summary_copies_pipeline_aggregates() -> None:
    print("test_operational_summary_copies_pipeline_aggregates")
    summary = summarize_pipeline_operations(
        _fake_pipeline_result(),
        OPERATIONAL_OPTION_CURRENT,
    )
    if summary.center_option != OPERATIONAL_OPTION_CURRENT:
        raise AssertionError("Debe conservar la alternativa operativa")
    if summary.depot_name != "SVQ1":
        raise AssertionError("Debe leer el depot desde el dataset del pipeline")
    approx(summary.total_routes, 8, 0, "Rutas totales")
    approx(summary.vrp_routes, 5, 0, "Rutas VRP")
    approx(summary.dedicated_routes, 3, 0, "Rutas dedicadas")
    approx(summary.trailer_routes, 1, 0, "Rutas trailer")
    approx(summary.total_distance_km, 640.5, 1e-9, "Distancia total")
    approx(summary.total_time_min, 1_230.0, 1e-9, "Tiempo total")
    approx(summary.total_packages, 50, 0, "Paquetes totales")


def test_current_structure_has_no_transfer_saving() -> None:
    print("test_current_structure_has_no_transfer_saving")
    current = CurrentCostParams()
    saving = estimate_transfer_saving(current, OPERATIONAL_OPTION_CURRENT)
    approx(saving, 0.0, 1e-9, "Transferencia mantenida")


def _two_hub_dataset() -> Dataset:
    distance = np.array([[0.0, 1.0], [1.0, 0.0]])
    time = np.array([[0.0, 2.0], [2.0, 0.0]])
    return Dataset(
        names=[DEPOT_NAME, SECONDARY_HUB_NAME],
        latitudes=np.array([0.0, 1.0]),
        longitudes=np.array([0.0, 1.0]),
        restringe_camion=np.array([0, 0]),
        poblacion=np.array([0, 10]),
        distance_matrix=distance,
        time_matrix=time,
        depot_index=0,
    )


def test_current_structure_uses_dqa4_as_last_mile_depot() -> None:
    print("test_current_structure_uses_dqa4_as_last_mile_depot")
    dataset, notes = _resolve_operational_dataset(_two_hub_dataset(), OPERATIONAL_OPTION_CURRENT)
    if dataset.names[dataset.depot_index] != SECONDARY_HUB_NAME:
        raise AssertionError("Estructura actual debe usar DQA4 como depot de última milla")
    if not any("DQA4" in note and "transferencia" in note for note in notes):
        raise AssertionError("La nota debe explicar DQA4 y la transferencia mantenida")
    print("  OK estructura actual sale desde DQA4")


def test_svq1_expanded_uses_svq1_as_last_mile_depot() -> None:
    print("test_svq1_expanded_uses_svq1_as_last_mile_depot")
    dataset, notes = _resolve_operational_dataset(_two_hub_dataset(), OPERATIONAL_OPTION_SVQ1_EXPANDED)
    if dataset.names[dataset.depot_index] != DEPOT_NAME:
        raise AssertionError("SVQ1 ampliado debe usar SVQ1 como depot de última milla")
    if not any("DQA4 sigue operando" in note for note in notes):
        raise AssertionError("La nota debe recordar que DQA4 sigue operando")
    print("  OK SVQ1 ampliado sale desde SVQ1")


def test_dqa4_reference_is_not_main_operational_option() -> None:
    print("test_dqa4_reference_is_not_main_operational_option")
    if "DQA4 referencia" in OPERATIONAL_OPTIONS:
        raise AssertionError("DQA4 referencia no debe exponerse como alternativa principal")
    if OPERATIONAL_OPTIONS != (
        OPERATIONAL_OPTION_CURRENT,
        OPERATIONAL_OPTION_SVQ1_EXPANDED,
        OPERATIONAL_OPTION_INTERMEDIATE,
    ):
        raise AssertionError("Las alternativas principales deben ser solo tres")
    print("  OK selector principal sin DQA4 referencia")


def test_svq1_expanded_has_transfer_saving_but_not_full_dqa4_closure() -> None:
    print("test_svq1_expanded_has_transfer_saving_but_not_full_dqa4_closure")
    current = CurrentCostParams()
    result = estimate_operational_cost_bridge(
        _fake_pipeline_result(),
        current,
        VehicleCostParams(),
        OPERATIONAL_OPTION_SVQ1_EXPANDED,
        dqa4_attributable_share=0.10,
    )
    approx(
        result.estimated_transfer_saving,
        current.transfer_annual_cost,
        1e-9,
        "Ahorro transferencia SVQ1 ampliado",
    )
    if result.estimated_dqa4_partial_saving <= 0:
        raise AssertionError("El ahorro parcial DQA4 debe ser positivo con share > 0")
    if result.estimated_dqa4_partial_saving >= dqa4_current_cost(current):
        raise AssertionError("El ahorro DQA4 parcial no debe ser cierre total")
    if "DQA4 no se cierra" not in result.interpretation:
        raise AssertionError("La interpretacion debe negar el cierre total de DQA4")
    print("  OK DQA4 parcial y transferencia reducible")


def test_dqa4_attributable_share_validation() -> None:
    print("test_dqa4_attributable_share_validation")
    current = CurrentCostParams()
    assert_raises_valueerror(
        lambda: estimate_dqa4_liberable_cost(current, -0.01),
        "share DQA4 negativo",
    )
    assert_raises_valueerror(
        lambda: estimate_dqa4_liberable_cost(current, 1.01),
        "share DQA4 mayor que 1",
    )
    assert_raises_valueerror(
        lambda: estimate_dqa4_liberable_cost(current, 1.0),
        "share DQA4 no puede ser cierre total",
    )


def test_dqa4_share_zero_and_partial_values() -> None:
    print("test_dqa4_share_zero_and_partial_values")
    current = CurrentCostParams()
    approx(
        estimate_dqa4_liberable_cost(current, 0.0),
        0.0,
        1e-9,
        "Share cero sin ahorro DQA4",
    )
    partial = estimate_dqa4_liberable_cost(current, 0.25)
    if not 0.0 < partial < dqa4_current_cost(current):
        raise AssertionError("Share parcial debe quedar entre 0 y coste DQA4 total")
    print("  OK share parcial menor que coste DQA4 total")


def test_intermediate_center_warns_without_false_transfer_saving() -> None:
    print("test_intermediate_center_warns_without_false_transfer_saving")
    result = estimate_operational_cost_bridge(
        _fake_pipeline_result(),
        CurrentCostParams(),
        VehicleCostParams(),
        OPERATIONAL_OPTION_INTERMEDIATE,
        dqa4_attributable_share=0.10,
    )
    approx(result.estimated_transfer_saving, 0.0, 1e-9, "Sin transferencia inventada")
    approx(result.estimated_dqa4_partial_saving, 0.0, 1e-9, "Sin DQA4 inventado")
    if not result.bridge.warnings:
        raise AssertionError("El centro intermedio debe producir advertencia")
    print("  OK centro intermedio advertido")


def test_bridge_does_not_change_base_economic_result() -> None:
    print("test_bridge_does_not_change_base_economic_result")
    additional = AdditionalCostParams()
    finance = FinanceParams()
    before = compute_economic_result(DEFAULT_OPTIONS[1], additional, finance)
    estimate_operational_cost_bridge(
        _fake_pipeline_result(),
        CurrentCostParams(),
        VehicleCostParams(),
        OPERATIONAL_OPTION_SVQ1_EXPANDED,
    )
    after = compute_economic_result(DEFAULT_OPTIONS[1], additional, finance)
    approx(after.capex_total, before.capex_total, 1e-9, "CAPEX base estable")
    approx(after.opex_new_annual, before.opex_new_annual, 1e-9, "OPEX base estable")
    approx(after.van, before.van, 1e-9, "VAN base estable")


def test_dataset_with_depot_preserves_matrices_and_changes_only_depot() -> None:
    print("test_dataset_with_depot_preserves_matrices_and_changes_only_depot")
    dataset = _two_hub_dataset()
    distance = dataset.distance_matrix
    time = dataset.time_matrix
    updated = dataset_with_depot(dataset, SECONDARY_HUB_NAME)
    if dataset.depot_index != 0:
        raise AssertionError("El dataset original no debe cambiar")
    if updated.depot_index != 1:
        raise AssertionError("El helper debe cambiar el depot_index")
    if updated.distance_matrix is not distance or updated.time_matrix is not time:
        raise AssertionError("El helper debe conservar las matrices")
    assert_raises_valueerror(lambda: dataset_with_depot(dataset, "Nodo inexistente"), "Nodo inexistente")
    print("  OK depot alternativo seguro")


def main() -> None:
    test_operational_summary_copies_pipeline_aggregates()
    test_current_structure_has_no_transfer_saving()
    test_current_structure_uses_dqa4_as_last_mile_depot()
    test_svq1_expanded_uses_svq1_as_last_mile_depot()
    test_dqa4_reference_is_not_main_operational_option()
    test_svq1_expanded_has_transfer_saving_but_not_full_dqa4_closure()
    test_dqa4_attributable_share_validation()
    test_dqa4_share_zero_and_partial_values()
    test_intermediate_center_warns_without_false_transfer_saving()
    test_bridge_does_not_change_base_economic_result()
    test_dataset_with_depot_preserves_matrices_and_changes_only_depot()
    print("\nTodos los tests del puente operativo-economico OK")


if __name__ == "__main__":
    main()
