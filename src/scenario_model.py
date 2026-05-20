"""Capa superior sencilla para agrupar decisiones y resultados de escenario.

Este modulo no ejecuta el VRP ni reimplementa economia, riesgos o cronograma.
Solo coordina los modelos existentes para construir una lectura integrada.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import pandas as pd

from .economics_model import (
    DEFAULT_DQA4_ATTRIBUTABLE_SHARE,
    DEFAULT_OPTIONS,
    AdditionalCostParams,
    CurrentCostParams,
    EconomicResult,
    FinanceParams,
    LaborPolicyResult,
    OPERATIONAL_OPTION_CURRENT,
    OPERATIONAL_OPTION_INTERMEDIATE,
    OperationalEconomicResult,
    VehicleCostParams,
    compute_economic_result,
    estimate_operational_cost_bridge,
    labor_policy_result_from_additional,
)
from .risk_model import RiskAssessment, RiskDecisionInputs, assess_risks
from .timeline_model import TimelineResult, build_timeline


NO_ROUTES_WARNING = "No hay rutas calculadas; el escenario no incluye resumen operativo real."


@dataclass(frozen=True)
class ScenarioConfig:
    """Decisiones principales que definen una lectura de escenario."""

    name: str = "Escenario actual"
    center_option: str = OPERATIONAL_OPTION_CURRENT
    investment_option_name: str = "Estándar"
    transport_support: str = "Subsidio transporte público"
    include_phasing: bool = True
    include_backup: bool = True
    include_training: bool = True
    include_incentives: bool = True
    include_insurance: bool = True
    include_labor_regulation: bool = False
    start_month: int = 1
    dqa4_attributable_share: float = DEFAULT_DQA4_ATTRIBUTABLE_SHARE
    notes: tuple[str, ...] = ()


@dataclass(frozen=True)
class ScenarioResult:
    """Resultados integrados producidos por los modelos existentes."""

    config: ScenarioConfig
    economic_result: EconomicResult
    operational_economic_result: OperationalEconomicResult | None
    labor_result: LaborPolicyResult
    timeline_result: TimelineResult
    risk_assessment: RiskAssessment
    total_expected_risk_cost: float
    adjusted_operational_saving: float
    net_savings_annual: float
    capex_total: float
    warnings: tuple[str, ...]
    interpretation: str


def build_scenario_result(
    config: ScenarioConfig,
    pipeline_result=None,
    route_params: dict | None = None,
) -> ScenarioResult:
    """Construye una lectura integrada sin recalcular rutas internamente."""

    option = _investment_option_by_name(config.investment_option_name)
    additional = AdditionalCostParams(
        transport_support=config.transport_support,
        include_training=config.include_training,
        include_mitigation_phasing=config.include_phasing,
        include_mitigation_backup=config.include_backup,
        include_incentives=config.include_incentives,
        include_insurance=config.include_insurance,
        include_labor_regulation_as_incremental=config.include_labor_regulation,
    )

    economic_result = compute_economic_result(option, additional, FinanceParams())
    labor_result = labor_policy_result_from_additional(additional)
    timeline_result = build_timeline(config.start_month)

    warnings: list[str] = []
    operational_economic_result: OperationalEconomicResult | None = None
    if pipeline_result is None:
        warnings.append(NO_ROUTES_WARNING)
    else:
        operational_economic_result = estimate_operational_cost_bridge(
            pipeline_result=pipeline_result,
            current_costs=CurrentCostParams(),
            vehicle_cost_params=VehicleCostParams(),
            center_option=config.center_option,
            dqa4_attributable_share=config.dqa4_attributable_share,
        )
        warnings.extend(operational_economic_result.bridge.warnings)

    summary = (
        operational_economic_result.bridge.operational_summary
        if operational_economic_result is not None
        else None
    )
    adjusted_operational_saving = (
        operational_economic_result.adjusted_operational_saving
        if operational_economic_result is not None
        else 0.0
    )
    critical_peak_milestones = sum(
        1 for milestone in timeline_result.milestones if milestone.in_critical_peak
    )

    risk_inputs = RiskDecisionInputs(
        center_option=config.center_option,
        investment_option=config.investment_option_name,
        transport_support=config.transport_support,
        labor_acceptability=labor_result.summary.acceptability,
        total_routes=summary.total_routes if summary is not None else 0,
        dedicated_routes=summary.dedicated_routes if summary is not None else 0,
        trailer_routes=summary.trailer_routes if summary is not None else 0,
        vehicle_count=(
            summary.diesel_count + summary.electric_count
            if summary is not None
            else 0
        ),
        total_distance_km=summary.total_distance_km if summary is not None else 0.0,
        total_time_min=summary.total_time_min if summary is not None else 0.0,
        seasonality_multiplier=_route_seasonality(route_params),
        adjusted_operational_saving=adjusted_operational_saving,
        include_phasing=config.include_phasing,
        include_backup_systems=config.include_backup,
        include_training=config.include_training,
        include_incentives=config.include_incentives,
        start_month=config.start_month,
        critical_peak_milestone_count=critical_peak_milestones,
        high_severity_timeline_warnings=timeline_result.high_severity_warning_count,
        intermediate_center_is_approximate=(
            config.center_option == OPERATIONAL_OPTION_INTERMEDIATE
        ),
    )
    risk_assessment = assess_risks(risk_inputs)

    return ScenarioResult(
        config=config,
        economic_result=economic_result,
        operational_economic_result=operational_economic_result,
        labor_result=labor_result,
        timeline_result=timeline_result,
        risk_assessment=risk_assessment,
        total_expected_risk_cost=risk_assessment.total_residual_expected_cost,
        adjusted_operational_saving=adjusted_operational_saving,
        net_savings_annual=economic_result.net_savings_annual,
        capex_total=economic_result.capex_total,
        warnings=tuple(warnings),
        interpretation=_build_interpretation(
            config,
            operational_economic_result,
            economic_result,
            risk_assessment,
        ),
    )


def scenario_result_to_frame_row(result: ScenarioResult) -> dict[str, object]:
    """Devuelve una fila resumida para tablas de escenario."""

    return {
        "Escenario": result.config.name,
        "Centro": result.config.center_option,
        "Inversión": result.config.investment_option_name,
        "CAPEX total": result.capex_total,
        "Ahorro neto anual": result.net_savings_annual,
        "Ahorro operativo ajustado": result.adjusted_operational_saving,
        "Coste riesgo": result.total_expected_risk_cost,
        "Aceptabilidad laboral": result.labor_result.summary.acceptability,
        "Alertas altas cronograma": result.timeline_result.high_severity_warning_count,
    }


def scenario_results_frame(results: Iterable[ScenarioResult]) -> pd.DataFrame:
    """Construye una tabla resumen con una fila por escenario."""

    return pd.DataFrame([scenario_result_to_frame_row(result) for result in results])


def _investment_option_by_name(name: str):
    for option in DEFAULT_OPTIONS:
        if option.name == name:
            return option
    valid = ", ".join(option.name for option in DEFAULT_OPTIONS)
    raise ValueError(f"Opción de inversión no reconocida: {name}. Opciones: {valid}")


def _route_seasonality(route_params: dict | None) -> float:
    if route_params is None:
        return 1.0
    return float(route_params.get("seasonality_multiplier", 1.0))


def _build_interpretation(
    config: ScenarioConfig,
    operational_result: OperationalEconomicResult | None,
    economic_result: EconomicResult,
    risk_assessment: RiskAssessment,
) -> str:
    operational_text = (
        "Incluye rutas calculadas y el puente operativo-económico existente."
        if operational_result is not None
        else "No incluye resumen operativo real porque todavía no hay rutas calculadas."
    )
    return (
        f"{config.name} agrupa la alternativa {config.center_option}, inversión "
        f"{config.investment_option_name} y política laboral '{config.transport_support}'. "
        f"{operational_text} CAPEX total {economic_result.capex_total / 1e6:.2f} M€, "
        f"ahorro neto anual {economic_result.net_savings_annual / 1e6:.2f} M€ y "
        f"coste medio residual de riesgos {risk_assessment.total_residual_expected_cost / 1e6:.2f} M€. "
        "Es una lectura integrada preliminar, no una recomendación automática."
    )
