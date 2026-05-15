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


def transfer_unit_cost(params: CurrentCostParams) -> float:
    denom = params.transfer_daily_packages * params.days_per_year
    return params.transfer_annual_cost / denom if denom else 0.0


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
