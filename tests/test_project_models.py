"""Tests de los modelos Python derivados de los scripts MATLAB."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.economics_model import (
    DEFAULT_OPTIONS,
    AdditionalCostParams,
    FinanceParams,
    VehicleCostParams,
    analyze_options,
    compute_economic_result,
    compute_economic_results,
    economic_results_frame,
    recommend_option,
    vehicle_totals,
)
from src.warehouse_model import DimensionParams, LayoutParams, compute_dimension, solve_layout
from src.warehouse_model import ALMACEN_3FLOOR_DOORS, floor_cost_summary


def approx(actual: float, expected: float, tolerance: float, msg: str) -> None:
    if abs(actual - expected) > tolerance:
        raise AssertionError(f"{msg}: esperado {expected}, obtenido {actual}")
    print(f"  OK {msg}")


def test_warehouse_dimension_defaults() -> None:
    print("test_warehouse_dimension_defaults")
    result = compute_dimension(DimensionParams())
    approx(result.slots_per_shelf, 56, 0.0, "Huecos por estanteria")
    approx(result.real_packages_per_shelf, 450.24, 1e-6, "Capacidad real por estanteria")
    approx(result.capacity_per_floor, 2_251_200, 1e-6, "Capacidad por planta")
    approx(result.total_capacity, 6_753_600, 1e-6, "Capacidad total")


def test_layout_comparison_defaults() -> None:
    print("test_layout_comparison_defaults")
    result = solve_layout(LayoutParams())
    approx(result.cost_by_floor, 71.68654761904762, 1e-9, "Coste ABC por planta")
    approx(result.cost_global, 64.73206349206349, 1e-9, "Coste ABC global")
    approx(result.improvement_pct, 9.701240132167102, 1e-9, "Mejora ABC global")


def test_almacen_3floor_vertical_penalty() -> None:
    print("test_almacen_3floor_vertical_penalty")
    result = solve_layout(LayoutParams(doors=ALMACEN_3FLOOR_DOORS))
    summary = floor_cost_summary(result)
    penalties = summary["Penalización vertical (celdas)"].tolist()
    approx(penalties[0], 12.0, 1e-9, "Penalizacion planta 1")
    approx(penalties[1], 24.0, 1e-9, "Penalizacion planta 2")
    approx(penalties[2], 36.0, 1e-9, "Penalizacion planta 3")

    means = summary["f medio"].tolist()
    approx(means[1] - means[0], 12.0, 1e-9, "Incremento f medio P2-P1")
    approx(means[2] - means[1], 12.0, 1e-9, "Incremento f medio P3-P2")


def test_economics_defaults() -> None:
    print("test_economics_defaults")
    results = analyze_options(DEFAULT_OPTIONS, AdditionalCostParams(), FinanceParams())
    if recommend_option(results) != "Estándar":
        raise AssertionError("La opcion recomendada por defecto debe ser Estándar")
    standard = results[results["Opción"] == "Estándar"].iloc[0]
    approx(standard["CAPEX total"], 34_400_000, 1e-6, "CAPEX total estándar")
    approx(standard["Ahorro neto anual"], 5_723_000, 1e-6, "Ahorro neto estándar")
    approx(standard["VAN"], 5_795_957.158757268, 1e-6, "VAN estándar")


def test_structured_economic_result_defaults() -> None:
    print("test_structured_economic_result_defaults")
    finance = FinanceParams()
    standard = compute_economic_result(DEFAULT_OPTIONS[1], AdditionalCostParams(), finance)
    approx(standard.capex_base, 28_500_000, 1e-6, "CAPEX base estructurado")
    approx(standard.capex_transition, 5_900_000, 1e-6, "CAPEX transicion estructurado")
    approx(standard.capex_total, 34_400_000, 1e-6, "CAPEX total estructurado")
    approx(standard.opex_new_annual, 977_000, 1e-6, "OPEX nuevo estructurado")
    approx(standard.net_savings_annual, 5_723_000, 1e-6, "Ahorro neto estructurado")
    approx(standard.van, 5_795_957.158757268, 1e-6, "VAN estructurado")
    approx(
        standard.pessimistic.capex_total,
        34_400_000 * finance.pessimistic_capex_multiplier,
        1e-6,
        "CAPEX pesimista estructurado",
    )
    approx(
        standard.pessimistic.net_savings_annual,
        5_723_000 * finance.pessimistic_savings_multiplier,
        1e-6,
        "Ahorro pesimista estructurado",
    )
    approx(
        standard.pessimistic.payback,
        standard.pessimistic.capex_total / standard.pessimistic.net_savings_annual,
        1e-12,
        "Payback pesimista estructurado",
    )


def test_analyze_options_wrapper_matches_structured_frame() -> None:
    print("test_analyze_options_wrapper_matches_structured_frame")
    additional = AdditionalCostParams()
    finance = FinanceParams()
    structured = compute_economic_results(DEFAULT_OPTIONS, additional, finance)
    structured_frame = economic_results_frame(structured)
    wrapper_frame = analyze_options(DEFAULT_OPTIONS, additional, finance)
    expected_columns = [
        "Opción",
        "CAPEX base",
        "CAPEX transición",
        "CAPEX total",
        "Ahorro bruto anual",
        "OPEX nuevo anual",
        "Ahorro neto anual",
        "Payback neto",
        "VAN",
        "TIR",
        "VAN/CAPEX",
        "Payback pesimista",
        "VAN pesimista",
        "Robots",
    ]
    if list(wrapper_frame.columns) != expected_columns:
        raise AssertionError("analyze_options debe mantener las columnas historicas")
    if not wrapper_frame.equals(structured_frame):
        raise AssertionError("analyze_options debe ser equivalente al frame estructurado")
    print("  OK wrapper estable de economia")


def test_vehicle_cost_defaults() -> None:
    print("test_vehicle_cost_defaults")
    totals = vehicle_totals(VehicleCostParams())
    approx(totals["vans"], 9_168_668.8, 1e-6, "Coste furgonetas")
    approx(totals["trailers"], 993_743.44, 1e-6, "Coste trailers")
    approx(totals["total"], 10_162_412.24, 1e-6, "Coste total rutas")
    approx(totals["difference"], 122_025.86, 1e-6, "Diferencial frente a sin unificar")


def main() -> None:
    test_warehouse_dimension_defaults()
    test_layout_comparison_defaults()
    test_almacen_3floor_vertical_penalty()
    test_economics_defaults()
    test_structured_economic_result_defaults()
    test_analyze_options_wrapper_matches_structured_frame()
    test_vehicle_cost_defaults()
    print("\nTodos los tests de modelos OK")


if __name__ == "__main__":
    main()
