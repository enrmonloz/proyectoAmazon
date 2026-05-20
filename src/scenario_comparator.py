"""Comparador ligero de escenarios integrados.

Este modulo coordina ScenarioConfig, run_pipeline y build_scenario_result para
comparar alternativas completas sin reimplementar rutas, economia, riesgos ni
cronograma.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Callable, Iterable

import pandas as pd

from .data_loader import DEPOT_NAME, SECONDARY_HUB_NAME, Dataset, dataset_with_depot
from .economics_model import (
    OPERATIONAL_OPTION_CURRENT,
    OPERATIONAL_OPTION_INTERMEDIATE,
    OPERATIONAL_OPTION_SVQ1_EXPANDED,
)
from .pipeline import PipelineConfig, PipelineResult, run_pipeline
from .scenario_model import (
    NO_ROUTES_WARNING,
    ScenarioConfig,
    ScenarioResult,
    build_scenario_result,
    scenario_results_frame,
)


INTERMEDIATE_NO_OD_WARNING = (
    "Nuevo centro/intermedio no tiene un nodo OD real seleccionado; no se calculan "
    "rutas para evitar inventar tiempos."
)


@dataclass(frozen=True)
class ScenarioComparisonConfig:
    """Configuracion de una comparacion de escenarios."""

    scenarios: tuple[ScenarioConfig, ...]
    run_routes: bool = True
    include_intermediate: bool = True
    active_scenario_name: str | None = None
    notes: tuple[str, ...] = ()


@dataclass(frozen=True)
class ScenarioComparisonResult:
    """Resultado agregado de una comparacion de escenarios."""

    results: tuple[ScenarioResult, ...]
    comparison_frame: pd.DataFrame
    warnings: tuple[str, ...]
    interpretation: str


PipelineRunner = Callable[[Dataset, PipelineConfig], PipelineResult]


def build_default_scenario_configs(
    include_intermediate: bool = True,
) -> tuple[ScenarioConfig, ...]:
    """Devuelve escenarios base comparables y editables en futuras iteraciones."""

    scenarios: list[ScenarioConfig] = [
        ScenarioConfig(
            name="Estructura actual",
            center_option=OPERATIONAL_OPTION_CURRENT,
            investment_option_name="Básica",
            transport_support="Sin apoyo",
            include_phasing=False,
            include_backup=False,
            include_training=False,
            include_incentives=False,
            include_insurance=False,
            start_month=1,
            notes=(
                "DQA4 se mantiene como centro de ultima milla para el flujo analizado.",
            ),
        ),
        ScenarioConfig(
            name="SVQ1 ampliado estándar",
            center_option=OPERATIONAL_OPTION_SVQ1_EXPANDED,
            investment_option_name="Estándar",
            transport_support="Subsidio transporte público",
            include_phasing=True,
            include_backup=True,
            include_training=True,
            include_incentives=True,
            include_insurance=True,
            start_month=1,
            notes=(
                "SVQ1 absorbe la ultima milla del flujo SVQ1-DQA4 analizado.",
            ),
        ),
    ]

    if include_intermediate:
        scenarios.append(
            ScenarioConfig(
                name="Nuevo centro/intermedio",
                center_option=OPERATIONAL_OPTION_INTERMEDIATE,
                investment_option_name="Premium",
                transport_support="Transporte corporativo",
                include_phasing=True,
                include_backup=True,
                include_training=True,
                include_incentives=True,
                include_insurance=True,
                start_month=1,
                notes=(
                    "Solo es comparable con rutas si existe un nodo OD o una aproximacion "
                    "explicita a municipio existente.",
                ),
            )
        )

    return tuple(scenarios)


def resolve_scenario_depot(
    dataset: Dataset,
    scenario: ScenarioConfig,
    intermediate_candidate=None,
) -> tuple[Dataset | None, tuple[str, ...]]:
    """Resuelve el dataset/depot compatible con un escenario."""

    if scenario.center_option == OPERATIONAL_OPTION_CURRENT:
        return (
            dataset_with_depot(dataset, SECONDARY_HUB_NAME),
            (),
        )

    if scenario.center_option == OPERATIONAL_OPTION_SVQ1_EXPANDED:
        return (
            dataset_with_depot(dataset, DEPOT_NAME),
            (),
        )

    if scenario.center_option == OPERATIONAL_OPTION_INTERMEDIATE:
        depot_name = _candidate_depot_name(dataset, intermediate_candidate)
        if depot_name is None:
            return None, (INTERMEDIATE_NO_OD_WARNING,)
        return (
            dataset_with_depot(dataset, depot_name),
            (
                "Nuevo centro/intermedio usa una aproximacion advertida a nodo OD "
                f"existente: {depot_name}.",
            ),
        )

    raise ValueError(f"Alternativa operativa no reconocida: {scenario.center_option}")


def build_scenario_comparison(
    dataset: Dataset,
    pipeline_config: PipelineConfig,
    comparison_config: ScenarioComparisonConfig | None = None,
    *,
    intermediate_candidate=None,
    route_params: dict | None = None,
    pipeline_runner: PipelineRunner = run_pipeline,
) -> ScenarioComparisonResult:
    """Construye una comparacion usando rutas y ScenarioResult existentes."""

    config = comparison_config or ScenarioComparisonConfig(
        scenarios=build_default_scenario_configs()
    )
    results: list[ScenarioResult] = []
    warnings: list[str] = list(config.notes)

    scenarios = tuple(
        scenario
        for scenario in config.scenarios
        if config.include_intermediate
        or scenario.center_option != OPERATIONAL_OPTION_INTERMEDIATE
    )

    for scenario in scenarios:
        pipeline_result = None
        scenario_warnings: list[str] = []
        dataset_for_run, depot_notes = resolve_scenario_depot(
            dataset,
            scenario,
            intermediate_candidate=intermediate_candidate,
        )
        scenario_warnings.extend(depot_notes)

        if config.run_routes and dataset_for_run is not None:
            try:
                pipeline_result = pipeline_runner(dataset_for_run, pipeline_config)
            except Exception as exc:
                scenario_warnings.append(
                    f"No se pudieron calcular rutas para {scenario.name}: {exc}"
                )
        elif not config.run_routes:
            scenario_warnings.append(
                f"{scenario.name}: comparacion configurada sin recalcular rutas."
            )

        result = build_scenario_result(
            scenario,
            pipeline_result=pipeline_result,
            route_params=route_params,
        )
        result = replace(
            result,
            warnings=_dedupe((*result.warnings, *scenario_warnings)),
        )
        results.append(result)
        warnings.extend(f"{scenario.name}: {warning}" for warning in scenario_warnings)

    result_tuple = tuple(results)
    frame = scenario_comparison_frame(result_tuple)
    return ScenarioComparisonResult(
        results=result_tuple,
        comparison_frame=frame,
        warnings=_dedupe(warnings),
        interpretation=_build_comparison_interpretation(result_tuple),
    )


def scenario_comparison_frame(results: Iterable[ScenarioResult]) -> pd.DataFrame:
    """Construye la tabla comparativa ampliada para presentacion."""

    result_tuple = tuple(results)
    base_rows = scenario_results_frame(result_tuple).to_dict("records")
    rows: list[dict[str, object]] = []

    for base_row, result in zip(base_rows, result_tuple):
        summary = (
            result.operational_economic_result.bridge.operational_summary
            if result.operational_economic_result is not None
            else None
        )
        vehicle_count = (
            summary.diesel_count + summary.electric_count
            if summary is not None
            else None
        )
        rows.append(
            {
                "Escenario": base_row["Escenario"],
                "Alternativa operativa": result.config.center_option,
                "Centro de reparto": summary.depot_name if summary is not None else None,
                "Inversión": base_row["Inversión"],
                "Rutas totales": summary.total_routes if summary is not None else None,
                "Distancia total": (
                    summary.total_distance_km if summary is not None else None
                ),
                "Tiempo total": summary.total_time_min if summary is not None else None,
                "Vehículos VRP": vehicle_count,
                "CAPEX total": base_row["CAPEX total"],
                "Ahorro neto anual": base_row["Ahorro neto anual"],
                "Ahorro operativo ajustado": base_row["Ahorro operativo ajustado"],
                "Coste medio de riesgos": base_row["Coste riesgo"],
                "Aceptabilidad laboral": base_row["Aceptabilidad laboral"],
                "Alertas altas de cronograma": base_row["Alertas altas cronograma"],
                "Payback": result.economic_result.payback_net,
                "VAN": result.economic_result.van,
                "Viabilidad preliminar": preliminary_viability(result),
                "Warnings": _warnings_text(result.warnings),
            }
        )

    return pd.DataFrame(rows)


def preliminary_viability(result: ScenarioResult) -> str:
    """Clasificacion simple y explicable, sin pesos ni score oculto."""

    has_no_routes = NO_ROUTES_WARNING in result.warnings
    labor_acceptability = result.labor_result.summary.acceptability
    high_timeline = result.timeline_result.high_severity_warning_count
    has_warnings = bool(result.warnings)

    if (
        has_no_routes
        or result.net_savings_annual <= 0
        or labor_acceptability == "Baja"
        or high_timeline > 2
    ):
        return "Débil"

    if (
        has_warnings
        or result.total_expected_risk_cost > result.net_savings_annual
        or labor_acceptability == "Media"
        or high_timeline > 0
    ):
        return "Condicionada"

    return "Favorable"


def _candidate_depot_name(dataset: Dataset, intermediate_candidate) -> str | None:
    if intermediate_candidate is None:
        return None

    if isinstance(intermediate_candidate, str):
        return _valid_depot_name(dataset, intermediate_candidate)

    if isinstance(intermediate_candidate, int):
        idx = int(intermediate_candidate)
        if 0 <= idx < dataset.n_nodes:
            return dataset.names[idx]
        return None

    node_index = getattr(intermediate_candidate, "node_index", None)
    if node_index is None and hasattr(intermediate_candidate, "candidate"):
        node_index = getattr(intermediate_candidate.candidate, "node_index", None)
    if node_index is not None:
        return _candidate_depot_name(dataset, int(node_index))

    nearest = getattr(intermediate_candidate, "nearest_municipality", None)
    if nearest is not None:
        return _valid_depot_name(dataset, str(nearest))

    return None


def _valid_depot_name(dataset: Dataset, name: str) -> str | None:
    normalized = name.strip().casefold()
    for candidate in dataset.names:
        if str(candidate).strip().casefold() == normalized:
            return candidate
    return None


def _warnings_text(warnings: tuple[str, ...]) -> str:
    return " | ".join(warnings) if warnings else "-"


def _dedupe(items: Iterable[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            out.append(item)
    return tuple(out)


def _build_comparison_interpretation(results: tuple[ScenarioResult, ...]) -> str:
    if not results:
        return "No hay escenarios calculados."

    favorable = [
        result.config.name
        for result in results
        if preliminary_viability(result) == "Favorable"
    ]
    conditioned = [
        result.config.name
        for result in results
        if preliminary_viability(result) == "Condicionada"
    ]
    weak = [
        result.config.name
        for result in results
        if preliminary_viability(result) == "Débil"
    ]

    parts = [
        "La comparacion integra rutas, economia, riesgos, medidas laborales y "
        "cronograma con reglas transparentes.",
    ]
    if favorable:
        parts.append("Lectura favorable: " + ", ".join(favorable) + ".")
    if conditioned:
        parts.append("Lectura condicionada: " + ", ".join(conditioned) + ".")
    if weak:
        parts.append("Lectura debil o incompleta: " + ", ".join(weak) + ".")
    parts.append("No es una recomendacion final automatica.")
    return " ".join(parts)
