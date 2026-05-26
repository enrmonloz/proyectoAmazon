"""Tests for route assignment strategy comparison."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.data_loader import Dataset  # noqa: E402
from src.fleet import FleetConfig  # noqa: E402
from src.pipeline import PipelineConfig  # noqa: E402
from src.route_strategy_comparison import compare_route_assignment_strategies  # noqa: E402
from src.vrp_solver import SolverStrategy  # noqa: E402


def _tiny_dataset() -> Dataset:
    return Dataset(
        names=["Depot", "A", "B"],
        latitudes=np.array([0.0, 0.1, 0.2]),
        longitudes=np.array([0.0, 0.1, 0.2]),
        restringe_camion=np.array([0, 0, 0]),
        poblacion=np.array([0, 100, 100]),
        distance_matrix=np.array(
            [
                [0.0, 10.0, 12.0],
                [10.0, 0.0, 5.0],
                [12.0, 5.0, 0.0],
            ]
        ),
        time_matrix=np.array(
            [
                [0.0, 12.0, 14.0],
                [12.0, 0.0, 6.0],
                [14.0, 6.0, 0.0],
            ]
        ),
        depot_index=0,
    )


def test_strategy_comparison_returns_route_metrics() -> None:
    print("test_strategy_comparison_returns_route_metrics")
    config = PipelineConfig(
        market_penetration=0.10,
        max_workday_hours=8.0,
        service_time_per_package_min=1.0,
        inter_package_time_min=0.0,
        fleet=FleetConfig(max_diesel=3, max_electric=0),
        solver_time_limit_seconds=5,
    )
    rows = compare_route_assignment_strategies(
        _tiny_dataset(),
        config,
        strategies=(SolverStrategy.INSERTION, SolverStrategy.NEAREST_NEIGHBOR),
    )

    if len(rows) != 2:
        raise AssertionError(f"Esperadas 2 filas, obtenido {len(rows)}")
    for row in rows:
        if row["Estado"] != "OK":
            raise AssertionError(f"Estrategia fallida: {row}")
        if row["Rutas VRP"] <= 0:
            raise AssertionError(f"Debe generar rutas VRP: {row}")
        if row["Rutas totales"] != row["Rutas VRP"] + row["Rutas dedicadas"]:
            raise AssertionError(f"Totales incoherentes: {row}")
        if row["Distancia total (km)"] <= 0 or row["Tiempo total (min)"] <= 0:
            raise AssertionError(f"Distancia y tiempo deben ser positivos: {row}")
    print("  OK comparacion de tecnicas con metricas operativas")


def main() -> None:
    test_strategy_comparison_returns_route_metrics()
    print("\nTodos los tests de comparacion de tecnicas OK")


if __name__ == "__main__":
    main()
