"""Tests del filtro lógico de provincias agregadas y diagnóstico OD.

Uso: ``python tests/test_service_area.py``
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.data_loader import load_dataset
from src.service_area import (
    AGGREGATED_PROVINCE_NODES,
    DEFAULT_ACTIVE_PROVINCE_NODES,
    apply_province_node_filter,
    validate_od_alignment_for_known_nodes,
)


DATA_DIR = ROOT / "data"


def _load_dataset_once():
    return load_dataset(
        poblacion_path=str(DATA_DIR / "poblacion.csv"),
        rutas_path=str(DATA_DIR / "rutasDistTiempo_v2.csv"),
    )


def _idx(dataset, name: str) -> int:
    return dataset.names.index(name)


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)
    print(f"  OK {message}")


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


def _assert_positive_finite_od(dataset, origin: str, destination: str) -> None:
    for from_name, to_name in ((origin, destination), (destination, origin)):
        i = _idx(dataset, from_name)
        j = _idx(dataset, to_name)
        distance = float(dataset.distance_matrix[i, j])
        time = float(dataset.time_matrix[i, j])
        _assert(np.isfinite(distance) and distance > 0, f"distancia finita {from_name}->{to_name}")
        _assert(np.isfinite(time) and time > 0, f"tiempo finito {from_name}->{to_name}")


def test_default_filter_keeps_shape_and_expected_population() -> None:
    print("test_default_filter_keeps_shape_and_expected_population")
    original = _load_dataset_once()
    filtered = apply_province_node_filter(original, DEFAULT_ACTIVE_PROVINCE_NODES)

    _assert(filtered.n_nodes == original.n_nodes, "mantiene numero de nodos")
    _assert(filtered.distance_matrix.shape == original.distance_matrix.shape, "mantiene forma distancia")
    _assert(filtered.time_matrix.shape == original.time_matrix.shape, "mantiene forma tiempo")

    for province_name in ("Málaga", "Granada", "Córdoba"):
        _assert(
            int(filtered.poblacion[_idx(filtered, province_name)]) == 0,
            f"{province_name} queda con poblacion 0",
        )

    for province_name in ("Cádiz", "Huelva"):
        original_population = int(original.poblacion[_idx(original, province_name)])
        filtered_population = int(filtered.poblacion[_idx(filtered, province_name)])
        _assert(filtered_population == original_population, f"{province_name} conserva poblacion")
        _assert(filtered_population > 0, f"{province_name} conserva poblacion positiva")


def test_filter_does_not_mutate_original_dataset() -> None:
    print("test_filter_does_not_mutate_original_dataset")
    original = _load_dataset_once()
    original_population = original.poblacion.copy()

    filtered = apply_province_node_filter(original, DEFAULT_ACTIVE_PROVINCE_NODES)

    _assert(np.array_equal(original.poblacion, original_population), "dataset original no se modifica")
    _assert(
        int(original.poblacion[_idx(original, "Málaga")]) > 0,
        "Malaga original mantiene poblacion positiva",
    )
    _assert(
        int(filtered.poblacion[_idx(filtered, "Málaga")]) == 0,
        "Malaga filtrada queda en 0",
    )


def test_all_provinces_keep_original_population() -> None:
    print("test_all_provinces_keep_original_population")
    original = _load_dataset_once()
    filtered = apply_province_node_filter(original, AGGREGATED_PROVINCE_NODES)

    for province_name in AGGREGATED_PROVINCE_NODES:
        _assert(
            int(filtered.poblacion[_idx(filtered, province_name)])
            == int(original.poblacion[_idx(original, province_name)]),
            f"{province_name} conserva poblacion al activar todas",
        )


def test_unknown_province_fails_clearly() -> None:
    print("test_unknown_province_fails_clearly")
    original = _load_dataset_once()
    _assert_raises_contains(
        lambda: apply_province_node_filter(original, ("Cádiz", "Jaén")),
        "Provincias agregadas no reconocidas",
    )


def test_od_diagnostics_known_pairs_are_positive() -> None:
    print("test_od_diagnostics_known_pairs_are_positive")
    original = _load_dataset_once()
    filtered = apply_province_node_filter(original, DEFAULT_ACTIVE_PROVINCE_NODES)

    warnings = validate_od_alignment_for_known_nodes(
        filtered,
        DEFAULT_ACTIVE_PROVINCE_NODES,
    )
    _assert(not warnings, f"diagnostico sin warnings: {warnings}")

    _assert_positive_finite_od(filtered, "SVQ1", "DQA4")
    _assert_positive_finite_od(filtered, "DQA4", "Huelva")
    _assert_positive_finite_od(filtered, "DQA4", "Cádiz")


def main() -> None:
    test_default_filter_keeps_shape_and_expected_population()
    test_filter_does_not_mutate_original_dataset()
    test_all_provinces_keep_original_population()
    test_unknown_province_fails_clearly()
    test_od_diagnostics_known_pairs_are_positive()


if __name__ == "__main__":
    main()
