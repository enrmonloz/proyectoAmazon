"""Modelo economico guiado y sencillo para FG/Analisis economico.

El bloque guiado usa solo el diferencial de costes de rutas frente a DQA4,
aplica una lectura Beta-PERT simple sobre el ahorro anual y mantiene fuera la
economia avanzada del resto de la aplicacion.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


GUIDED_HORIZON_YEARS = 15
GUIDED_DISCOUNT_RATE = 0.08
GUIDED_TRANSFER_ELIMINATED_ANNUAL = 1.99e6

CURRENT_SVQ1_ANNUAL_COST = 36.2e6
CURRENT_DQA4_ANNUAL_COST = 18.1e6
CURRENT_TRANSFER_ANNUAL_COST = 1.99e6
CURRENT_TOTAL_ANNUAL_COST = 56.29e6

CURRENT_COST_BREAKDOWN: dict[str, dict[str, float]] = {
    "SVQ1": {
        "personal": 20.7e6,
        "energy_fuel": 6.2e6,
        "facilities": 2.4e6,
        "other": 7.0e6,
    },
    "DQA4": {
        "personal": 9.1e6,
        "energy_fuel": 4.7e6,
        "facilities": 1.5e6,
        "other": 2.8e6,
    },
}

GUIDED_CAPEX_BY_OPTION: dict[str, float] = {
    "Básica": 18.3e6,
    "Estándar": 28.5e6,
    "Premium": 42.7e6,
}

GUIDED_SUPPORT_ANNEX_COSTS: dict[str, float] = {
    "Sin apoyo": 0.0,
    "Subsidio transporte público": 187_000.0,
    "Transporte corporativo": 441_000.0,
    "Compensación única": 0.0,
}

GUIDED_SUPPORT_CAPEX: dict[str, float] = {
    "Sin apoyo": 0.0,
    "Subsidio transporte público": 0.0,
    "Transporte corporativo": 0.0,
    "Compensación única": 450_000.0,
}


@dataclass(frozen=True)
class GuidedSavingsProfile:
    """Ahorros anuales centrales para un caso."""

    case_name: str
    personal: float
    energy: float
    one_installation: float


GUIDED_SCENARIO_SAVINGS: tuple[GuidedSavingsProfile, ...] = (
    GuidedSavingsProfile("Optimista", 4.1e6, 2.3e6, 1.5e6),
    GuidedSavingsProfile("Probable", 3.25e6, 1.95e6, 0.85e6),
    GuidedSavingsProfile("Pesimista", 2.4e6, 1.6e6, 0.2e6),
)


@dataclass(frozen=True)
class GuidedEconomicInputs:
    """Parametros compartidos por el analisis guiado."""

    alternative: str
    investment_option_name: str
    transport_support: str
    route_cost_annual: float
    route_cost_reference_annual: float
    include_training: bool = True
    include_dqa4_value_loss: bool = True
    include_phasing: bool = False
    include_backup: bool = False
    include_insurance: bool = False
    include_incentives: bool = False
    discount_rate: float = GUIDED_DISCOUNT_RATE
    horizon_years: int = GUIDED_HORIZON_YEARS


@dataclass(frozen=True)
class GuidedMitigationLine:
    """Mitigacion aplicada y su coste asociado."""

    name: str
    capex: float
    applied: bool
    risk_targets: tuple[str, ...]


@dataclass(frozen=True)
class GuidedRiskLine:
    """Riesgo simple con valor esperado antes y despues de mitigaciones."""

    name: str
    probability: float
    impact: float
    expected_cost: float
    residual_probability: float
    residual_expected_cost: float
    mitigation_names: tuple[str, ...]


@dataclass(frozen=True)
class GuidedEconomicCaseResult:
    """Resultado de un caso economico guiado."""

    case_name: str
    alternative: str
    investment_option_name: str
    transport_support: str
    route_cost_annual: float
    route_cost_reference_annual: float
    route_overcost_annual: float
    capex_base: float
    capex_transition: float
    capex_risk_expected: float
    capex_total: float
    annual_support_cost: float
    annual_technology_failure_cost: float
    annual_recurring_cost: float
    annual_flows: tuple[float, ...]
    cash_flows: tuple[float, ...]
    learning_factors: tuple[float, ...]
    ahorro_neto_promedio: float
    current_total_annual_cost: float
    estimated_absolute_annual_cost: float
    van: float
    payback: float
    savings_profile: GuidedSavingsProfile
    risk_lines: tuple[GuidedRiskLine, ...]
    mitigation_lines: tuple[GuidedMitigationLine, ...]


@dataclass(frozen=True)
class GuidedEconomicAnalysisResult:
    """Resultado agregado para los tres casos guiados."""

    alternative: str
    route_cost_annual: float
    route_cost_reference_annual: float
    route_overcost_annual: float
    cases: tuple[GuidedEconomicCaseResult, ...]
    ahorro_pert: float
    sigma: float

    @property
    def optimistic_case(self) -> GuidedEconomicCaseResult:
        return self.cases[0]

    @property
    def probable_case(self) -> GuidedEconomicCaseResult:
        return self.cases[1]

    @property
    def pessimistic_case(self) -> GuidedEconomicCaseResult:
        return self.cases[2]


def compute_guided_economic_case(
    inputs: GuidedEconomicInputs,
    savings_profile: GuidedSavingsProfile,
) -> GuidedEconomicCaseResult:
    """Calcula un caso guiado a partir de un perfil de ahorros y la ruta."""

    _validate_guided_inputs(inputs)
    _validate_guided_savings_profile(savings_profile)

    capex_base = GUIDED_CAPEX_BY_OPTION[inputs.investment_option_name]
    mitigation_lines = _build_mitigation_lines(inputs)
    risk_lines = _build_risk_lines(mitigation_lines)

    capex_transition = 0.0
    if inputs.include_training:
        capex_transition += 1.56e6
    if inputs.include_dqa4_value_loss:
        capex_transition += 0.523e6
    if inputs.transport_support == "Compensación única":
        capex_transition += GUIDED_SUPPORT_CAPEX[inputs.transport_support]
    capex_transition += sum(line.capex for line in mitigation_lines if line.applied)

    capex_risk_expected = sum(line.residual_expected_cost for line in risk_lines)
    capex_total = capex_base + capex_transition + capex_risk_expected

    annual_support_cost = GUIDED_SUPPORT_ANNEX_COSTS[inputs.transport_support]
    annual_technology_failure_cost = _annual_technology_failure_cost(inputs)
    route_overcost_annual = inputs.route_cost_annual - inputs.route_cost_reference_annual
    annual_recurring_cost = annual_support_cost + annual_technology_failure_cost + route_overcost_annual

    learning_factors = tuple(_learning_factor(year) for year in range(1, inputs.horizon_years + 1))
    annual_flows = tuple(
        _annual_cash_flow(
            savings_profile,
            factor,
            annual_recurring_cost,
        )
        for factor in learning_factors
    )
    cash_flows = (-capex_total, *annual_flows)
    ahorro_neto_promedio = sum(annual_flows) / len(annual_flows) if annual_flows else 0.0
    estimated_absolute_annual_cost = CURRENT_TOTAL_ANNUAL_COST - ahorro_neto_promedio
    van = _npv(inputs.discount_rate, cash_flows)
    payback = capex_total / ahorro_neto_promedio if ahorro_neto_promedio > 0 else float("inf")

    return GuidedEconomicCaseResult(
        case_name=savings_profile.case_name,
        alternative=inputs.alternative,
        investment_option_name=inputs.investment_option_name,
        transport_support=inputs.transport_support,
        route_cost_annual=inputs.route_cost_annual,
        route_cost_reference_annual=inputs.route_cost_reference_annual,
        route_overcost_annual=route_overcost_annual,
        capex_base=capex_base,
        capex_transition=capex_transition,
        capex_risk_expected=capex_risk_expected,
        capex_total=capex_total,
        annual_support_cost=annual_support_cost,
        annual_technology_failure_cost=annual_technology_failure_cost,
        annual_recurring_cost=annual_recurring_cost,
        annual_flows=annual_flows,
        cash_flows=cash_flows,
        learning_factors=learning_factors,
        ahorro_neto_promedio=ahorro_neto_promedio,
        current_total_annual_cost=CURRENT_TOTAL_ANNUAL_COST,
        estimated_absolute_annual_cost=estimated_absolute_annual_cost,
        van=van,
        payback=payback,
        savings_profile=savings_profile,
        risk_lines=risk_lines,
        mitigation_lines=mitigation_lines,
    )


def compute_guided_economic_analysis(
    inputs: GuidedEconomicInputs,
) -> GuidedEconomicAnalysisResult:
    """Calcula los tres casos, la media Beta-PERT y la dispersion."""

    cases = tuple(
        compute_guided_economic_case(inputs, savings_profile)
        for savings_profile in GUIDED_SCENARIO_SAVINGS
    )
    optimistic = cases[0].ahorro_neto_promedio
    probable = cases[1].ahorro_neto_promedio
    pessimistic = cases[2].ahorro_neto_promedio
    ahorro_pert = (optimistic + 4.0 * probable + pessimistic) / 6.0
    sigma = abs(optimistic - pessimistic) / 6.0
    return GuidedEconomicAnalysisResult(
        alternative=inputs.alternative,
        route_cost_annual=inputs.route_cost_annual,
        route_cost_reference_annual=inputs.route_cost_reference_annual,
        route_overcost_annual=inputs.route_cost_annual - inputs.route_cost_reference_annual,
        cases=cases,
        ahorro_pert=ahorro_pert,
        sigma=sigma,
    )


def current_cost_reference_summary() -> dict[str, object]:
    """Devuelve los costes actuales del enunciado para la lectura absoluta."""

    return {
        "svq1_annual_cost": CURRENT_SVQ1_ANNUAL_COST,
        "dqa4_annual_cost": CURRENT_DQA4_ANNUAL_COST,
        "transfer_annual_cost": CURRENT_TRANSFER_ANNUAL_COST,
        "total_annual_cost": CURRENT_TOTAL_ANNUAL_COST,
        "breakdown": {
            center: dict(values)
            for center, values in CURRENT_COST_BREAKDOWN.items()
        },
    }


def _build_mitigation_lines(inputs: GuidedEconomicInputs) -> tuple[GuidedMitigationLine, ...]:
    return (
        GuidedMitigationLine(
            name="Implementación por fases",
            capex=2.2e6,
            applied=bool(inputs.include_phasing),
            risk_targets=("Interrupción de servicio",),
        ),
        GuidedMitigationLine(
            name="Sistemas de respaldo",
            capex=1.8e6,
            applied=bool(inputs.include_backup),
            risk_targets=("Fallos de tecnología",),
        ),
        GuidedMitigationLine(
            name="Seguros especiales",
            capex=0.45e6,
            applied=bool(inputs.include_insurance),
            risk_targets=("Problemas legales", "Fallos de tecnología"),
        ),
        GuidedMitigationLine(
            name="Incentivos empleados",
            capex=0.68e6,
            applied=bool(inputs.include_incentives),
            risk_targets=("Problemas empleados",),
        ),
    )


def _build_risk_lines(mitigation_lines: tuple[GuidedMitigationLine, ...]) -> tuple[GuidedRiskLine, ...]:
    mitigation_map = {line.name: line for line in mitigation_lines}
    interruption_factor = 1.0 - (0.75 if mitigation_map["Implementación por fases"].applied else 0.0)
    employee_factor = 1.0 - (0.70 if mitigation_map["Incentivos empleados"].applied else 0.0)
    legal_factor = 1.0 - (0.60 if mitigation_map["Seguros especiales"].applied else 0.0)

    technology_factor = 1.0
    if mitigation_map["Sistemas de respaldo"].applied:
        technology_factor *= 0.15
    if mitigation_map["Seguros especiales"].applied:
        technology_factor *= 0.40

    risks = (
        ("Interrupción de servicio", 0.30, 4.65e6, interruption_factor, ("Implementación por fases",)),
        ("Problemas empleados", 0.45, 2.1e6, employee_factor, ("Incentivos empleados",)),
        ("Sobrecoste construcción", 0.35, 9.25e6, 1.0, ()),
        ("Problemas legales", 0.15, 3.0e6, legal_factor, ("Seguros especiales",)),
    )

    lines: list[GuidedRiskLine] = []
    for name, probability, impact, residual_factor, mitigation_names in risks:
        if name == "Sobrecoste construcción":
            residual_factor = 1.0
        lines.append(
            GuidedRiskLine(
                name=name,
                probability=probability,
                impact=impact,
                expected_cost=probability * impact,
                residual_probability=probability * residual_factor,
                residual_expected_cost=probability * residual_factor * impact,
                mitigation_names=mitigation_names,
            )
        )
    return tuple(lines)


def _annual_technology_failure_cost(inputs: GuidedEconomicInputs) -> float:
    annual_cost = 3.2e6 * 0.30
    if inputs.include_backup:
        annual_cost *= 0.15
    if inputs.include_insurance:
        annual_cost *= 0.40
    return annual_cost


def _annual_cash_flow(
    savings_profile: GuidedSavingsProfile,
    learning_factor: float,
    annual_recurring_cost: float,
) -> float:
    return (
        GUIDED_TRANSFER_ELIMINATED_ANNUAL
        + savings_profile.personal * learning_factor
        + savings_profile.energy * learning_factor
        + savings_profile.one_installation
        - annual_recurring_cost
    )


def _learning_factor(year: int) -> float:
    if year <= 1:
        return 0.50
    if year == 2:
        return 0.75
    return 1.0


def _npv(rate: float, cash_flows: Iterable[float]) -> float:
    return float(sum(cash_flow / (1.0 + rate) ** index for index, cash_flow in enumerate(cash_flows)))


def _validate_guided_inputs(inputs: GuidedEconomicInputs) -> None:
    if inputs.investment_option_name not in GUIDED_CAPEX_BY_OPTION:
        valid = ", ".join(GUIDED_CAPEX_BY_OPTION)
        raise ValueError(f"Opcion de inversion no reconocida: {inputs.investment_option_name}. Opciones: {valid}")
    if inputs.transport_support not in GUIDED_SUPPORT_ANNEX_COSTS:
        valid = ", ".join(GUIDED_SUPPORT_ANNEX_COSTS)
        raise ValueError(f"Apoyo laboral no reconocido: {inputs.transport_support}. Opciones: {valid}")
    if inputs.horizon_years <= 0:
        raise ValueError("El horizonte debe ser positivo")
    if inputs.discount_rate < -0.95:
        raise ValueError("La tasa de descuento es demasiado baja para el calculo guiado")
    for name, value in (
        ("route_cost_annual", inputs.route_cost_annual),
        ("route_cost_reference_annual", inputs.route_cost_reference_annual),
    ):
        if value < 0:
            raise ValueError(f"{name} no puede ser negativo")


def _validate_guided_savings_profile(savings_profile: GuidedSavingsProfile) -> None:
    for name, value in (
        ("personal", savings_profile.personal),
        ("energy", savings_profile.energy),
        ("one_installation", savings_profile.one_installation),
    ):
        if value < 0:
            raise ValueError(f"El ahorro {name} no puede ser negativo")
