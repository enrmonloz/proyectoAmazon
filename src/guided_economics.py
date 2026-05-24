"""Modelo economico guiado para FG/Analisis economico.

El bloque guiado compara Basica, Estandar y Premium con ahorros propios del
enunciado. Las rutas entran solo como diferencial anual frente a DQA4; no se
usa ninguna penalizacion fija de los scripts MATLAB ni costes de rutas externos.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


GUIDED_HORIZON_YEARS = 10
GUIDED_DISCOUNT_RATE = 0.07
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


@dataclass(frozen=True)
class InvestmentEconomicProfile:
    """Perfil economico de una opcion de inversion del enunciado."""

    name: str
    capex_base: float
    annual_saving_base: float


GUIDED_INVESTMENT_PROFILES: tuple[InvestmentEconomicProfile, ...] = (
    InvestmentEconomicProfile("Básica", 18.3e6, 4.7e6),
    InvestmentEconomicProfile("Estándar", 28.5e6, 6.7e6),
    InvestmentEconomicProfile("Premium", 42.7e6, 8.9e6),
)

GUIDED_CAPEX_BY_OPTION: dict[str, float] = {
    profile.name: profile.capex_base for profile in GUIDED_INVESTMENT_PROFILES
}
GUIDED_ANNUAL_SAVINGS_BY_OPTION: dict[str, float] = {
    profile.name: profile.annual_saving_base for profile in GUIDED_INVESTMENT_PROFILES
}

GUIDED_SUPPORT_ANNUAL_COSTS: dict[str, float] = {
    "Sin apoyo": 0.0,
    "Subsidio transporte público": 187_000.0,
    "Transporte corporativo": 441_000.0,
    "Compensación única": 0.0,
}

GUIDED_SUPPORT_INITIAL_COSTS: dict[str, float] = {
    "Sin apoyo": 0.0,
    "Subsidio transporte público": 0.0,
    "Transporte corporativo": 0.0,
    "Compensación única": 450_000.0,
}


@dataclass(frozen=True)
class GuidedEconomicInputs:
    """Parametros compartidos por el analisis economico guiado."""

    alternative: str
    investment_option_name: str = "Estándar"
    transport_support: str = "Subsidio transporte público"
    route_cost_annual: float = 0.0
    route_cost_reference_annual: float = 0.0
    include_training: bool = True
    include_dqa4_value_loss: bool = True
    include_phasing: bool = False
    include_backup: bool = False
    include_insurance: bool = False
    include_incentives: bool = False
    discount_rate: float = GUIDED_DISCOUNT_RATE
    horizon_years: int = GUIDED_HORIZON_YEARS


@dataclass(frozen=True)
class GuidedScenarioDefinition:
    """Definicion de curva y riesgo de un escenario."""

    case_name: str
    saving_multiplier: float
    learning_factors: tuple[float, ...]
    include_construction_risk_year0: bool = False
    include_operational_risk_year1: bool = False


@dataclass(frozen=True)
class GuidedInitialCostLine:
    """Coste inicial de transicion mostrado de forma trazable."""

    name: str
    amount: float
    included: bool


@dataclass(frozen=True)
class GuidedMitigationLine:
    """Mitigacion aplicada y su coste inicial asociado."""

    name: str
    initial_cost: float
    applied: bool
    risk_targets: tuple[str, ...]

    @property
    def capex(self) -> float:
        """Alias historico usado por algunas vistas/tests."""
        return self.initial_cost


@dataclass(frozen=True)
class GuidedRiskLine:
    """Riesgo esperado antes y despues de mitigaciones."""

    name: str
    probability: float
    impact: float
    expected_cost: float
    residual_probability: float
    residual_expected_cost: float
    mitigation_names: tuple[str, ...]
    risk_kind: str


@dataclass(frozen=True)
class GuidedEconomicCaseResult:
    """Resultado de un escenario O/P/P para una opcion de inversion."""

    case_name: str
    alternative: str
    investment_profile: InvestmentEconomicProfile
    transport_support: str
    route_cost_annual: float
    route_cost_reference_annual: float
    route_overcost_annual: float
    capex_base: float
    transition_initial_cost: float
    initial_cost_total: float
    construction_risk_year0: float
    operational_risk_year1: float
    annual_support_cost: float
    annual_recurring_cost: float
    annual_flows: tuple[float, ...]
    cash_flows: tuple[float, ...]
    learning_factors: tuple[float, ...]
    average_operating_saving: float
    current_total_annual_cost: float
    estimated_absolute_annual_cost: float
    van: float
    tir: float | None
    payback: float | None
    risk_lines: tuple[GuidedRiskLine, ...]
    mitigation_lines: tuple[GuidedMitigationLine, ...]
    initial_cost_lines: tuple[GuidedInitialCostLine, ...]

    @property
    def investment_option_name(self) -> str:
        return self.investment_profile.name

    @property
    def capex_transition(self) -> float:
        return self.transition_initial_cost

    @property
    def capex_total(self) -> float:
        return self.initial_cost_total

    @property
    def ahorro_neto_promedio(self) -> float:
        return self.average_operating_saving


@dataclass(frozen=True)
class InvestmentCriterionResult:
    """Resultado de un criterio simple de la matriz de decision."""

    criterion: str
    winner: str
    values: dict[str, float | None]
    higher_is_better: bool


@dataclass(frozen=True)
class GuidedEconomicAnalysisResult:
    """Resultado completo de una opcion de inversion para una alternativa."""

    alternative: str
    investment_profile: InvestmentEconomicProfile
    route_cost_annual: float
    route_cost_reference_annual: float
    route_overcost_annual: float
    annual_recurring_cost: float
    initial_cost_total: float
    cases: tuple[GuidedEconomicCaseResult, ...]
    cash_flows_pert: tuple[float, ...]
    annual_flows_pert: tuple[float, ...]
    average_operating_saving_pert: float
    estimated_absolute_annual_cost_pert: float
    van_pert: float
    tir_pert: float | None
    payback_pert: float | None
    van_pessimistic: float
    sigma: float
    risk_lines: tuple[GuidedRiskLine, ...]
    mitigation_lines: tuple[GuidedMitigationLine, ...]
    initial_cost_lines: tuple[GuidedInitialCostLine, ...]

    @property
    def optimistic_case(self) -> GuidedEconomicCaseResult:
        return self.cases[0]

    @property
    def probable_case(self) -> GuidedEconomicCaseResult:
        return self.cases[1]

    @property
    def pessimistic_case(self) -> GuidedEconomicCaseResult:
        return self.cases[2]

    @property
    def investment_option_name(self) -> str:
        return self.investment_profile.name

    @property
    def ahorro_pert(self) -> float:
        return self.average_operating_saving_pert


@dataclass(frozen=True)
class InvestmentComparisonResult:
    """Comparacion Basica/Estandar/Premium para una alternativa logistica."""

    alternative: str
    route_cost_annual: float
    route_cost_reference_annual: float
    route_overcost_annual: float
    analyses: tuple[GuidedEconomicAnalysisResult, ...]
    decision_matrix: tuple[InvestmentCriterionResult, ...]
    scores: dict[str, int]
    best_option_name: str

    @property
    def best_analysis(self) -> GuidedEconomicAnalysisResult:
        return next(
            analysis
            for analysis in self.analyses
            if analysis.investment_option_name == self.best_option_name
        )


def compute_guided_economic_case(
    inputs: GuidedEconomicInputs,
    scenario: GuidedScenarioDefinition,
    investment_profile: InvestmentEconomicProfile | None = None,
) -> GuidedEconomicCaseResult:
    """Calcula un escenario guiado para una opcion de inversion."""

    _validate_guided_inputs(inputs)
    profile = investment_profile or _profile_by_name(inputs.investment_option_name)
    _validate_investment_profile(profile)
    if len(scenario.learning_factors) != inputs.horizon_years:
        raise ValueError("La curva del escenario debe coincidir con el horizonte")

    route_overcost_annual = inputs.route_cost_annual - inputs.route_cost_reference_annual
    annual_support_cost = GUIDED_SUPPORT_ANNUAL_COSTS[inputs.transport_support]
    annual_recurring_cost = annual_support_cost + route_overcost_annual
    mitigation_lines = _build_mitigation_lines(inputs)
    initial_cost_lines = _build_initial_cost_lines(inputs, mitigation_lines)
    transition_initial_cost = sum(line.amount for line in initial_cost_lines if line.included)
    initial_cost_total = profile.capex_base + transition_initial_cost
    risk_lines = _build_risk_lines(profile, mitigation_lines)

    construction_risk_year0 = (
        _construction_residual_risk(risk_lines)
        if scenario.include_construction_risk_year0
        else 0.0
    )
    operational_risk_year1 = (
        _operational_residual_risk(risk_lines)
        if scenario.include_operational_risk_year1
        else 0.0
    )

    annual_gross_saving = profile.annual_saving_base * scenario.saving_multiplier
    annual_flows_list: list[float] = []
    for index, learning_factor in enumerate(scenario.learning_factors):
        flow = annual_gross_saving * learning_factor - annual_recurring_cost
        if index == 0:
            flow -= operational_risk_year1
        annual_flows_list.append(flow)

    annual_flows = tuple(annual_flows_list)
    cash_flows = (-(initial_cost_total + construction_risk_year0), *annual_flows)
    average_operating_saving = _average(annual_flows)

    return GuidedEconomicCaseResult(
        case_name=scenario.case_name,
        alternative=inputs.alternative,
        investment_profile=profile,
        transport_support=inputs.transport_support,
        route_cost_annual=inputs.route_cost_annual,
        route_cost_reference_annual=inputs.route_cost_reference_annual,
        route_overcost_annual=route_overcost_annual,
        capex_base=profile.capex_base,
        transition_initial_cost=transition_initial_cost,
        initial_cost_total=initial_cost_total,
        construction_risk_year0=construction_risk_year0,
        operational_risk_year1=operational_risk_year1,
        annual_support_cost=annual_support_cost,
        annual_recurring_cost=annual_recurring_cost,
        annual_flows=annual_flows,
        cash_flows=cash_flows,
        learning_factors=scenario.learning_factors,
        average_operating_saving=average_operating_saving,
        current_total_annual_cost=CURRENT_TOTAL_ANNUAL_COST,
        estimated_absolute_annual_cost=CURRENT_TOTAL_ANNUAL_COST - average_operating_saving,
        van=_npv(inputs.discount_rate, cash_flows),
        tir=_irr(cash_flows),
        payback=_payback(cash_flows),
        risk_lines=risk_lines,
        mitigation_lines=mitigation_lines,
        initial_cost_lines=initial_cost_lines,
    )


def compute_guided_economic_analysis(
    inputs: GuidedEconomicInputs,
    investment_profile: InvestmentEconomicProfile | None = None,
) -> GuidedEconomicAnalysisResult:
    """Calcula O/P/P, PERT y metricas para una opcion de inversion."""

    _validate_guided_inputs(inputs)
    profile = investment_profile or _profile_by_name(inputs.investment_option_name)
    scenarios = _scenario_definitions(inputs.horizon_years)
    cases = tuple(
        compute_guided_economic_case(inputs, scenario, profile)
        for scenario in scenarios
    )
    cash_flows_pert = tuple(
        (cases[0].cash_flows[index] + 4.0 * cases[1].cash_flows[index] + cases[2].cash_flows[index]) / 6.0
        for index in range(len(cases[0].cash_flows))
    )
    annual_flows_pert = cash_flows_pert[1:]
    average_operating_saving_pert = _average(annual_flows_pert)
    sigma = abs(cases[0].average_operating_saving - cases[2].average_operating_saving) / 6.0

    return GuidedEconomicAnalysisResult(
        alternative=inputs.alternative,
        investment_profile=profile,
        route_cost_annual=inputs.route_cost_annual,
        route_cost_reference_annual=inputs.route_cost_reference_annual,
        route_overcost_annual=inputs.route_cost_annual - inputs.route_cost_reference_annual,
        annual_recurring_cost=cases[1].annual_recurring_cost,
        initial_cost_total=cases[1].initial_cost_total,
        cases=cases,
        cash_flows_pert=cash_flows_pert,
        annual_flows_pert=annual_flows_pert,
        average_operating_saving_pert=average_operating_saving_pert,
        estimated_absolute_annual_cost_pert=CURRENT_TOTAL_ANNUAL_COST - average_operating_saving_pert,
        van_pert=_npv(inputs.discount_rate, cash_flows_pert),
        tir_pert=_irr(cash_flows_pert),
        payback_pert=_payback(cash_flows_pert),
        van_pessimistic=cases[2].van,
        sigma=sigma,
        risk_lines=cases[1].risk_lines,
        mitigation_lines=cases[1].mitigation_lines,
        initial_cost_lines=cases[1].initial_cost_lines,
    )


def compute_investment_comparison(inputs: GuidedEconomicInputs) -> InvestmentComparisonResult:
    """Compara Basica/Estandar/Premium para una alternativa logistica."""

    _validate_guided_inputs(inputs)
    analyses = tuple(
        compute_guided_economic_analysis(
            GuidedEconomicInputs(
                alternative=inputs.alternative,
                investment_option_name=profile.name,
                transport_support=inputs.transport_support,
                route_cost_annual=inputs.route_cost_annual,
                route_cost_reference_annual=inputs.route_cost_reference_annual,
                include_training=inputs.include_training,
                include_dqa4_value_loss=inputs.include_dqa4_value_loss,
                include_phasing=inputs.include_phasing,
                include_backup=inputs.include_backup,
                include_insurance=inputs.include_insurance,
                include_incentives=inputs.include_incentives,
                discount_rate=inputs.discount_rate,
                horizon_years=inputs.horizon_years,
            ),
            profile,
        )
        for profile in GUIDED_INVESTMENT_PROFILES
    )
    decision_matrix = _decision_matrix(analyses)
    scores = {analysis.investment_option_name: 0 for analysis in analyses}
    for criterion in decision_matrix:
        scores[criterion.winner] += 1
    best_option_name = max(
        scores,
        key=lambda name: (
            scores[name],
            _analysis_by_name(analyses, name).van_pert,
            -_analysis_by_name(analyses, name).initial_cost_total,
        ),
    )
    return InvestmentComparisonResult(
        alternative=inputs.alternative,
        route_cost_annual=inputs.route_cost_annual,
        route_cost_reference_annual=inputs.route_cost_reference_annual,
        route_overcost_annual=inputs.route_cost_annual - inputs.route_cost_reference_annual,
        analyses=analyses,
        decision_matrix=decision_matrix,
        scores=scores,
        best_option_name=best_option_name,
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


def _scenario_definitions(horizon_years: int) -> tuple[GuidedScenarioDefinition, ...]:
    return (
        GuidedScenarioDefinition(
            case_name="Optimista",
            saving_multiplier=1.20,
            learning_factors=tuple(1.0 for _ in range(horizon_years)),
        ),
        GuidedScenarioDefinition(
            case_name="Probable",
            saving_multiplier=1.00,
            learning_factors=tuple(0.75 if year == 1 else 1.0 for year in range(1, horizon_years + 1)),
        ),
        GuidedScenarioDefinition(
            case_name="Pesimista",
            saving_multiplier=0.80,
            learning_factors=tuple(
                0.50 if year == 1 else 0.75 if year == 2 else 1.0
                for year in range(1, horizon_years + 1)
            ),
            include_construction_risk_year0=True,
            include_operational_risk_year1=True,
        ),
    )


def _build_initial_cost_lines(
    inputs: GuidedEconomicInputs,
    mitigation_lines: tuple[GuidedMitigationLine, ...],
) -> tuple[GuidedInitialCostLine, ...]:
    lines = [
        GuidedInitialCostLine("Formación empleados", 1.56e6, bool(inputs.include_training)),
        GuidedInitialCostLine("Pérdida valor DQA4", 0.523e6, bool(inputs.include_dqa4_value_loss)),
        GuidedInitialCostLine(
            "Compensación única empleados",
            GUIDED_SUPPORT_INITIAL_COSTS[inputs.transport_support],
            inputs.transport_support == "Compensación única",
        ),
    ]
    lines.extend(
        GuidedInitialCostLine(line.name, line.initial_cost, line.applied)
        for line in mitigation_lines
    )
    return tuple(lines)


def _build_mitigation_lines(inputs: GuidedEconomicInputs) -> tuple[GuidedMitigationLine, ...]:
    return (
        GuidedMitigationLine(
            name="Implementación por fases",
            initial_cost=2.2e6,
            applied=bool(inputs.include_phasing),
            risk_targets=("Interrupción de servicio",),
        ),
        GuidedMitigationLine(
            name="Sistemas de respaldo",
            initial_cost=1.8e6,
            applied=bool(inputs.include_backup),
            risk_targets=("Fallos de tecnología",),
        ),
        GuidedMitigationLine(
            name="Seguros especiales",
            initial_cost=0.45e6,
            applied=bool(inputs.include_insurance),
            risk_targets=("Problemas legales",),
        ),
        GuidedMitigationLine(
            name="Incentivos empleados",
            initial_cost=0.68e6,
            applied=bool(inputs.include_incentives),
            risk_targets=("Problemas empleados",),
        ),
    )


def _build_risk_lines(
    profile: InvestmentEconomicProfile,
    mitigation_lines: tuple[GuidedMitigationLine, ...],
) -> tuple[GuidedRiskLine, ...]:
    mitigation_map = {line.name: line for line in mitigation_lines}
    interruption_factor = 1.0 - (0.75 if mitigation_map["Implementación por fases"].applied else 0.0)
    employee_factor = 1.0 - (0.70 if mitigation_map["Incentivos empleados"].applied else 0.0)
    technology_factor = 1.0 - (0.85 if mitigation_map["Sistemas de respaldo"].applied else 0.0)
    legal_factor = 1.0 - (0.60 if mitigation_map["Seguros especiales"].applied else 0.0)

    risks = (
        (
            "Interrupción de servicio",
            0.30,
            8.5e6,
            interruption_factor,
            ("Implementación por fases",),
            "operational",
        ),
        (
            "Problemas empleados",
            0.45,
            2.1e6,
            employee_factor,
            ("Incentivos empleados",),
            "operational",
        ),
        (
            "Sobrecoste construcción",
            0.35,
            profile.capex_base * 0.30,
            1.0,
            (),
            "construction",
        ),
        (
            "Fallos de tecnología",
            0.30,
            3.2e6,
            technology_factor,
            ("Sistemas de respaldo",),
            "operational",
        ),
        (
            "Problemas legales",
            0.15,
            3.0e6,
            legal_factor,
            ("Seguros especiales",),
            "operational",
        ),
    )

    lines: list[GuidedRiskLine] = []
    for name, probability, impact, residual_factor, mitigation_names, risk_kind in risks:
        lines.append(
            GuidedRiskLine(
                name=name,
                probability=probability,
                impact=impact,
                expected_cost=probability * impact,
                residual_probability=probability * residual_factor,
                residual_expected_cost=probability * residual_factor * impact,
                mitigation_names=mitigation_names,
                risk_kind=risk_kind,
            )
        )
    return tuple(lines)


def _construction_residual_risk(risk_lines: Iterable[GuidedRiskLine]) -> float:
    return sum(line.residual_expected_cost for line in risk_lines if line.risk_kind == "construction")


def _operational_residual_risk(risk_lines: Iterable[GuidedRiskLine]) -> float:
    return sum(line.residual_expected_cost for line in risk_lines if line.risk_kind == "operational")


def _decision_matrix(
    analyses: tuple[GuidedEconomicAnalysisResult, ...],
) -> tuple[InvestmentCriterionResult, ...]:
    criteria = (
        ("VAN PERT", True, lambda analysis: analysis.van_pert),
        ("Payback PERT", False, lambda analysis: analysis.payback_pert),
        ("VAN pesimista", True, lambda analysis: analysis.van_pessimistic),
        ("Coste inicial total", False, lambda analysis: analysis.initial_cost_total),
    )
    rows: list[InvestmentCriterionResult] = []
    for criterion, higher_is_better, getter in criteria:
        values = {analysis.investment_option_name: getter(analysis) for analysis in analyses}
        winner = _winner(values, higher_is_better)
        rows.append(
            InvestmentCriterionResult(
                criterion=criterion,
                winner=winner,
                values=values,
                higher_is_better=higher_is_better,
            )
        )
    return tuple(rows)


def _winner(values: dict[str, float | None], higher_is_better: bool) -> str:
    valid = {
        name: value
        for name, value in values.items()
        if value is not None
    }
    if not valid:
        return next(iter(values))
    if higher_is_better:
        return max(valid, key=lambda name: valid[name])
    return min(valid, key=lambda name: valid[name])


def _analysis_by_name(
    analyses: tuple[GuidedEconomicAnalysisResult, ...],
    option_name: str,
) -> GuidedEconomicAnalysisResult:
    return next(analysis for analysis in analyses if analysis.investment_option_name == option_name)


def _profile_by_name(name: str) -> InvestmentEconomicProfile:
    for profile in GUIDED_INVESTMENT_PROFILES:
        if profile.name == name:
            return profile
    valid = ", ".join(profile.name for profile in GUIDED_INVESTMENT_PROFILES)
    raise ValueError(f"Opcion de inversion no reconocida: {name}. Opciones: {valid}")


def _validate_guided_inputs(inputs: GuidedEconomicInputs) -> None:
    _profile_by_name(inputs.investment_option_name)
    if inputs.transport_support not in GUIDED_SUPPORT_ANNUAL_COSTS:
        valid = ", ".join(GUIDED_SUPPORT_ANNUAL_COSTS)
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


def _validate_investment_profile(profile: InvestmentEconomicProfile) -> None:
    if profile.capex_base < 0:
        raise ValueError("El CAPEX base no puede ser negativo")
    if profile.annual_saving_base < 0:
        raise ValueError("El ahorro anual base no puede ser negativo")


def _npv(rate: float, cash_flows: Iterable[float]) -> float:
    return float(sum(cash_flow / (1.0 + rate) ** index for index, cash_flow in enumerate(cash_flows)))


def _irr(cash_flows: Iterable[float]) -> float | None:
    """Calcula TIR por biseccion; devuelve None si no hay solucion estable."""

    flows = tuple(float(value) for value in cash_flows)
    if not flows or not any(value > 0 for value in flows) or not any(value < 0 for value in flows):
        return None

    def value(rate: float) -> float:
        try:
            return _npv(rate, flows)
        except OverflowError:
            return float("nan")

    low = -0.95
    high = 2.0
    f_low = value(low)
    f_high = value(high)
    attempts = 0
    while f_low * f_high > 0 and attempts < 8:
        high *= 2.0
        f_high = value(high)
        attempts += 1
    if f_low != f_low or f_high != f_high or f_low * f_high > 0:
        return None

    for _ in range(120):
        mid = (low + high) / 2.0
        f_mid = value(mid)
        if f_mid != f_mid:
            return None
        if abs(f_mid) < 1e-7:
            return mid
        if f_low * f_mid <= 0:
            high = mid
            f_high = f_mid
        else:
            low = mid
            f_low = f_mid
    result = (low + high) / 2.0
    return result if -0.95 < result < high + 1.0 else None


def _payback(cash_flows: Iterable[float]) -> float | None:
    """Payback simple acumulado sobre flujos nominales."""

    flows = tuple(float(value) for value in cash_flows)
    if not flows:
        return None
    accumulated = flows[0]
    if accumulated >= 0:
        return 0.0
    for index, flow in enumerate(flows[1:], start=1):
        previous = accumulated
        accumulated += flow
        if accumulated >= 0 and flow > 0:
            return (index - 1) + abs(previous) / flow
    return None


def _average(values: Iterable[float]) -> float:
    values = tuple(values)
    return sum(values) / len(values) if values else 0.0
