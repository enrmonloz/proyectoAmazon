"""Modelo económico parametrizable para la unificación SVQ1 + DQA4.

Reimplementa en Python la lógica principal de ``codes/Economia.m`` y añade un
pequeño modelo de costes de flota basado en el Excel de vehículos. La idea es
permitir análisis de sensibilidad desde Streamlit sin ejecutar MATLAB ni Excel.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class CurrentCostParams:
    """Costes actuales anuales en euros."""

    personal_svq1: float = 20.7e6
    personal_dqa4: float = 9.1e6
    energy_svq1: float = 6.2e6
    energy_dqa4: float = 4.7e6
    facilities_svq1: float = 2.4e6
    facilities_dqa4: float = 1.5e6
    other_svq1: float = 7.0e6
    other_dqa4: float = 2.8e6
    transfer_annual_cost: float = 1.99e6
    svq1_daily_units: int = 125_000
    dqa4_daily_packages: int = 38_900
    transfer_daily_packages: int = 26_100
    transfer_distance_km: float = 25.0
    days_per_year: int = 365


@dataclass(frozen=True)
class InvestmentOption:
    """Opción de inversión parametrizable."""

    name: str
    capex_base: float
    capex_infra: float
    capex_tech: float
    capex_it: float
    gross_savings: float
    robots_total: int | None = None


@dataclass(frozen=True)
class AdditionalCostParams:
    """Costes incrementales y decisiones de tratamiento financiero."""

    training_capex: float = 1.56e6
    mitigation_phasing_capex: float = 2.20e6
    mitigation_backup_capex: float = 1.80e6
    incentive_total: float = 0.68e6
    incentive_capex_share: float = 0.50
    insurance_opex: float = 0.45e6
    transport_corporate_opex: float = 441_000.0
    transport_public_opex: float = 187_000.0
    transport_oneoff_capex: float = 450_000.0
    labor_regulation_opex: float = 3.25e6
    transport_support: str = "Subsidio transporte público"
    include_training: bool = True
    include_mitigation_phasing: bool = True
    include_mitigation_backup: bool = True
    include_incentives: bool = True
    include_insurance: bool = True
    include_labor_regulation_as_incremental: bool = False


@dataclass(frozen=True)
class LaborBaselineParams:
    """Datos laborales base extraidos del enunciado."""

    total_employees: int = 915
    svq1_employees: int = 670
    dqa4_affected_employees: int = 245
    additional_commute_km_daily: float = 28.0
    regulation_staff_increase_pct: float = 0.08
    union_notice_months: int = 6
    training_wms_share: float = 0.40
    training_routes_share: float = 0.70
    training_regulation_share: float = 1.00


@dataclass(frozen=True)
class LaborPolicyParams:
    """Politica laboral evaluable de forma independiente a la economia actual."""

    transport_support: str = "Subsidio transporte público"
    include_training: bool = True
    include_incentives: bool = True
    include_labor_regulation_as_incremental: bool = False
    training_capex: float = 1.56e6
    incentive_total: float = 0.68e6
    incentive_capex_share: float = 0.50
    transport_corporate_opex: float = 441_000.0
    transport_public_opex: float = 187_000.0
    transport_oneoff_capex: float = 450_000.0
    labor_regulation_opex: float = 3.25e6
    incentive_effectiveness: float = 0.70
    training_change_resistance_reduction: float = 0.10
    regulation_union_risk_reduction: float = 0.05


@dataclass(frozen=True)
class LaborCostLine:
    """Linea de coste laboral unica o recurrente."""

    concept: str
    amount: float
    kind: str
    included: bool


@dataclass(frozen=True)
class LaborRisk:
    """Riesgo laboral especifico del cambio organizativo."""

    name: str
    probability: float
    cost_if_occurs: float


@dataclass(frozen=True)
class LaborRiskResult:
    """Resultado de riesgo laboral antes y despues de mitigaciones."""

    name: str
    probability: float
    residual_probability: float
    cost_if_occurs: float
    expected_cost: float
    residual_expected_cost: float
    probability_reduction: float


@dataclass(frozen=True)
class LaborImpactSummary:
    """Resumen agregado de costes, riesgos y aceptabilidad laboral."""

    affected_employees: int
    additional_commute_km_daily: float
    oneoff_cost: float
    annual_recurring_cost: float
    expected_risk_cost: float
    residual_risk_cost: float
    first_year_cash_cost: float
    first_year_with_residual_risk: float
    acceptability: str


@dataclass(frozen=True)
class LaborPolicyResult:
    """Resultado reusable para conectar politica laboral, economia y riesgos."""

    baseline: LaborBaselineParams
    policy: LaborPolicyParams
    cost_lines: tuple[LaborCostLine, ...]
    risk_results: tuple[LaborRiskResult, ...]
    summary: LaborImpactSummary


@dataclass(frozen=True)
class FinanceParams:
    """Parámetros financieros de evaluación."""

    discount_rate: float = 0.07
    horizon_years: int = 10
    pessimistic_capex_multiplier: float = 1.30
    pessimistic_savings_multiplier: float = 0.75


@dataclass(frozen=True)
class PessimisticResult:
    """Resultado financiero bajo los multiplicadores pesimistas."""

    capex_total: float
    net_savings_annual: float
    payback: float
    van: float


@dataclass(frozen=True)
class EconomicResult:
    """Resultado estructurado de una opción de inversión."""

    option_name: str
    capex_base: float
    capex_infra: float
    capex_tech: float
    capex_it: float
    capex_transition: float
    capex_total: float
    gross_savings_annual: float
    opex_new_annual: float
    net_savings_annual: float
    payback_net: float
    van: float
    tir: float
    van_over_capex: float
    pessimistic: PessimisticResult
    robots_total: int | None = None

    def to_frame_row(self) -> dict[str, float | str | int | None]:
        """Devuelve la fila compatible con la tabla historica."""
        return {
            "Opción": self.option_name,
            "CAPEX base": self.capex_base,
            "CAPEX transición": self.capex_transition,
            "CAPEX total": self.capex_total,
            "Ahorro bruto anual": self.gross_savings_annual,
            "OPEX nuevo anual": self.opex_new_annual,
            "Ahorro neto anual": self.net_savings_annual,
            "Payback neto": self.payback_net,
            "VAN": self.van,
            "TIR": self.tir,
            "VAN/CAPEX": self.van_over_capex,
            "Payback pesimista": self.pessimistic.payback,
            "VAN pesimista": self.pessimistic.van,
            "Robots": self.robots_total,
        }


@dataclass(frozen=True)
class OperationalSummary:
    """Resumen operativo agregado reusable por economia y futuros escenarios."""

    center_option: str
    depot_name: str
    total_routes: int
    vrp_routes: int
    dedicated_routes: int
    trailer_routes: int
    van_dedicated_routes: int
    total_distance_km: float
    total_time_min: float
    diesel_count: int
    electric_count: int
    total_packages: int


@dataclass(frozen=True)
class LogisticsEconomicsBridge:
    """Traduccion simple entre resultados logisticos y lectura economica."""

    operational_summary: OperationalSummary
    transfer_cost_removed_or_reduced: float
    dqa4_attributable_share: float
    dqa4_liberable_cost_estimate: float
    route_cost_estimate: float
    notes: tuple[str, ...]
    warnings: tuple[str, ...]


@dataclass(frozen=True)
class OperationalEconomicResult:
    """Lectura economica complementaria, sin sustituir el VAN."""

    baseline_current_cost: float
    estimated_transfer_saving: float
    estimated_dqa4_partial_saving: float
    estimated_route_cost_delta: float
    adjusted_operational_saving: float
    interpretation: str
    bridge: LogisticsEconomicsBridge


@dataclass(frozen=True)
class Risk:
    """Riesgo cuantificado por probabilidad e impacto."""

    name: str
    probability: float
    cost_if_occurs: float


@dataclass(frozen=True)
class VehicleCostParams:
    """Costes anuales de vehículos parametrizados desde el Excel."""

    own_vans_no_km_no_diet_count: int = 26
    own_vans_no_km_with_diet_count: int = 19
    own_vans_with_km_diet_count: int = 75
    subcontracted_vans_count: int = 51
    trailer_with_km_diet_count: int = 1
    trailer_without_diet_count: int = 6
    unit_van_no_km_no_diet: float = 48_370.93
    unit_van_no_km_with_diet: float = 54_739.73
    unit_van_with_km_diet: float = 61_012.93
    unit_subcontracted_van: float = 45_000.0
    unit_trailer_with_km_diet: float = 147_422.32
    unit_trailer_without_diet: float = 141_053.52
    baseline_without_unification_millions: float | None = 10.04038638


DEFAULT_OPTIONS: tuple[InvestmentOption, ...] = (
    InvestmentOption("Básica", 18.3e6, 8.5e6, 5.2e6, 2.8e6, 4.7e6, None),
    InvestmentOption("Estándar", 28.5e6, 12.8e6, 8.2e6, 4.1e6, 6.7e6, 650),
    InvestmentOption("Premium", 42.7e6, 18.2e6, 12.5e6, 6.2e6, 8.9e6, None),
)


DEFAULT_RISKS: tuple[Risk, ...] = (
    Risk("Interrupciones de servicio", 0.30, 8.5e6),
    Risk("Problemas con empleados", 0.45, 2.1e6),
    Risk("Fallos de tecnología", 0.30, 3.2e6),
    Risk("Problemas legales/sindicatos", 0.15, 3.0e6),
)


DEFAULT_LABOR_BASELINE = LaborBaselineParams()


DEFAULT_LABOR_RISKS: tuple[LaborRisk, ...] = (
    LaborRisk("Renuncias de empleados", 0.35, 1.28e6),
    LaborRisk("Resistencia al cambio", 0.45, 750_000.0),
    LaborRisk("Conflictos sindicales", 0.25, 2.1e6),
)


OPERATIONAL_OPTION_CURRENT = "Estructura actual"
OPERATIONAL_OPTION_SVQ1_EXPANDED = "SVQ1 ampliado"
OPERATIONAL_OPTION_INTERMEDIATE = "Nuevo centro/intermedio"

OPERATIONAL_OPTIONS: tuple[str, ...] = (
    OPERATIONAL_OPTION_CURRENT,
    OPERATIONAL_OPTION_SVQ1_EXPANDED,
    OPERATIONAL_OPTION_INTERMEDIATE,
)

DEFAULT_DQA4_ATTRIBUTABLE_SHARE = 0.10


LABOR_ACCEPTABILITY_HIGH_MAX = 3.0e6
LABOR_ACCEPTABILITY_MEDIUM_MAX = 6.0e6


_LABOR_TRANSPORT_RISK_REDUCTIONS: dict[str, dict[str, float]] = {
    "Transporte corporativo": {
        "Renuncias de empleados": 0.25,
        "Resistencia al cambio": 0.15,
        "Conflictos sindicales": 0.10,
    },
    "Subsidio transporte público": {
        "Renuncias de empleados": 0.15,
        "Resistencia al cambio": 0.08,
        "Conflictos sindicales": 0.05,
    },
    "Compensación única": {
        "Renuncias de empleados": 0.05,
        "Resistencia al cambio": 0.03,
        "Conflictos sindicales": 0.03,
    },
    "Sin apoyo": {
        "Renuncias de empleados": 0.0,
        "Resistencia al cambio": 0.0,
        "Conflictos sindicales": 0.0,
    },
}


def current_cost_frame(params: CurrentCostParams) -> pd.DataFrame:
    """Desglose de costes actuales."""
    rows = [
        ("Personal", params.personal_svq1, params.personal_dqa4),
        ("Energía/combustible", params.energy_svq1, params.energy_dqa4),
        ("Instalaciones", params.facilities_svq1, params.facilities_dqa4),
        ("Otros gastos", params.other_svq1, params.other_dqa4),
    ]
    df = pd.DataFrame(rows, columns=["Concepto", "SVQ1", "DQA4"])
    df["Total"] = df["SVQ1"] + df["DQA4"]
    transfers = pd.DataFrame(
        [("Transferencias SVQ1-DQA4", params.transfer_annual_cost, 0.0, params.transfer_annual_cost)],
        columns=["Concepto", "SVQ1", "DQA4", "Total"],
    )
    return pd.concat([df, transfers], ignore_index=True)


def total_current_cost(params: CurrentCostParams) -> float:
    return float(current_cost_frame(params)["Total"].sum())


def dqa4_current_cost(params: CurrentCostParams) -> float:
    """Coste anual total asociado a DQA4 en la linea base documentada."""
    return float(
        params.personal_dqa4
        + params.energy_dqa4
        + params.facilities_dqa4
        + params.other_dqa4
    )


def transfer_unit_cost(params: CurrentCostParams) -> float:
    denom = params.transfer_daily_packages * params.days_per_year
    return params.transfer_annual_cost / denom if denom else 0.0


def _validate_non_negative(name: str, value: float) -> None:
    if value < 0:
        raise ValueError(f"{name} no puede ser negativo: {value}")


def _validate_probability(name: str, value: float) -> None:
    if value < 0.0 or value > 1.0:
        raise ValueError(f"{name} debe estar entre 0 y 1: {value}")


def _validate_operational_option(center_option: str) -> None:
    if center_option not in OPERATIONAL_OPTIONS:
        raise ValueError(f"Alternativa operativa no reconocida: {center_option}")


def _validate_dqa4_attributable_share(value: float) -> None:
    if value < 0.0 or value >= 1.0:
        raise ValueError(
            "dqa4_attributable_share debe estar entre 0 y 1 sin representar cierre total: "
            f"{value}"
        )


def _validate_labor_baseline(params: LaborBaselineParams) -> None:
    for name, value in (
        ("total_employees", params.total_employees),
        ("svq1_employees", params.svq1_employees),
        ("dqa4_affected_employees", params.dqa4_affected_employees),
        ("additional_commute_km_daily", params.additional_commute_km_daily),
        ("union_notice_months", params.union_notice_months),
    ):
        _validate_non_negative(name, float(value))
    for name, value in (
        ("regulation_staff_increase_pct", params.regulation_staff_increase_pct),
        ("training_wms_share", params.training_wms_share),
        ("training_routes_share", params.training_routes_share),
        ("training_regulation_share", params.training_regulation_share),
    ):
        _validate_probability(name, value)


def _validate_labor_policy(params: LaborPolicyParams) -> None:
    if params.transport_support not in _LABOR_TRANSPORT_RISK_REDUCTIONS:
        raise ValueError(f"Opción de transporte no reconocida: {params.transport_support}")
    for name, value in (
        ("training_capex", params.training_capex),
        ("incentive_total", params.incentive_total),
        ("transport_corporate_opex", params.transport_corporate_opex),
        ("transport_public_opex", params.transport_public_opex),
        ("transport_oneoff_capex", params.transport_oneoff_capex),
        ("labor_regulation_opex", params.labor_regulation_opex),
    ):
        _validate_non_negative(name, value)
    for name, value in (
        ("incentive_capex_share", params.incentive_capex_share),
        ("incentive_effectiveness", params.incentive_effectiveness),
        ("training_change_resistance_reduction", params.training_change_resistance_reduction),
        ("regulation_union_risk_reduction", params.regulation_union_risk_reduction),
    ):
        _validate_probability(name, value)


def _validate_labor_risk(risk: LaborRisk) -> None:
    _validate_probability(f"{risk.name}.probability", risk.probability)
    _validate_non_negative(f"{risk.name}.cost_if_occurs", risk.cost_if_occurs)


def compute_labor_costs(policy: LaborPolicyParams) -> tuple[float, float, tuple[LaborCostLine, ...]]:
    """Calcula costes laborales unicos y recurrentes de una politica."""
    _validate_labor_policy(policy)
    lines: list[LaborCostLine] = []
    oneoff_cost = 0.0
    annual_recurring_cost = 0.0

    def add(concept: str, amount: float, kind: str, included: bool) -> None:
        lines.append(LaborCostLine(concept=concept, amount=amount, kind=kind, included=included))

    if policy.include_training:
        oneoff_cost += policy.training_capex
    add("Formación empleados", policy.training_capex, "Coste único", policy.include_training)

    incentive_oneoff = policy.incentive_total * policy.incentive_capex_share
    incentive_annual = policy.incentive_total * (1.0 - policy.incentive_capex_share)
    if policy.include_incentives:
        oneoff_cost += incentive_oneoff
        annual_recurring_cost += incentive_annual
    add("Incentivos empleados: bono inicial", incentive_oneoff, "Coste único", policy.include_incentives)
    add("Incentivos empleados: permanencia", incentive_annual, "Recurrente anual", policy.include_incentives)

    if policy.transport_support == "Transporte corporativo":
        annual_recurring_cost += policy.transport_corporate_opex
        add("Apoyo DQA4: transporte corporativo", policy.transport_corporate_opex, "Recurrente anual", True)
    elif policy.transport_support == "Subsidio transporte público":
        annual_recurring_cost += policy.transport_public_opex
        add("Apoyo DQA4: subsidio transporte público", policy.transport_public_opex, "Recurrente anual", True)
    elif policy.transport_support == "Compensación única":
        oneoff_cost += policy.transport_oneoff_capex
        add("Apoyo DQA4: compensación única", policy.transport_oneoff_capex, "Coste único", True)
    elif policy.transport_support == "Sin apoyo":
        add("Apoyo DQA4", 0.0, "No incluido", False)

    if policy.include_labor_regulation_as_incremental:
        annual_recurring_cost += policy.labor_regulation_opex
    add(
        "Regulación laboral 2025",
        policy.labor_regulation_opex,
        "Recurrente anual",
        policy.include_labor_regulation_as_incremental,
    )

    return oneoff_cost, annual_recurring_cost, tuple(lines)


def _labor_probability_reduction(risk_name: str, policy: LaborPolicyParams) -> float:
    remaining_probability_factor = 1.0
    transport_reduction = _LABOR_TRANSPORT_RISK_REDUCTIONS[policy.transport_support].get(risk_name, 0.0)
    remaining_probability_factor *= 1.0 - transport_reduction
    if policy.include_incentives:
        remaining_probability_factor *= 1.0 - policy.incentive_effectiveness
    if policy.include_training and risk_name == "Resistencia al cambio":
        remaining_probability_factor *= 1.0 - policy.training_change_resistance_reduction
    if policy.include_labor_regulation_as_incremental and risk_name == "Conflictos sindicales":
        remaining_probability_factor *= 1.0 - policy.regulation_union_risk_reduction
    return 1.0 - remaining_probability_factor


def compute_labor_risks(
    policy: LaborPolicyParams,
    risks: Iterable[LaborRisk] = DEFAULT_LABOR_RISKS,
) -> tuple[LaborRiskResult, ...]:
    """Calcula riesgo esperado y residual para una politica laboral."""
    _validate_labor_policy(policy)
    results: list[LaborRiskResult] = []
    for risk in risks:
        _validate_labor_risk(risk)
        probability_reduction = _labor_probability_reduction(risk.name, policy)
        residual_probability = risk.probability * (1.0 - probability_reduction)
        results.append(
            LaborRiskResult(
                name=risk.name,
                probability=risk.probability,
                residual_probability=residual_probability,
                cost_if_occurs=risk.cost_if_occurs,
                expected_cost=risk.probability * risk.cost_if_occurs,
                residual_expected_cost=residual_probability * risk.cost_if_occurs,
                probability_reduction=probability_reduction,
            )
        )
    return tuple(results)


def _labor_acceptability(first_year_with_residual_risk: float) -> str:
    if first_year_with_residual_risk <= LABOR_ACCEPTABILITY_HIGH_MAX:
        return "Alta"
    if first_year_with_residual_risk <= LABOR_ACCEPTABILITY_MEDIUM_MAX:
        return "Media"
    return "Baja"


def compute_labor_policy_result(
    policy: LaborPolicyParams,
    baseline: LaborBaselineParams = DEFAULT_LABOR_BASELINE,
    risks: Iterable[LaborRisk] = DEFAULT_LABOR_RISKS,
) -> LaborPolicyResult:
    """Agrupa costes, riesgos residuales y aceptabilidad de una politica laboral."""
    _validate_labor_baseline(baseline)
    oneoff_cost, annual_recurring_cost, cost_lines = compute_labor_costs(policy)
    risk_results = compute_labor_risks(policy, risks)
    expected_risk_cost = sum(result.expected_cost for result in risk_results)
    residual_risk_cost = sum(result.residual_expected_cost for result in risk_results)
    first_year_cash_cost = oneoff_cost + annual_recurring_cost
    first_year_with_residual_risk = first_year_cash_cost + residual_risk_cost
    summary = LaborImpactSummary(
        affected_employees=baseline.dqa4_affected_employees,
        additional_commute_km_daily=baseline.additional_commute_km_daily,
        oneoff_cost=oneoff_cost,
        annual_recurring_cost=annual_recurring_cost,
        expected_risk_cost=expected_risk_cost,
        residual_risk_cost=residual_risk_cost,
        first_year_cash_cost=first_year_cash_cost,
        first_year_with_residual_risk=first_year_with_residual_risk,
        acceptability=_labor_acceptability(first_year_with_residual_risk),
    )
    return LaborPolicyResult(
        baseline=baseline,
        policy=policy,
        cost_lines=cost_lines,
        risk_results=risk_results,
        summary=summary,
    )


def labor_policy_from_additional(additional: AdditionalCostParams) -> LaborPolicyParams:
    """Deriva una politica laboral desde los parametros economicos existentes."""
    return LaborPolicyParams(
        transport_support=additional.transport_support,
        include_training=additional.include_training,
        include_incentives=additional.include_incentives,
        include_labor_regulation_as_incremental=additional.include_labor_regulation_as_incremental,
        training_capex=additional.training_capex,
        incentive_total=additional.incentive_total,
        incentive_capex_share=additional.incentive_capex_share,
        transport_corporate_opex=additional.transport_corporate_opex,
        transport_public_opex=additional.transport_public_opex,
        transport_oneoff_capex=additional.transport_oneoff_capex,
        labor_regulation_opex=additional.labor_regulation_opex,
    )


def labor_policy_result_from_additional(
    additional: AdditionalCostParams,
    baseline: LaborBaselineParams = DEFAULT_LABOR_BASELINE,
    risks: Iterable[LaborRisk] = DEFAULT_LABOR_RISKS,
) -> LaborPolicyResult:
    """Genera el resultado laboral sin modificar el calculo economico actual."""
    return compute_labor_policy_result(labor_policy_from_additional(additional), baseline, risks)


def labor_cost_frame(lines: Iterable[LaborCostLine]) -> pd.DataFrame:
    """Convierte las lineas laborales a una tabla de visualizacion."""
    return pd.DataFrame(
        [
            {
                "Coste laboral": line.concept,
                "Importe": line.amount,
                "Tipo": line.kind,
                "Incluido": line.included,
            }
            for line in lines
        ]
    )


def labor_risk_frame(results: Iterable[LaborRiskResult]) -> pd.DataFrame:
    """Convierte resultados de riesgos laborales a tabla."""
    return pd.DataFrame(
        [
            {
                "Riesgo laboral": result.name,
                "Probabilidad": result.probability,
                "Probabilidad residual": result.residual_probability,
                "Coste si ocurre": result.cost_if_occurs,
                "Valor esperado": result.expected_cost,
                "Valor esperado residual": result.residual_expected_cost,
                "Reducción probabilidad": result.probability_reduction,
            }
            for result in results
        ]
    )


def additional_capex_opex(params: AdditionalCostParams) -> tuple[float, float, pd.DataFrame]:
    """Clasifica costes adicionales como CAPEX u OPEX incremental."""
    rows: list[dict[str, object]] = []

    def add(name: str, amount: float, kind: str, included: bool) -> None:
        rows.append({"Coste": name, "Importe": amount, "Tipo": kind, "Incluido": included})

    capex = 0.0
    opex = 0.0
    if params.include_training:
        capex += params.training_capex
    add("Formación empleados", params.training_capex, "CAPEX", params.include_training)

    if params.include_mitigation_phasing:
        capex += params.mitigation_phasing_capex
    add("Mitigación: implementación por fases", params.mitigation_phasing_capex, "CAPEX", params.include_mitigation_phasing)

    if params.include_mitigation_backup:
        capex += params.mitigation_backup_capex
    add("Mitigación: sistemas de respaldo", params.mitigation_backup_capex, "CAPEX", params.include_mitigation_backup)

    incentive_capex = params.incentive_total * params.incentive_capex_share
    incentive_opex = params.incentive_total * (1.0 - params.incentive_capex_share)
    if params.include_incentives:
        capex += incentive_capex
        opex += incentive_opex
    add("Incentivos empleados: bono inicial", incentive_capex, "CAPEX", params.include_incentives)
    add("Incentivos empleados: permanencia", incentive_opex, "OPEX anual", params.include_incentives)

    if params.include_insurance:
        opex += params.insurance_opex
    add("Seguros especiales", params.insurance_opex, "OPEX anual", params.include_insurance)

    if params.transport_support == "Transporte corporativo":
        opex += params.transport_corporate_opex
        add("Apoyo DQA4: transporte corporativo", params.transport_corporate_opex, "OPEX anual", True)
    elif params.transport_support == "Subsidio transporte público":
        opex += params.transport_public_opex
        add("Apoyo DQA4: subsidio transporte público", params.transport_public_opex, "OPEX anual", True)
    elif params.transport_support == "Compensación única":
        capex += params.transport_oneoff_capex
        add("Apoyo DQA4: compensación única", params.transport_oneoff_capex, "CAPEX", True)
    elif params.transport_support == "Sin apoyo":
        add("Apoyo DQA4", 0.0, "No incluido", False)
    else:
        raise ValueError(f"Opción de transporte no reconocida: {params.transport_support}")

    if params.include_labor_regulation_as_incremental:
        opex += params.labor_regulation_opex
    add(
        "Regulación laboral 2025",
        params.labor_regulation_opex,
        "OPEX anual",
        params.include_labor_regulation_as_incremental,
    )

    return capex, opex, pd.DataFrame(rows)


def npv(rate: float, cashflows: Iterable[float]) -> float:
    return float(sum(cf / (1.0 + rate) ** i for i, cf in enumerate(cashflows)))


def irr(cashflows: Iterable[float]) -> float:
    """TIR por bisección. Devuelve NaN si no hay cambio de signo claro."""
    flows = list(cashflows)

    def f(rate: float) -> float:
        return npv(rate, flows)

    low = -0.95
    high = 2.0
    f_low = f(low)
    f_high = f(high)
    if np.isnan(f_low) or np.isnan(f_high) or f_low * f_high > 0:
        return float("nan")
    for _ in range(120):
        mid = (low + high) / 2.0
        f_mid = f(mid)
        if f_low * f_mid <= 0:
            high = mid
            f_high = f_mid
        else:
            low = mid
            f_low = f_mid
    return (low + high) / 2.0


def _payback(capex: float, annual_net: float) -> float:
    return capex / annual_net if annual_net > 0 else float("inf")


def _compute_economic_result(
    option: InvestmentOption,
    capex_transition: float,
    annual_opex: float,
    finance: FinanceParams,
) -> EconomicResult:
    capex_total = option.capex_base + capex_transition
    annual_net = option.gross_savings - annual_opex
    cashflows = [-capex_total] + [annual_net] * finance.horizon_years
    van = npv(finance.discount_rate, cashflows)
    tir = irr(cashflows)

    capex_pessimistic = capex_total * finance.pessimistic_capex_multiplier
    savings_pessimistic = annual_net * finance.pessimistic_savings_multiplier
    cashflows_pessimistic = [-capex_pessimistic] + [savings_pessimistic] * finance.horizon_years
    pessimistic = PessimisticResult(
        capex_total=capex_pessimistic,
        net_savings_annual=savings_pessimistic,
        payback=_payback(capex_pessimistic, savings_pessimistic),
        van=npv(finance.discount_rate, cashflows_pessimistic),
    )

    return EconomicResult(
        option_name=option.name,
        capex_base=option.capex_base,
        capex_infra=option.capex_infra,
        capex_tech=option.capex_tech,
        capex_it=option.capex_it,
        capex_transition=capex_transition,
        capex_total=capex_total,
        gross_savings_annual=option.gross_savings,
        opex_new_annual=annual_opex,
        net_savings_annual=annual_net,
        payback_net=_payback(capex_total, annual_net),
        van=van,
        tir=tir,
        van_over_capex=van / capex_total if capex_total else float("nan"),
        pessimistic=pessimistic,
        robots_total=option.robots_total,
    )


def compute_economic_result(
    option: InvestmentOption,
    additional: AdditionalCostParams,
    finance: FinanceParams,
) -> EconomicResult:
    """Calcula el resultado estructurado de una opción."""
    capex_transition, annual_opex, _ = additional_capex_opex(additional)
    return _compute_economic_result(option, capex_transition, annual_opex, finance)


def compute_economic_results(
    options: Iterable[InvestmentOption],
    additional: AdditionalCostParams,
    finance: FinanceParams,
) -> tuple[EconomicResult, ...]:
    """Calcula resultados estructurados para varias opciones con los mismos supuestos."""
    capex_transition, annual_opex, _ = additional_capex_opex(additional)
    return tuple(
        _compute_economic_result(option, capex_transition, annual_opex, finance)
        for option in options
    )


def economic_results_frame(results: Iterable[EconomicResult]) -> pd.DataFrame:
    """Convierte resultados estructurados a la tabla historica de economia."""
    return pd.DataFrame([result.to_frame_row() for result in results])


def analyze_options(
    options: Iterable[InvestmentOption],
    additional: AdditionalCostParams,
    finance: FinanceParams,
) -> pd.DataFrame:
    """Calcula CAPEX total, ahorro neto, payback, VAN, TIR y pesimista."""
    return economic_results_frame(compute_economic_results(options, additional, finance))


def recommend_option(results: pd.DataFrame) -> str:
    """Selecciona opción por ranking multicriterio simple."""
    if results.empty:
        return ""
    scores = {row["Opción"]: 0 for _, row in results.iterrows()}
    criteria = [
        ("Payback neto", True),
        ("VAN", False),
        ("TIR", False),
        ("VAN/CAPEX", False),
        ("Payback pesimista", True),
        ("VAN pesimista", False),
    ]
    for col, lower_is_better in criteria:
        values = results[col].replace([np.inf, -np.inf], np.nan)
        if values.isna().all():
            continue
        idx = values.idxmin() if lower_is_better else values.idxmax()
        scores[results.loc[idx, "Opción"]] += 1
    return max(scores, key=scores.get)


def risk_frame(risks: Iterable[Risk], selected_option: InvestmentOption | None = None) -> pd.DataFrame:
    """Tabla de valor esperado de riesgos."""
    rows = []
    for risk in risks:
        cost = risk.cost_if_occurs
        if risk.name.lower().startswith("sobrecostes") and selected_option is not None:
            cost = selected_option.capex_base * 0.30
        rows.append(
            {
                "Riesgo": risk.name,
                "Probabilidad": risk.probability,
                "Coste si ocurre": cost,
                "Valor esperado": risk.probability * cost,
            }
        )
    return pd.DataFrame(rows)


def vehicle_cost_frame(params: VehicleCostParams) -> pd.DataFrame:
    """Calcula costes de flota con la estructura del Excel de vehículos."""
    rows = [
        (
            "Furgonetas propias sin km ni dietas",
            params.own_vans_no_km_no_diet_count,
            params.unit_van_no_km_no_diet,
        ),
        (
            "Furgonetas propias sin km con dietas",
            params.own_vans_no_km_with_diet_count,
            params.unit_van_no_km_with_diet,
        ),
        (
            "Furgonetas propias con km y dietas",
            params.own_vans_with_km_diet_count,
            params.unit_van_with_km_diet,
        ),
        ("Furgonetas subcontratadas", params.subcontracted_vans_count, params.unit_subcontracted_van),
        ("Trailers con km y dietas", params.trailer_with_km_diet_count, params.unit_trailer_with_km_diet),
        ("Trailers sin dietas", params.trailer_without_diet_count, params.unit_trailer_without_diet),
    ]
    df = pd.DataFrame(rows, columns=["Bloque", "Vehículos", "Coste unitario anual"])
    df["Coste anual"] = df["Vehículos"] * df["Coste unitario anual"]
    return df


def vehicle_totals(params: VehicleCostParams) -> dict[str, float]:
    df = vehicle_cost_frame(params)
    vans = df[df["Bloque"].str.contains("Furgonetas")]["Coste anual"].sum()
    trailers = df[df["Bloque"].str.contains("Trailers")]["Coste anual"].sum()
    total = float(vans + trailers)
    baseline = (
        params.baseline_without_unification_millions * 1e6
        if params.baseline_without_unification_millions is not None
        else float("nan")
    )
    return {
        "vans": float(vans),
        "trailers": float(trailers),
        "total": total,
        "baseline": baseline,
        "difference": total - baseline if not np.isnan(baseline) else float("nan"),
    }


def summarize_pipeline_operations(
    pipeline_result,
    center_option: str,
) -> OperationalSummary:
    """Extrae las metricas operativas agregadas del resultado del pipeline."""
    _validate_operational_option(center_option)
    dataset = pipeline_result.dataset
    depot_name = dataset.names[dataset.depot_index]
    return OperationalSummary(
        center_option=center_option,
        depot_name=depot_name,
        total_routes=int(pipeline_result.total_routes),
        vrp_routes=int(pipeline_result.vrp_route_count),
        dedicated_routes=int(pipeline_result.dedicated_route_count),
        trailer_routes=int(pipeline_result.trailer_route_count),
        van_dedicated_routes=int(pipeline_result.van_dedicated_route_count),
        total_distance_km=float(pipeline_result.total_distance_km),
        total_time_min=float(pipeline_result.total_time_min),
        diesel_count=int(pipeline_result.vrp.diesel_count),
        electric_count=int(pipeline_result.vrp.electric_count),
        total_packages=int(pipeline_result.packages.sum()),
    )


def estimate_transfer_saving(
    current_costs: CurrentCostParams,
    center_option: str,
) -> float:
    """Ahorro anual atribuible a reducir la transferencia SVQ1-DQA4."""
    _validate_operational_option(center_option)
    if center_option == OPERATIONAL_OPTION_SVQ1_EXPANDED:
        return float(current_costs.transfer_annual_cost)
    return 0.0


def estimate_dqa4_liberable_cost(
    current_costs: CurrentCostParams,
    attributable_share: float,
) -> float:
    """Estimacion parcial/liberable de DQA4; nunca representa cierre total."""
    _validate_dqa4_attributable_share(attributable_share)
    return dqa4_current_cost(current_costs) * attributable_share


def _operational_bridge_notes_and_warnings(
    summary: OperationalSummary,
    dqa4_attributable_share: float,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    notes: list[str] = [
        "Este bloque es complementario: no sustituye el VAN ni decide la inversion.",
        "Las rutas se mantienen bajo las restricciones actuales de jornada y rango electrico.",
    ]
    warnings: list[str] = []

    if summary.center_option == OPERATIONAL_OPTION_CURRENT:
        notes.append(
            "La estructura actual usa DQA4 como centro de última milla y mantiene la transferencia SVQ1-DQA4."
        )
    elif summary.center_option == OPERATIONAL_OPTION_SVQ1_EXPANDED:
        notes.append(
            "SVQ1 ampliado puede reducir la transferencia del flujo SVQ1-DQA4."
        )
        notes.append(
            f"DQA4 sigue operando; solo se usa un {dqa4_attributable_share:.0%} "
            "como actividad atribuible/liberable."
        )
    elif summary.center_option == OPERATIONAL_OPTION_INTERMEDIATE:
        warnings.append(
            "El centro intermedio solo debe usarse como depot si existe como nodo OD o "
            "si se aproxima explicitamente a un nodo existente."
        )
        notes.append(
            "No se estima ahorro por transferencia reorganizada hasta justificar la matriz OD del candidato."
        )

    return tuple(notes), tuple(warnings)


def estimate_operational_cost_bridge(
    pipeline_result,
    current_costs: CurrentCostParams,
    vehicle_cost_params: VehicleCostParams,
    center_option: str,
    dqa4_attributable_share: float = DEFAULT_DQA4_ATTRIBUTABLE_SHARE,
) -> OperationalEconomicResult:
    """Conecta rutas agregadas con una lectura economica-operativa sencilla."""
    _validate_operational_option(center_option)
    _validate_dqa4_attributable_share(dqa4_attributable_share)

    summary = summarize_pipeline_operations(pipeline_result, center_option)
    transfer_saving = estimate_transfer_saving(current_costs, center_option)
    dqa4_partial_saving = (
        estimate_dqa4_liberable_cost(current_costs, dqa4_attributable_share)
        if center_option == OPERATIONAL_OPTION_SVQ1_EXPANDED
        else 0.0
    )

    totals = vehicle_totals(vehicle_cost_params)
    route_cost_estimate = totals["total"]
    route_cost_delta = (
        totals["difference"]
        if center_option == OPERATIONAL_OPTION_SVQ1_EXPANDED
        and not np.isnan(totals["difference"])
        else 0.0
    )
    adjusted_saving = transfer_saving + dqa4_partial_saving - route_cost_delta

    notes, warnings = _operational_bridge_notes_and_warnings(summary, dqa4_attributable_share)
    bridge = LogisticsEconomicsBridge(
        operational_summary=summary,
        transfer_cost_removed_or_reduced=transfer_saving,
        dqa4_attributable_share=dqa4_attributable_share,
        dqa4_liberable_cost_estimate=dqa4_partial_saving,
        route_cost_estimate=route_cost_estimate,
        notes=notes,
        warnings=warnings,
    )

    if center_option == OPERATIONAL_OPTION_SVQ1_EXPANDED:
        interpretation = (
            "La alternativa SVQ1 ampliado conecta las rutas desde SVQ1 con el ahorro "
            "potencial de transferencia y una liberacion parcial de DQA4. DQA4 no se "
            "cierra: el porcentaje solo representa actividad atribuible al flujo SVQ1-DQA4."
        )
    elif center_option == OPERATIONAL_OPTION_CURRENT:
        interpretation = (
            "La estructura actual sirve como base comparativa: SVQ1 funciona como fulfillment, "
            "DQA4 como centro de última milla, se mantiene la transferencia SVQ1-DQA4 "
            "y no se reconocen ahorros por transferencia ni por DQA4."
        )
    elif center_option == OPERATIONAL_OPTION_INTERMEDIATE:
        interpretation = (
            "El centro intermedio queda como alternativa cautelosa: solo se interpreta "
            "operativamente si el depot usado existe en la matriz OD."
        )
    else:
        raise ValueError(f"Alternativa operativa no reconocida: {center_option}")

    return OperationalEconomicResult(
        baseline_current_cost=total_current_cost(current_costs),
        estimated_transfer_saving=transfer_saving,
        estimated_dqa4_partial_saving=dqa4_partial_saving,
        estimated_route_cost_delta=route_cost_delta,
        adjusted_operational_saving=adjusted_saving,
        interpretation=interpretation,
        bridge=bridge,
    )
