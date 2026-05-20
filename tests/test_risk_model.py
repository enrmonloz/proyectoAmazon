"""Tests minimos del modelo de riesgos dependiente de decisiones."""

from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.economics_model import (
    OPERATIONAL_OPTION_CURRENT,
    OPERATIONAL_OPTION_INTERMEDIATE,
)
from src.risk_model import RiskDecisionInputs, RiskDefinition, assess_risks


def _risk_by_name(assessment, name: str):
    return next(risk for risk in assessment.risks if risk.name == name)


def test_phasing_reduces_operational_risk() -> None:
    print("test_phasing_reduces_operational_risk")
    base = RiskDecisionInputs(
        total_routes=80,
        dedicated_routes=8,
        seasonality_multiplier=1.25,
        include_phasing=False,
    )
    phased = replace(base, include_phasing=True)
    without_phasing = _risk_by_name(assess_risks(base), "Operativo")
    with_phasing = _risk_by_name(assess_risks(phased), "Operativo")
    if with_phasing.residual_expected_cost >= without_phasing.residual_expected_cost:
        raise AssertionError("La implementacion por fases debe reducir el riesgo operativo")
    print("  OK fases reducen riesgo operativo")


def test_backup_reduces_technology_risk() -> None:
    print("test_backup_reduces_technology_risk")
    base = RiskDecisionInputs(
        investment_option="Básica",
        include_backup_systems=False,
    )
    with_backup = replace(base, include_backup_systems=True)
    no_backup_risk = _risk_by_name(assess_risks(base), "Tecnológico")
    backup_risk = _risk_by_name(assess_risks(with_backup), "Tecnológico")
    if backup_risk.residual_expected_cost >= no_backup_risk.residual_expected_cost:
        raise AssertionError("Los sistemas de respaldo deben reducir el riesgo tecnologico")
    print("  OK respaldo reduce riesgo tecnologico")


def test_intermediate_center_increases_financial_risk() -> None:
    print("test_intermediate_center_increases_financial_risk")
    current = RiskDecisionInputs(
        center_option=OPERATIONAL_OPTION_CURRENT,
        adjusted_operational_saving=2.0e6,
    )
    intermediate = replace(
        current,
        center_option=OPERATIONAL_OPTION_INTERMEDIATE,
        intermediate_center_is_approximate=True,
    )
    current_financial = _risk_by_name(assess_risks(current), "Financiero")
    intermediate_financial = _risk_by_name(assess_risks(intermediate), "Financiero")
    if intermediate_financial.residual_expected_cost <= current_financial.residual_expected_cost:
        raise AssertionError("El nuevo centro/intermedio debe aumentar el riesgo financiero")
    print("  OK centro intermedio aumenta riesgo financiero")


def test_probabilities_remain_between_zero_and_one() -> None:
    print("test_probabilities_remain_between_zero_and_one")
    inputs = RiskDecisionInputs(
        center_option=OPERATIONAL_OPTION_INTERMEDIATE,
        investment_option="Premium",
        transport_support="Sin apoyo",
        labor_acceptability="Baja",
        total_routes=200,
        dedicated_routes=50,
        seasonality_multiplier=1.25,
        adjusted_operational_saving=-1.0,
        include_phasing=False,
        include_backup_systems=False,
        include_training=False,
        include_incentives=False,
        critical_peak_milestone_count=4,
        high_severity_timeline_warnings=5,
        intermediate_center_is_approximate=True,
    )
    definitions = (RiskDefinition("Operativo", 0.95, 1.0e6, "Prueba de clamp"),)
    assessment = assess_risks(inputs, definitions)
    for risk in assessment.risks:
        if not 0.0 <= risk.residual_probability <= 1.0:
            raise AssertionError("La probabilidad residual debe quedar entre 0 y 1")
    print("  OK probabilidades acotadas")


def main() -> None:
    test_phasing_reduces_operational_risk()
    test_backup_reduces_technology_risk()
    test_intermediate_center_increases_financial_risk()
    test_probabilities_remain_between_zero_and_one()
    print("\nTodos los tests de riesgos OK")


if __name__ == "__main__":
    main()
