"""Tests for the simple guided economics module."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.guided_economics import (  # noqa: E402
    CURRENT_DQA4_ANNUAL_COST,
    CURRENT_SVQ1_ANNUAL_COST,
    CURRENT_TOTAL_ANNUAL_COST,
    CURRENT_TRANSFER_ANNUAL_COST,
    GUIDED_SCENARIO_SAVINGS,
    GuidedEconomicInputs,
    GuidedSavingsProfile,
    _npv,
    compute_guided_economic_analysis,
    compute_guided_economic_case,
    current_cost_reference_summary,
)


def approx(actual: float, expected: float, tolerance: float, msg: str) -> None:
    if abs(actual - expected) > tolerance:
        raise AssertionError(f"{msg}: esperado {expected}, obtenido {actual}")
    print(f"  OK {msg}")


def test_route_differential_uses_dqa4_reference() -> None:
    print("test_route_differential_uses_dqa4_reference")
    inputs = GuidedEconomicInputs(
        alternative="SVQ1 ampliado",
        investment_option_name="Básica",
        transport_support="Sin apoyo",
        route_cost_annual=12.0,
        route_cost_reference_annual=10.0,
        include_training=False,
        include_dqa4_value_loss=False,
    )
    case = compute_guided_economic_case(inputs, GuidedSavingsProfile("Prueba", 0.0, 0.0, 0.0))
    approx(case.route_overcost_annual, 2.0, 1e-12, "diferencial de rutas")


def test_current_cost_reference_uses_enunciado_totals() -> None:
    print("test_current_cost_reference_uses_enunciado_totals")
    expected_total = 36.2e6 + 18.1e6 + 1.99e6
    approx(CURRENT_TOTAL_ANNUAL_COST, expected_total, 1e-6, "total actual del enunciado")

    summary = current_cost_reference_summary()
    approx(float(summary["svq1_annual_cost"]), CURRENT_SVQ1_ANNUAL_COST, 1e-6, "coste actual SVQ1")
    approx(float(summary["dqa4_annual_cost"]), CURRENT_DQA4_ANNUAL_COST, 1e-6, "coste actual DQA4")
    approx(float(summary["transfer_annual_cost"]), CURRENT_TRANSFER_ANNUAL_COST, 1e-6, "coste transferencia")
    approx(float(summary["total_annual_cost"]), CURRENT_TOTAL_ANNUAL_COST, 1e-6, "coste actual total")

    breakdown = summary["breakdown"]
    approx(float(breakdown["SVQ1"]["personal"]), 20.7e6, 1e-6, "desglose SVQ1 personal")
    approx(float(breakdown["DQA4"]["energy_fuel"]), 4.7e6, 1e-6, "desglose DQA4 energia")


def test_current_reference_is_absolute_cost_for_dqa4_base() -> None:
    print("test_current_reference_is_absolute_cost_for_dqa4_base")
    ahorro_base = 0.0
    estimated_base_cost = CURRENT_TOTAL_ANNUAL_COST - ahorro_base
    approx(estimated_base_cost, CURRENT_TOTAL_ANNUAL_COST, 1e-6, "DQA4/base mantiene coste actual")


def test_route_differential_can_be_negative() -> None:
    print("test_route_differential_can_be_negative")
    inputs = GuidedEconomicInputs(
        alternative="Centro óptimo",
        investment_option_name="Básica",
        transport_support="Sin apoyo",
        route_cost_annual=8.0,
        route_cost_reference_annual=10.0,
        include_training=False,
        include_dqa4_value_loss=False,
    )
    analysis = compute_guided_economic_analysis(inputs)
    approx(analysis.route_overcost_annual, -2.0, 1e-12, "diferencial negativo de rutas")


def test_estimated_absolute_cost_subtracts_average_net_saving() -> None:
    print("test_estimated_absolute_cost_subtracts_average_net_saving")
    inputs = GuidedEconomicInputs(
        alternative="SVQ1 ampliado",
        investment_option_name="Básica",
        transport_support="Sin apoyo",
        route_cost_annual=12.0,
        route_cost_reference_annual=10.0,
        include_training=False,
        include_dqa4_value_loss=False,
        include_phasing=False,
        include_backup=False,
        include_insurance=False,
        include_incentives=False,
    )
    case = compute_guided_economic_case(inputs, GUIDED_SCENARIO_SAVINGS[1])
    expected = CURRENT_TOTAL_ANNUAL_COST - case.ahorro_neto_promedio
    approx(case.current_total_annual_cost, CURRENT_TOTAL_ANNUAL_COST, 1e-6, "referencia anual del caso")
    approx(case.estimated_absolute_annual_cost, expected, 1e-6, "coste absoluto estimado")


def test_capex_does_not_change_estimated_absolute_cost_directly() -> None:
    print("test_capex_does_not_change_estimated_absolute_cost_directly")
    base_inputs = GuidedEconomicInputs(
        alternative="SVQ1 ampliado",
        investment_option_name="Básica",
        transport_support="Sin apoyo",
        route_cost_annual=0.0,
        route_cost_reference_annual=0.0,
        include_training=False,
        include_dqa4_value_loss=False,
        include_phasing=False,
        include_backup=False,
        include_insurance=False,
        include_incentives=False,
    )
    premium_inputs = GuidedEconomicInputs(
        alternative="SVQ1 ampliado",
        investment_option_name="Premium",
        transport_support="Sin apoyo",
        route_cost_annual=0.0,
        route_cost_reference_annual=0.0,
        include_training=False,
        include_dqa4_value_loss=False,
        include_phasing=False,
        include_backup=False,
        include_insurance=False,
        include_incentives=False,
    )
    base_case = compute_guided_economic_case(base_inputs, GUIDED_SCENARIO_SAVINGS[1])
    premium_case = compute_guided_economic_case(premium_inputs, GUIDED_SCENARIO_SAVINGS[1])
    if premium_case.capex_total <= base_case.capex_total:
        raise AssertionError("La opción premium debe tener más CAPEX que la básica")
    approx(
        premium_case.estimated_absolute_annual_cost,
        base_case.estimated_absolute_annual_cost,
        1e-6,
        "CAPEX no cambia directamente el coste anual estimado",
    )


def test_pert_and_sigma_follow_formula() -> None:
    print("test_pert_and_sigma_follow_formula")
    inputs = GuidedEconomicInputs(
        alternative="SVQ1 ampliado",
        investment_option_name="Básica",
        transport_support="Sin apoyo",
        route_cost_annual=0.0,
        route_cost_reference_annual=0.0,
        include_training=False,
        include_dqa4_value_loss=False,
    )
    analysis = compute_guided_economic_analysis(inputs)
    expected_pert = (
        analysis.optimistic_case.ahorro_neto_promedio
        + 4.0 * analysis.probable_case.ahorro_neto_promedio
        + analysis.pessimistic_case.ahorro_neto_promedio
    ) / 6.0
    expected_sigma = abs(
        analysis.optimistic_case.ahorro_neto_promedio - analysis.pessimistic_case.ahorro_neto_promedio
    ) / 6.0
    approx(analysis.ahorro_pert, expected_pert, 1e-9, "PERT de ahorro anual")
    approx(analysis.sigma, expected_sigma, 1e-9, "sigma PERT")


def test_van_for_known_cashflow() -> None:
    print("test_van_for_known_cashflow")
    cashflows = (-100.0, 60.0, 60.0)
    expected = -100.0 + 60.0 / 1.1 + 60.0 / (1.1**2)
    approx(_npv(0.1, cashflows), expected, 1e-12, "VAN conocido")


def test_learning_curve_applies_to_personal_and_energy() -> None:
    print("test_learning_curve_applies_to_personal_and_energy")
    inputs = GuidedEconomicInputs(
        alternative="SVQ1 ampliado",
        investment_option_name="Básica",
        transport_support="Sin apoyo",
        route_cost_annual=0.0,
        route_cost_reference_annual=0.0,
        include_training=False,
        include_dqa4_value_loss=False,
        include_phasing=False,
        include_backup=False,
        include_insurance=False,
        include_incentives=False,
        horizon_years=3,
    )
    profile = GuidedSavingsProfile("Prueba", 100.0, 40.0, 10.0)
    case = compute_guided_economic_case(inputs, profile)
    expected_year_1 = 1.99e6 + 0.5 * 100.0 + 0.5 * 40.0 + 10.0 - (3.2e6 * 0.30)
    expected_year_2 = 1.99e6 + 0.75 * 100.0 + 0.75 * 40.0 + 10.0 - (3.2e6 * 0.30)
    expected_year_3 = 1.99e6 + 1.0 * 100.0 + 1.0 * 40.0 + 10.0 - (3.2e6 * 0.30)
    approx(case.annual_flows[0], expected_year_1, 1e-9, "año 1 al 50 %")
    approx(case.annual_flows[1], expected_year_2, 1e-9, "año 2 al 75 %")
    approx(case.annual_flows[2], expected_year_3, 1e-9, "año 3 al 100 %")


def test_mitigation_reduces_expected_risk_and_adds_capex() -> None:
    print("test_mitigation_reduces_expected_risk_and_adds_capex")
    base_inputs = GuidedEconomicInputs(
        alternative="SVQ1 ampliado",
        investment_option_name="Básica",
        transport_support="Sin apoyo",
        route_cost_annual=0.0,
        route_cost_reference_annual=0.0,
        include_training=False,
        include_dqa4_value_loss=False,
        include_phasing=False,
        include_backup=False,
        include_insurance=False,
        include_incentives=False,
    )
    mitigated_inputs = GuidedEconomicInputs(
        alternative="SVQ1 ampliado",
        investment_option_name="Básica",
        transport_support="Sin apoyo",
        route_cost_annual=0.0,
        route_cost_reference_annual=0.0,
        include_training=False,
        include_dqa4_value_loss=False,
        include_phasing=True,
        include_backup=True,
        include_insurance=True,
        include_incentives=True,
    )
    base_case = compute_guided_economic_case(base_inputs, GUIDED_SCENARIO_SAVINGS[1])
    mitigated_case = compute_guided_economic_case(mitigated_inputs, GUIDED_SCENARIO_SAVINGS[1])
    if mitigated_case.capex_transition <= base_case.capex_transition:
        raise AssertionError("Las mitigaciones deben sumar CAPEX")
    if mitigated_case.capex_risk_expected >= base_case.capex_risk_expected:
        raise AssertionError("Las mitigaciones deben reducir el riesgo esperado")
    if mitigated_case.annual_technology_failure_cost >= base_case.annual_technology_failure_cost:
        raise AssertionError("Las mitigaciones deben reducir el coste tecnológico recurrente")


def main() -> None:
    test_route_differential_uses_dqa4_reference()
    test_current_cost_reference_uses_enunciado_totals()
    test_current_reference_is_absolute_cost_for_dqa4_base()
    test_route_differential_can_be_negative()
    test_estimated_absolute_cost_subtracts_average_net_saving()
    test_capex_does_not_change_estimated_absolute_cost_directly()
    test_pert_and_sigma_follow_formula()
    test_van_for_known_cashflow()
    test_learning_curve_applies_to_personal_and_energy()
    test_mitigation_reduces_expected_risk_and_adds_capex()
    print("\nTodos los tests de economia guiada OK")


if __name__ == "__main__":
    main()
