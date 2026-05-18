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
    LaborPolicyParams,
    LaborRisk,
    VehicleCostParams,
    analyze_options,
    compute_labor_costs,
    compute_labor_policy_result,
    compute_labor_risks,
    compute_economic_result,
    compute_economic_results,
    economic_results_frame,
    labor_policy_result_from_additional,
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


def test_labor_cost_policy_classification() -> None:
    print("test_labor_cost_policy_classification")
    corporate = LaborPolicyParams(
        transport_support="Transporte corporativo",
        include_training=False,
        include_incentives=False,
        include_labor_regulation_as_incremental=False,
    )
    oneoff, annual, _ = compute_labor_costs(corporate)
    approx(oneoff, 0.0, 1e-6, "Transporte corporativo no es coste unico")
    approx(annual, 441_000.0, 1e-6, "Transporte corporativo recurrente")

    subsidy = LaborPolicyParams(
        transport_support="Subsidio transporte público",
        include_training=False,
        include_incentives=False,
        include_labor_regulation_as_incremental=False,
    )
    oneoff, annual, _ = compute_labor_costs(subsidy)
    approx(oneoff, 0.0, 1e-6, "Subsidio no es coste unico")
    approx(annual, 187_000.0, 1e-6, "Subsidio recurrente")

    compensation = LaborPolicyParams(
        transport_support="Compensación única",
        include_training=False,
        include_incentives=False,
        include_labor_regulation_as_incremental=False,
    )
    oneoff, annual, _ = compute_labor_costs(compensation)
    approx(oneoff, 450_000.0, 1e-6, "Compensacion unica como coste unico")
    approx(annual, 0.0, 1e-6, "Compensacion unica sin recurrente")

    training_regulation = LaborPolicyParams(
        transport_support="Sin apoyo",
        include_training=True,
        include_incentives=False,
        include_labor_regulation_as_incremental=True,
    )
    oneoff, annual, _ = compute_labor_costs(training_regulation)
    approx(oneoff, 1_560_000.0, 1e-6, "Formacion como coste unico")
    approx(annual, 3_250_000.0, 1e-6, "Regulacion como recurrente")


def test_labor_risk_residuals_with_transport_mitigation() -> None:
    print("test_labor_risk_residuals_with_transport_mitigation")
    policy = LaborPolicyParams(
        transport_support="Transporte corporativo",
        include_training=False,
        include_incentives=False,
        include_labor_regulation_as_incremental=False,
    )
    results = compute_labor_risks(policy)
    totals = {result.name: result for result in results}
    approx(totals["Renuncias de empleados"].expected_cost, 448_000.0, 1e-6, "Riesgo base renuncias")
    approx(totals["Renuncias de empleados"].residual_expected_cost, 336_000.0, 1e-6, "Riesgo residual renuncias")
    approx(totals["Resistencia al cambio"].residual_expected_cost, 286_875.0, 1e-6, "Riesgo residual resistencia")
    approx(totals["Conflictos sindicales"].residual_expected_cost, 472_500.0, 1e-6, "Riesgo residual conflictos")


def test_lowest_labor_cash_cost_is_not_lowest_risk() -> None:
    print("test_lowest_labor_cash_cost_is_not_lowest_risk")
    no_support = compute_labor_policy_result(
        LaborPolicyParams(
            transport_support="Sin apoyo",
            include_training=False,
            include_incentives=False,
            include_labor_regulation_as_incremental=False,
        )
    )
    corporate = compute_labor_policy_result(
        LaborPolicyParams(
            transport_support="Transporte corporativo",
            include_training=False,
            include_incentives=False,
            include_labor_regulation_as_incremental=False,
        )
    )
    if no_support.summary.first_year_cash_cost >= corporate.summary.first_year_cash_cost:
        raise AssertionError("Sin apoyo debe tener menor coste directo que transporte corporativo")
    if no_support.summary.residual_risk_cost <= corporate.summary.residual_risk_cost:
        raise AssertionError("Sin apoyo debe conservar mayor riesgo residual")
    print("  OK menor coste directo no implica menor riesgo laboral")


def test_labor_validations() -> None:
    print("test_labor_validations")
    try:
        compute_labor_risks(LaborPolicyParams(), (LaborRisk("Probabilidad inválida", 1.2, 100.0),))
    except ValueError:
        print("  OK probabilidad laboral fuera de rango rechazada")
    else:
        raise AssertionError("Probabilidad laboral fuera de rango debe fallar")

    try:
        compute_labor_costs(LaborPolicyParams(training_capex=-1.0))
    except ValueError:
        print("  OK coste laboral negativo rechazado")
    else:
        raise AssertionError("Coste laboral negativo debe fallar")


def test_labor_wrapper_does_not_change_economic_result() -> None:
    print("test_labor_wrapper_does_not_change_economic_result")
    additional = AdditionalCostParams()
    finance = FinanceParams()
    before = compute_economic_result(DEFAULT_OPTIONS[1], additional, finance)
    labor = labor_policy_result_from_additional(additional)
    after = compute_economic_result(DEFAULT_OPTIONS[1], additional, finance)
    approx(labor.summary.oneoff_cost, 1_900_000.0, 1e-6, "Coste laboral unico por defecto")
    approx(labor.summary.annual_recurring_cost, 527_000.0, 1e-6, "Coste laboral recurrente por defecto")
    approx(after.capex_total, before.capex_total, 1e-6, "CAPEX economico estable tras wrapper laboral")
    approx(after.opex_new_annual, before.opex_new_annual, 1e-6, "OPEX economico estable tras wrapper laboral")
    approx(after.van, before.van, 1e-6, "VAN economico estable tras wrapper laboral")


def main() -> None:
    test_warehouse_dimension_defaults()
    test_layout_comparison_defaults()
    test_almacen_3floor_vertical_penalty()
    test_economics_defaults()
    test_structured_economic_result_defaults()
    test_analyze_options_wrapper_matches_structured_frame()
    test_vehicle_cost_defaults()
    test_labor_cost_policy_classification()
    test_labor_risk_residuals_with_transport_mitigation()
    test_lowest_labor_cash_cost_is_not_lowest_risk()
    test_labor_validations()
    test_labor_wrapper_does_not_change_economic_result()
    print("\nTodos los tests de modelos OK")


if __name__ == "__main__":
    main()
