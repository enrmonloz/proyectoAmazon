"""Modelo simple de riesgos dependientes de decisiones.

El modulo calcula riesgo residual como:

    probabilidad base x modificadores de probabilidad
    impacto base x modificadores de impacto

No implementa ScenarioConfig/ScenarioResult ni simulacion avanzada. Su objetivo
es conectar, de forma trazable, las decisiones actuales de centro, rutas,
inversion, politica laboral, cronograma y mitigaciones.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import pandas as pd

from .economics_model import (
    OPERATIONAL_OPTION_CURRENT,
    OPERATIONAL_OPTION_INTERMEDIATE,
    OPERATIONAL_OPTION_SVQ1_EXPANDED,
)


INVESTMENT_BASIC = "Básica"
INVESTMENT_STANDARD = "Estándar"
INVESTMENT_PREMIUM = "Premium"

LABOR_SUPPORT_NONE = "Sin apoyo"
LABOR_ACCEPTABILITY_LOW = "Baja"
LABOR_ACCEPTABILITY_MEDIUM = "Media"

FAVORABLE_START_MONTHS = frozenset({1, 2, 3})


@dataclass(frozen=True)
class RiskFactor:
    """Factor multiplicativo aplicado a probabilidad e impacto."""

    label: str
    probability_multiplier: float = 1.0
    impact_multiplier: float = 1.0


@dataclass(frozen=True)
class RiskDecisionInputs:
    """Entradas agregadas que explican los riesgos residuales."""

    center_option: str = OPERATIONAL_OPTION_CURRENT
    investment_option: str = INVESTMENT_STANDARD
    transport_support: str = "Subsidio transporte público"
    labor_acceptability: str = LABOR_ACCEPTABILITY_MEDIUM
    total_routes: int = 0
    dedicated_routes: int = 0
    trailer_routes: int = 0
    vehicle_count: int = 0
    total_distance_km: float = 0.0
    total_time_min: float = 0.0
    seasonality_multiplier: float = 1.0
    adjusted_operational_saving: float = 0.0
    include_phasing: bool = True
    include_backup_systems: bool = True
    include_training: bool = True
    include_incentives: bool = True
    start_month: int = 1
    critical_peak_milestone_count: int = 0
    high_severity_timeline_warnings: int = 0
    intermediate_center_is_approximate: bool = False

    @property
    def uses_existing_infrastructure(self) -> bool:
        return self.center_option in {
            OPERATIONAL_OPTION_CURRENT,
            OPERATIONAL_OPTION_SVQ1_EXPANDED,
        }

    @property
    def favorable_start_month(self) -> bool:
        return self.start_month in FAVORABLE_START_MONTHS


@dataclass(frozen=True)
class RiskDefinition:
    """Riesgo base antes de decisiones y mitigaciones."""

    name: str
    base_probability: float
    base_impact: float
    explanation: str


@dataclass(frozen=True)
class RiskResult:
    """Resultado completo de un riesgo antes y despues de decisiones."""

    name: str
    base_probability: float
    base_impact: float
    residual_probability: float
    residual_impact: float
    base_expected_cost: float
    residual_expected_cost: float
    factors: tuple[RiskFactor, ...]
    explanation: str

    @property
    def factor_labels(self) -> tuple[str, ...]:
        return tuple(factor.label for factor in self.factors)


@dataclass(frozen=True)
class RiskAssessment:
    """Conjunto de riesgos calculados con totales agregados."""

    inputs: RiskDecisionInputs
    risks: tuple[RiskResult, ...]

    @property
    def total_base_expected_cost(self) -> float:
        return sum(risk.base_expected_cost for risk in self.risks)

    @property
    def total_residual_expected_cost(self) -> float:
        return sum(risk.residual_expected_cost for risk in self.risks)


DEFAULT_RISK_DEFINITIONS: tuple[RiskDefinition, ...] = (
    RiskDefinition(
        "Operativo",
        0.30,
        8.5e6,
        "Riesgo de interrupciones o complejidad operativa durante la transición.",
    ),
    RiskDefinition(
        "Tecnológico",
        0.30,
        3.2e6,
        "Riesgo de fallos de sistemas, integración o continuidad tecnológica.",
    ),
    RiskDefinition(
        "Laboral",
        0.40,
        2.1e6,
        "Riesgo asociado a adaptación, desplazamientos y aceptación de empleados.",
    ),
    RiskDefinition(
        "Financiero",
        0.25,
        5.0e6,
        "Riesgo de sobrecostes, ahorro insuficiente o mayor exposición de capital.",
    ),
    RiskDefinition(
        "Cronograma",
        0.25,
        2.5e6,
        "Riesgo de que hitos críticos coincidan con meses operativamente sensibles.",
    ),
    RiskDefinition(
        "Legal/sindical",
        0.15,
        3.0e6,
        "Riesgo de negociación, cumplimiento laboral o conflicto sindical.",
    ),
)


def assess_risks(
    inputs: RiskDecisionInputs,
    definitions: Iterable[RiskDefinition] = DEFAULT_RISK_DEFINITIONS,
) -> RiskAssessment:
    """Calcula el riesgo residual por categoria."""

    results = tuple(
        _apply_factors(definition, _factors_for(definition.name, inputs))
        for definition in definitions
    )
    return RiskAssessment(inputs=inputs, risks=results)


def risk_results_frame(results: Iterable[RiskResult]) -> pd.DataFrame:
    """Convierte resultados de riesgo a una tabla de visualizacion."""

    return pd.DataFrame(
        [
            {
                "Riesgo": result.name,
                "Probabilidad base": result.base_probability,
                "Probabilidad tras decisiones": result.residual_probability,
                "Impacto base si ocurre": result.base_impact,
                "Impacto si ocurre": result.residual_impact,
                "Coste medio base": result.base_expected_cost,
                "Coste medio estimado": result.residual_expected_cost,
                "Factores aplicados": "; ".join(result.factor_labels) or "Sin modificadores",
                "Explicación breve": result.explanation,
            }
            for result in results
        ]
    )


def _apply_factors(definition: RiskDefinition, factors: tuple[RiskFactor, ...]) -> RiskResult:
    probability = definition.base_probability
    impact = definition.base_impact
    for factor in factors:
        probability *= factor.probability_multiplier
        impact *= factor.impact_multiplier

    residual_probability = _clamp_probability(probability)
    residual_impact = max(0.0, impact)
    return RiskResult(
        name=definition.name,
        base_probability=definition.base_probability,
        base_impact=definition.base_impact,
        residual_probability=residual_probability,
        residual_impact=residual_impact,
        base_expected_cost=definition.base_probability * definition.base_impact,
        residual_expected_cost=residual_probability * residual_impact,
        factors=factors,
        explanation=definition.explanation,
    )


def _factors_for(risk_name: str, inputs: RiskDecisionInputs) -> tuple[RiskFactor, ...]:
    if risk_name == "Operativo":
        return _operational_factors(inputs)
    if risk_name == "Tecnológico":
        return _technology_factors(inputs)
    if risk_name == "Laboral":
        return _labor_factors(inputs)
    if risk_name == "Financiero":
        return _financial_factors(inputs)
    if risk_name == "Cronograma":
        return _schedule_factors(inputs)
    if risk_name == "Legal/sindical":
        return _legal_union_factors(inputs)
    return ()


def _operational_factors(inputs: RiskDecisionInputs) -> tuple[RiskFactor, ...]:
    factors: list[RiskFactor] = []
    if inputs.total_routes >= 100:
        factors.append(RiskFactor("muchas rutas", 1.25, 1.05))
    elif inputs.total_routes >= 60:
        factors.append(RiskFactor("volumen alto de rutas", 1.15, 1.02))
    elif inputs.total_routes >= 30:
        factors.append(RiskFactor("volumen medio de rutas", 1.08, 1.0))

    if inputs.dedicated_routes >= 10:
        factors.append(RiskFactor("muchas rutas dedicadas", 1.20, 1.05))
    elif inputs.dedicated_routes >= 5:
        factors.append(RiskFactor("rutas dedicadas relevantes", 1.10, 1.02))

    if inputs.seasonality_multiplier >= 1.20:
        factors.append(RiskFactor("temporada alta", 1.25, 1.10))
    elif inputs.seasonality_multiplier >= 1.08:
        factors.append(RiskFactor("temporada media-alta", 1.10, 1.03))

    if inputs.intermediate_center_is_approximate:
        factors.append(RiskFactor("centro intermedio aproximado", 1.15, 1.10))

    if inputs.include_phasing:
        factors.append(RiskFactor("implementación por fases", 0.82, 0.90))
    if inputs.high_severity_timeline_warnings == 0 and inputs.favorable_start_month:
        factors.append(RiskFactor("cronograma favorable", 0.90, 1.0))
    return tuple(factors)


def _technology_factors(inputs: RiskDecisionInputs) -> tuple[RiskFactor, ...]:
    factors: list[RiskFactor] = []
    if inputs.investment_option == INVESTMENT_BASIC:
        factors.append(RiskFactor("inversión básica", 1.25, 1.10))
    elif inputs.investment_option == INVESTMENT_STANDARD:
        factors.append(RiskFactor("inversión estándar", 0.95, 1.0))
    elif inputs.investment_option == INVESTMENT_PREMIUM:
        factors.append(RiskFactor("inversión premium", 0.90, 0.95))

    if inputs.include_backup_systems:
        factors.append(RiskFactor("sistemas de respaldo", 0.75, 0.90))
    else:
        factors.append(RiskFactor("sin sistemas de respaldo", 1.35, 1.15))
    return tuple(factors)


def _labor_factors(inputs: RiskDecisionInputs) -> tuple[RiskFactor, ...]:
    factors: list[RiskFactor] = []
    if inputs.transport_support == LABOR_SUPPORT_NONE:
        factors.append(RiskFactor("sin apoyo laboral", 1.30, 1.10))
    elif inputs.transport_support == "Transporte corporativo":
        factors.append(RiskFactor("apoyo transporte corporativo", 0.85, 0.95))
    elif inputs.transport_support == "Subsidio transporte público":
        factors.append(RiskFactor("apoyo transporte público", 0.92, 0.97))
    elif inputs.transport_support == "Compensación única":
        factors.append(RiskFactor("compensación laboral", 0.95, 0.98))

    if inputs.labor_acceptability == LABOR_ACCEPTABILITY_LOW:
        factors.append(RiskFactor("baja aceptabilidad laboral", 1.25, 1.15))
    elif inputs.labor_acceptability == LABOR_ACCEPTABILITY_MEDIUM:
        factors.append(RiskFactor("aceptabilidad laboral media", 1.10, 1.0))

    if inputs.include_incentives:
        factors.append(RiskFactor("incentivos", 0.80, 0.95))
    if inputs.include_training:
        factors.append(RiskFactor("formación", 0.90, 0.95))
    return tuple(factors)


def _financial_factors(inputs: RiskDecisionInputs) -> tuple[RiskFactor, ...]:
    factors: list[RiskFactor] = []
    if inputs.center_option == OPERATIONAL_OPTION_INTERMEDIATE:
        factors.append(RiskFactor("nuevo centro/intermedio", 1.25, 1.20))
    if inputs.investment_option == INVESTMENT_PREMIUM:
        factors.append(RiskFactor("inversión premium", 1.20, 1.15))
    elif inputs.investment_option == INVESTMENT_BASIC:
        factors.append(RiskFactor("menor CAPEX inicial", 0.95, 0.95))

    if inputs.adjusted_operational_saving <= 0.0:
        factors.append(RiskFactor("ahorro operativo ajustado bajo o negativo", 1.35, 1.20))
    elif inputs.adjusted_operational_saving < 1.0e6:
        factors.append(RiskFactor("ahorro operativo ajustado bajo", 1.20, 1.10))
    elif inputs.adjusted_operational_saving < 3.0e6:
        factors.append(RiskFactor("ahorro operativo ajustado moderado", 1.10, 1.0))
    else:
        factors.append(RiskFactor("ahorro operativo positivo", 0.90, 0.95))

    if inputs.uses_existing_infrastructure:
        factors.append(RiskFactor("infraestructura existente", 0.90, 0.90))
    return tuple(factors)


def _schedule_factors(inputs: RiskDecisionInputs) -> tuple[RiskFactor, ...]:
    factors: list[RiskFactor] = []
    if inputs.critical_peak_milestone_count > 0:
        factors.append(RiskFactor("hitos en octubre-diciembre", 1.25, 1.10))
    if inputs.high_severity_timeline_warnings > 0:
        warning_multiplier = min(1.45, 1.0 + 0.15 * inputs.high_severity_timeline_warnings)
        factors.append(RiskFactor("alertas altas del cronograma", warning_multiplier, 1.10))

    if inputs.favorable_start_month:
        factors.append(RiskFactor("mes de inicio favorable", 0.90, 1.0))
    if inputs.include_phasing:
        factors.append(RiskFactor("transición por fases", 0.82, 0.90))
    else:
        factors.append(RiskFactor("sin transición por fases", 1.15, 1.05))
    return tuple(factors)


def _legal_union_factors(inputs: RiskDecisionInputs) -> tuple[RiskFactor, ...]:
    factors: list[RiskFactor] = []
    if inputs.labor_acceptability == LABOR_ACCEPTABILITY_LOW:
        factors.append(RiskFactor("baja aceptabilidad laboral", 1.35, 1.15))
    elif inputs.labor_acceptability == LABOR_ACCEPTABILITY_MEDIUM:
        factors.append(RiskFactor("aceptabilidad laboral media", 1.10, 1.0))

    if inputs.transport_support == LABOR_SUPPORT_NONE:
        factors.append(RiskFactor("sin apoyo laboral", 1.15, 1.05))
    else:
        factors.append(RiskFactor("apoyo laboral", 0.85, 0.95))

    if inputs.include_phasing:
        factors.append(RiskFactor("fases", 0.90, 0.95))
    else:
        factors.append(RiskFactor("sin transición por fases", 1.20, 1.10))

    if inputs.include_training:
        factors.append(RiskFactor("formación", 0.90, 0.95))
    return tuple(factors)


def _clamp_probability(value: float) -> float:
    return min(1.0, max(0.0, value))
