"""Tests for the guided economics redesign."""

from __future__ import annotations

import inspect
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import src.guided_economics as guided_economics_module  # noqa: E402
from src.guided_economics import (  # noqa: E402
    CURRENT_TOTAL_ANNUAL_COST,
    GUIDED_ANNUAL_SAVINGS_BY_OPTION,
    GUIDED_CAPEX_BY_OPTION,
    GUIDED_INVESTMENT_PROFILES,
    GuidedEconomicInputs,
    InvestmentEconomicProfile,
    _irr,
    _npv,
    _payback,
    compute_guided_economic_analysis,
    compute_investment_comparison,
    current_cost_reference_summary,
)


def approx(actual: float, expected: float, tolerance: float, msg: str) -> None:
    if abs(actual - expected) > tolerance:
        raise AssertionError(f"{msg}: esperado {expected}, obtenido {actual}")
    print(f"  OK {msg}")


def assert_none(value: object, msg: str) -> None:
    if value is not None:
        raise AssertionError(f"{msg}: esperado None, obtenido {value}")
    print(f"  OK {msg}")


def _base_inputs(**kwargs) -> GuidedEconomicInputs:
    values = dict(
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
        discount_rate=0.07,
    )
    values.update(kwargs)
    return GuidedEconomicInputs(**values)


def test_investment_profiles_use_enunciado_values() -> None:
    print("test_investment_profiles_use_enunciado_values")
    if [profile.name for profile in GUIDED_INVESTMENT_PROFILES] != ["Básica", "Estándar", "Premium"]:
        raise AssertionError("Los perfiles deben conservar el orden Basica/Estandar/Premium")
    approx(GUIDED_CAPEX_BY_OPTION["Básica"], 18.3e6, 1e-6, "CAPEX básica")
    approx(GUIDED_CAPEX_BY_OPTION["Estándar"], 28.5e6, 1e-6, "CAPEX estándar")
    approx(GUIDED_CAPEX_BY_OPTION["Premium"], 42.7e6, 1e-6, "CAPEX premium")
    approx(GUIDED_ANNUAL_SAVINGS_BY_OPTION["Básica"], 4.7e6, 1e-6, "ahorro básica")
    approx(GUIDED_ANNUAL_SAVINGS_BY_OPTION["Estándar"], 6.7e6, 1e-6, "ahorro estándar")
    approx(GUIDED_ANNUAL_SAVINGS_BY_OPTION["Premium"], 8.9e6, 1e-6, "ahorro premium")


def test_route_differential_positive_reduces_flow() -> None:
    print("test_route_differential_positive_reduces_flow")
    neutral = compute_guided_economic_analysis(_base_inputs())
    penalized = compute_guided_economic_analysis(
        _base_inputs(route_cost_annual=125.0, route_cost_reference_annual=25.0)
    )
    approx(penalized.route_overcost_annual, 100.0, 1e-12, "diferencial positivo")
    approx(
        penalized.probable_case.annual_flows[0],
        neutral.probable_case.annual_flows[0] - 100.0,
        1e-9,
        "diferencial positivo resta ahorro",
    )


def test_route_differential_negative_improves_flow() -> None:
    print("test_route_differential_negative_improves_flow")
    neutral = compute_guided_economic_analysis(_base_inputs())
    improved = compute_guided_economic_analysis(
        _base_inputs(route_cost_annual=25.0, route_cost_reference_annual=125.0)
    )
    approx(improved.route_overcost_annual, -100.0, 1e-12, "diferencial negativo")
    approx(
        improved.probable_case.annual_flows[0],
        neutral.probable_case.annual_flows[0] + 100.0,
        1e-9,
        "diferencial negativo aumenta ahorro",
    )


def test_model_does_not_contain_fixed_matlab_route_penalty() -> None:
    print("test_model_does_not_contain_fixed_matlab_route_penalty")
    source = inspect.getsource(guided_economics_module)
    forbidden = ("122025", "opex_penalizacion_um")
    for token in forbidden:
        if token in source:
            raise AssertionError(f"No debe aparecer la penalización fija MATLAB: {token}")
    print("  OK sin penalización fija MATLAB")


def test_initial_costs_are_not_annual_opex() -> None:
    print("test_initial_costs_are_not_annual_opex")
    analysis = compute_guided_economic_analysis(
        _base_inputs(
            investment_option_name="Estándar",
            transport_support="Compensación única",
            include_training=True,
            include_dqa4_value_loss=True,
            include_insurance=True,
            include_incentives=True,
            include_phasing=False,
            include_backup=False,
        )
    )
    expected_transition = 1.56e6 + 0.523e6 + 0.45e6 + 0.45e6 + 0.68e6
    approx(analysis.probable_case.transition_initial_cost, expected_transition, 1e-6, "costes iniciales")
    approx(analysis.probable_case.annual_support_cost, 0.0, 1e-6, "compensacion no es OPEX")
    approx(analysis.probable_case.annual_recurring_cost, 0.0, 1e-6, "seguros/incentivos no son OPEX")
    approx(
        analysis.initial_cost_total,
        28.5e6 + expected_transition,
        1e-6,
        "coste inicial total",
    )


def test_public_and_corporate_transport_are_annual_opex() -> None:
    print("test_public_and_corporate_transport_are_annual_opex")
    public = compute_guided_economic_analysis(
        _base_inputs(transport_support="Subsidio transporte público")
    )
    corporate = compute_guided_economic_analysis(
        _base_inputs(transport_support="Transporte corporativo")
    )
    approx(public.probable_case.annual_recurring_cost, 187_000.0, 1e-6, "subsidio anual")
    approx(corporate.probable_case.annual_recurring_cost, 441_000.0, 1e-6, "transporte corporativo anual")


def test_opp_flows_and_pert_are_year_by_year() -> None:
    print("test_opp_flows_and_pert_are_year_by_year")
    profile = InvestmentEconomicProfile("Prueba", 0.0, 100.0)
    analysis = compute_guided_economic_analysis(_base_inputs(horizon_years=3), profile)
    approx(analysis.optimistic_case.annual_flows[0], 120.0, 1e-9, "optimista año 1")
    approx(analysis.probable_case.annual_flows[0], 75.0, 1e-9, "probable año 1")

    operational_risk = analysis.pessimistic_case.operational_risk_year1
    approx(
        analysis.pessimistic_case.annual_flows[0],
        100.0 * 0.80 * 0.50 - operational_risk,
        1e-6,
        "pesimista año 1 con golpe operativo",
    )
    expected_pert_year_1 = (
        analysis.optimistic_case.cash_flows[1]
        + 4.0 * analysis.probable_case.cash_flows[1]
        + analysis.pessimistic_case.cash_flows[1]
    ) / 6.0
    approx(analysis.cash_flows_pert[1], expected_pert_year_1, 1e-9, "PERT año 1")


def test_van_tir_and_payback_helpers() -> None:
    print("test_van_tir_and_payback_helpers")
    cashflows = (-100.0, 60.0, 60.0)
    expected_van = -100.0 + 60.0 / 1.1 + 60.0 / (1.1**2)
    approx(_npv(0.1, cashflows), expected_van, 1e-12, "VAN conocido")
    approx(_irr(cashflows) or 0.0, 0.1306623863, 1e-8, "TIR conocida")
    approx(_payback((-100.0, 30.0, 80.0)) or 0.0, 1.875, 1e-12, "payback conocido")
    assert_none(_irr((-100.0, -10.0, -5.0)), "TIR sin cambio de signo")
    assert_none(_payback((-100.0, 20.0, 20.0)), "payback no recuperado")


def test_residual_risk_after_mitigations() -> None:
    print("test_residual_risk_after_mitigations")
    analysis = compute_guided_economic_analysis(
        _base_inputs(
            investment_option_name="Estándar",
            include_phasing=True,
            include_backup=True,
            include_insurance=True,
            include_incentives=True,
        )
    )
    risks = {risk.name: risk for risk in analysis.risk_lines}
    approx(risks["Interrupción de servicio"].residual_probability, 0.075, 1e-12, "servicio mitigado")
    approx(risks["Problemas empleados"].residual_probability, 0.135, 1e-12, "empleados mitigado")
    approx(risks["Fallos de tecnología"].residual_probability, 0.045, 1e-12, "tecnologia mitigado")
    approx(risks["Problemas legales"].residual_probability, 0.06, 1e-12, "legal mitigado")


def test_pessimistic_case_includes_construction_and_operational_risk() -> None:
    print("test_pessimistic_case_includes_construction_and_operational_risk")
    analysis = compute_guided_economic_analysis(_base_inputs(investment_option_name="Básica"))
    pessimistic = analysis.pessimistic_case
    construction = next(risk for risk in analysis.risk_lines if risk.name == "Sobrecoste construcción")
    operational = sum(risk.residual_expected_cost for risk in analysis.risk_lines if risk.risk_kind == "operational")
    approx(pessimistic.construction_risk_year0, construction.residual_expected_cost, 1e-6, "riesgo construccion año 0")
    approx(pessimistic.operational_risk_year1, operational, 1e-6, "riesgo operativo año 1")
    approx(
        pessimistic.cash_flows[0],
        -(pessimistic.initial_cost_total + construction.residual_expected_cost),
        1e-6,
        "cash flow inicial pesimista",
    )


def test_estimated_annual_cost_pert_excludes_initial_costs() -> None:
    print("test_estimated_annual_cost_pert_excludes_initial_costs")
    no_initial = compute_guided_economic_analysis(
        _base_inputs(include_training=False, include_dqa4_value_loss=False)
    )
    with_initial = compute_guided_economic_analysis(
        _base_inputs(include_training=True, include_dqa4_value_loss=True)
    )
    approx(
        no_initial.estimated_absolute_annual_cost_pert,
        with_initial.estimated_absolute_annual_cost_pert,
        1e-6,
        "coste anual PERT no incluye iniciales",
    )
    expected = CURRENT_TOTAL_ANNUAL_COST - with_initial.average_operating_saving_pert
    approx(with_initial.estimated_absolute_annual_cost_pert, expected, 1e-6, "formula coste anual PERT")


def test_investment_comparison_returns_three_options_and_best() -> None:
    print("test_investment_comparison_returns_three_options_and_best")
    comparison = compute_investment_comparison(_base_inputs())
    if len(comparison.analyses) != 3:
        raise AssertionError("Debe comparar tres opciones")
    if comparison.best_option_name not in {"Básica", "Estándar", "Premium"}:
        raise AssertionError("La mejor opcion debe ser una opcion conocida")
    if len(comparison.decision_matrix) != 4:
        raise AssertionError("La matriz debe tener criterios simples y trazables")
    print(f"  OK mejor opción calculada: {comparison.best_option_name}")


def test_current_cost_reference_uses_enunciado_totals() -> None:
    print("test_current_cost_reference_uses_enunciado_totals")
    summary = current_cost_reference_summary()
    approx(float(summary["total_annual_cost"]), 36.2e6 + 18.1e6 + 1.99e6, 1e-6, "total actual")
    approx(float(summary["transfer_annual_cost"]), 1.99e6, 1e-6, "transferencia explicativa")


def main() -> None:
    test_investment_profiles_use_enunciado_values()
    test_route_differential_positive_reduces_flow()
    test_route_differential_negative_improves_flow()
    test_model_does_not_contain_fixed_matlab_route_penalty()
    test_initial_costs_are_not_annual_opex()
    test_public_and_corporate_transport_are_annual_opex()
    test_opp_flows_and_pert_are_year_by_year()
    test_van_tir_and_payback_helpers()
    test_residual_risk_after_mitigations()
    test_pessimistic_case_includes_construction_and_operational_risk()
    test_estimated_annual_cost_pert_excludes_initial_costs()
    test_investment_comparison_returns_three_options_and_best()
    test_current_cost_reference_uses_enunciado_totals()
    print("\nTodos los tests de economia guiada OK")


if __name__ == "__main__":
    main()
