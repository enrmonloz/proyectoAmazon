"""Tests for guided route operating costs."""

from __future__ import annotations

import inspect
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import src.route_costs as route_costs_module  # noqa: E402
from src.route_costs import (  # noqa: E402
    FURGONETA_RATE_2026,
    TRAILER_RATE_2026,
    compute_pipeline_route_costs,
    compute_route_cost,
)


def approx(actual: float, expected: float, tolerance: float, msg: str) -> None:
    if abs(actual - expected) > tolerance:
        raise AssertionError(f"{msg}: esperado {expected}, obtenido {actual}")
    print(f"  OK {msg}")


def _route(distance_km: float, time_min: float, vehicle_type: str = "furgoneta"):
    return SimpleNamespace(
        travel_distance_km=distance_km,
        total_time_min=time_min,
        vehicle_type=vehicle_type,
    )


def _pipeline_result():
    return SimpleNamespace(
        packages=[0, 80, 20],
        vrp=SimpleNamespace(routes=[_route(100.0, 120.0)], unassigned_nodes=[]),
        split=SimpleNamespace(dedicated_routes=[_route(100.0, 120.0, "trailer")]),
    )


def test_furgoneta_route_cost_formula() -> None:
    print("test_furgoneta_route_cost_formula")
    expected = 100.0 * 0.3035 + 2.0 * 25.47
    actual = compute_route_cost(100.0, 120.0, FURGONETA_RATE_2026)
    approx(actual, expected, 1e-9, "formula furgoneta")


def test_trailer_route_cost_formula() -> None:
    print("test_trailer_route_cost_formula")
    expected = 100.0 * 0.6670 + 2.0 * 43.80
    actual = compute_route_cost(100.0, 120.0, TRAILER_RATE_2026)
    approx(actual, expected, 1e-9, "formula trailer")


def test_pipeline_annual_and_package_costs() -> None:
    print("test_pipeline_annual_and_package_costs")
    summary = compute_pipeline_route_costs(
        _pipeline_result(),
        scenario_name="Escenario",
        center_name="DQA4",
        working_days_per_year=225,
    )
    expected_van_daily = 100.0 * 0.3035 + 2.0 * 25.47
    expected_trailer_daily = 100.0 * 0.6670 + 2.0 * 43.80
    expected_daily = expected_van_daily + expected_trailer_daily
    expected_annual = expected_daily * 225
    expected_package_cost = expected_annual / (100 * 225)

    approx(summary.van_daily_cost, expected_van_daily, 1e-9, "coste diario furgonetas")
    approx(summary.trailer_daily_cost, expected_trailer_daily, 1e-9, "coste diario trailers")
    approx(summary.total_annual_cost, expected_annual, 1e-9, "coste anual = diario * 225")
    approx(summary.cost_per_package, expected_package_cost, 1e-9, "coste por paquete")
    if len(summary.breakdown) != 2:
        raise AssertionError("Debe generar desglose por ruta")
    print("  OK desglose por ruta")


def test_route_costs_do_not_use_spreadsheets() -> None:
    print("test_route_costs_do_not_use_spreadsheets")
    source = inspect.getsource(route_costs_module).lower()
    forbidden = ("read_excel", "openpyxl", "xlrd", ".xlsx", ".xls")
    for token in forbidden:
        if token in source:
            raise AssertionError(f"No debe depender de hojas de calculo: {token}")
    print("  OK sin lectura de hojas de calculo")


def main() -> None:
    test_furgoneta_route_cost_formula()
    test_trailer_route_cost_formula()
    test_pipeline_annual_and_package_costs()
    test_route_costs_do_not_use_spreadsheets()
    print("\nTodos los tests de costes de rutas OK")


if __name__ == "__main__":
    main()
