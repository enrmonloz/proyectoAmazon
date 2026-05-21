"""Tests for external OD loader.

Uso: ``python tests/test_external_od_loader.py``
"""

from __future__ import annotations

import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.data_loader import Dataset  # noqa: E402
from src.external_od_loader import (  # noqa: E402
    dataset_with_external_depot_od,
    load_center_od_from_excel,
)


def _dataset() -> Dataset:
    distance = np.array(
        [
            [0.0, 10.0],
            [10.0, 0.0],
        ]
    )
    time = np.array(
        [
            [0.0, 15.0],
            [15.0, 0.0],
        ]
    )
    return Dataset(
        names=["Nodo A", "Nodo B"],
        latitudes=np.array([0.0, 1.0]),
        longitudes=np.array([0.0, 1.0]),
        restringe_camion=np.array([0, 0]),
        poblacion=np.array([10, 20]),
        distance_matrix=distance,
        time_matrix=time,
        depot_index=0,
    )


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


def test_load_center_od_from_excel_validates_columns() -> None:
    print("test_load_center_od_from_excel_validates_columns")
    df = pd.DataFrame(
        {
            "center_name": ["Centro X"],
            "destination": ["Nodo A"],
            "distance_km": [12.0],
        }
    )
    with TemporaryDirectory() as tmp:
        path = Path(tmp) / "od.xlsx"
        df.to_excel(path, index=False)
        _assert_raises_contains(
            lambda: load_center_od_from_excel(path, "Centro X"),
            "Faltan columnas",
        )
    print("  OK valida columnas minimas")


def test_load_center_od_from_excel_filters_center() -> None:
    print("test_load_center_od_from_excel_filters_center")
    df = pd.DataFrame(
        {
            "center_name": ["Centro X", "Centro Y"],
            "destination": ["Nodo A", "Nodo B"],
            "distance_km": [12.0, 14.0],
            "time_min": [20.0, 25.0],
        }
    )
    with TemporaryDirectory() as tmp:
        path = Path(tmp) / "od.xlsx"
        df.to_excel(path, index=False)
        filtered = load_center_od_from_excel(path, "Centro X")
    if len(filtered) != 1 or filtered.iloc[0]["center_name"] != "Centro X":
        raise AssertionError("Debe filtrar por center_name")
    print("  OK filtra por centro")


def test_dataset_with_external_depot_od_builds_dataset() -> None:
    print("test_dataset_with_external_depot_od_builds_dataset")
    ds = _dataset()
    od_table = pd.DataFrame(
        {
            "center_name": ["Centro X", "Centro X"],
            "destination": ["Nodo A", "Nodo B"],
            "distance_km": [12.0, 15.0],
            "time_min": [18.0, 22.0],
        }
    )
    new_ds = dataset_with_external_depot_od(
        ds,
        center_name="Centro X",
        latitude=2.0,
        longitude=3.0,
        od_table=od_table,
    )
    if new_ds.n_nodes != ds.n_nodes + 1:
        raise AssertionError("Debe añadir un nodo al dataset")
    if new_ds.depot_index != ds.n_nodes:
        raise AssertionError("El nuevo depot debe quedar al final")
    if new_ds.names[-1] != "Centro X":
        raise AssertionError("Debe conservar el nombre del nuevo depot")
    if new_ds.distance_matrix[new_ds.depot_index, 0] != 12.0:
        raise AssertionError("Debe usar distancia OD externa")
    if new_ds.time_matrix[new_ds.depot_index, 1] != 22.0:
        raise AssertionError("Debe usar tiempo OD externo")
    print("  OK dataset extendido con OD externo")


def test_dataset_with_external_depot_od_requires_all_destinations() -> None:
    print("test_dataset_with_external_depot_od_requires_all_destinations")
    ds = _dataset()
    od_table = pd.DataFrame(
        {
            "center_name": ["Centro X"],
            "destination": ["Nodo A"],
            "distance_km": [12.0],
            "time_min": [18.0],
        }
    )
    _assert_raises_contains(
        lambda: dataset_with_external_depot_od(
            ds,
            center_name="Centro X",
            latitude=2.0,
            longitude=3.0,
            od_table=od_table,
        ),
        "Faltan destinos",
    )
    print("  OK valida destinos completos")


def main() -> None:
    test_load_center_od_from_excel_validates_columns()
    test_load_center_od_from_excel_filters_center()
    test_dataset_with_external_depot_od_builds_dataset()
    test_dataset_with_external_depot_od_requires_all_destinations()
    print("\nTodos los tests de OD externo OK")


if __name__ == "__main__":
    main()
