"""Comparador ligero de escenarios integrados.

Este modulo coordina ScenarioConfig, run_pipeline y build_scenario_result para
comparar alternativas completas sin reimplementar rutas, economia, riesgos ni
cronograma.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from itertools import product
from typing import Callable, Iterable

import pandas as pd

from .data_loader import (
    DEPOT_NAME,
    SECONDARY_HUB_NAME,
    VIRTUAL_DEPOT_NAME_PREFIX,
    Dataset,
    dataset_with_depot,
    dataset_with_virtual_depot,
)
from .economics_model import (
    OPERATIONAL_OPTION_CURRENT,
    OPERATIONAL_OPTION_INTERMEDIATE,
    OPERATIONAL_OPTION_SVQ1_EXPANDED,
)
from .pipeline import PipelineConfig, PipelineResult, run_pipeline
from .location_solver import AutoLocationSelection, select_auto_new_location
from .scenario_model import (
    NO_ROUTES_WARNING,
    ScenarioConfig,
    ScenarioResult,
    build_scenario_result,
    scenario_results_frame,
)


AUTO_NEW_LOCATION_NOTE = (
    "Nuevo centro/intermedio elegido automaticamente por menor distancia media "
    "ponderada."
)
AUTO_NEW_LOCATION_VIRTUAL_WARNING = (
    "Nuevo centro/intermedio usa depot virtual con distancias rectas y tiempos "
    "estimados mediante el ratio interno min/km de la matriz OD."
)
LEGACY_INTERMEDIATE_BRIDGE_WARNING_PREFIX = (
    "El centro intermedio solo debe usarse como depot"
)
TRANSITION_DIRECT = "Directa"
TRANSITION_PHASED = "Por fases"
DEFAULT_MAX_TREE_SCENARIOS = 12

SCENARIO_PRESET_STRATEGIC = "Comparación estratégica principal"
SCENARIO_PRESET_SVQ1_INVESTMENT = "Sensibilidad de inversión en SVQ1"
SCENARIO_PRESET_TRANSITION_RISK = "Riesgo de transición"

# Alias de compatibilidad: build_default_scenario_configs sigue apuntando al
# preset principal, y cualquier import antiguo mantiene significado razonable.
SCENARIO_PRESET_BASIC = SCENARIO_PRESET_STRATEGIC
SCENARIO_PRESET_SVQ1 = SCENARIO_PRESET_SVQ1_INVESTMENT
SCENARIO_PRESET_LABOR = SCENARIO_PRESET_TRANSITION_RISK
SCENARIO_PRESET_TIMELINE = SCENARIO_PRESET_TRANSITION_RISK
SCENARIO_PRESET_COMPLETE = SCENARIO_PRESET_STRATEGIC

SCENARIO_PRESETS: tuple[str, ...] = (
    SCENARIO_PRESET_STRATEGIC,
    SCENARIO_PRESET_SVQ1_INVESTMENT,
    SCENARIO_PRESET_TRANSITION_RISK,
)

TREE_START_MONTHS: dict[str, int] = {
    "Enero": 1,
    "Abril": 4,
    "Julio": 7,
    "Octubre": 10,
}


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


@dataclass(frozen=True)
class ScenarioTreeConfig:
    """Ejes seleccionados para generar escenarios por combinatoria simple."""

    centers: tuple[str, ...]
    investment_options: tuple[str, ...]
    transport_supports: tuple[str, ...]
    transition_modes: tuple[str, ...]
    backup_options: tuple[bool, ...]
    start_months: tuple[int, ...]
    max_scenarios: int = DEFAULT_MAX_TREE_SCENARIOS


@dataclass(frozen=True)
class ScenarioTreeResult:
    """Escenarios generados desde un arbol de decisiones."""

    scenarios: tuple[ScenarioConfig, ...]
    total_combinations: int
    warnings: tuple[str, ...]
    limit_exceeded: bool


PipelineRunner = Callable[[Dataset, PipelineConfig], PipelineResult]


def build_default_scenario_configs(
    include_intermediate: bool = True,
) -> tuple[ScenarioConfig, ...]:
    """Devuelve el preset de comparacion basica para compatibilidad."""

    scenarios = list(build_preset_scenario_configs(SCENARIO_PRESET_BASIC))
    if not include_intermediate:
        scenarios = [
            scenario
            for scenario in scenarios
            if scenario.center_option != OPERATIONAL_OPTION_INTERMEDIATE
        ]
    return tuple(scenarios)


def build_preset_scenario_configs(preset_name: str) -> tuple[ScenarioConfig, ...]:
    """Devuelve escenarios predefinidos como punto de partida rapido."""

    if preset_name == "Comparación básica":
        preset_name = SCENARIO_PRESET_STRATEGIC
    elif preset_name == "Comparación SVQ1":
        preset_name = SCENARIO_PRESET_SVQ1_INVESTMENT
    elif preset_name in {"Comparación laboral", "Comparación cronograma"}:
        preset_name = SCENARIO_PRESET_TRANSITION_RISK
    elif preset_name == "Comparación completa":
        preset_name = SCENARIO_PRESET_STRATEGIC

    if preset_name == SCENARIO_PRESET_STRATEGIC:
        return (
            _scenario(
                name="Escenario A: Estructura actual",
                center_option=OPERATIONAL_OPTION_CURRENT,
                investment_option_name="Básica",
                transport_support="Sin apoyo",
                include_phasing=False,
                include_backup=False,
                include_training=False,
                include_incentives=False,
                include_insurance=False,
                start_month=1,
            ),
            _scenario(
                name="Escenario B: SVQ1 ampliado estándar",
                center_option=OPERATIONAL_OPTION_SVQ1_EXPANDED,
                investment_option_name="Estándar",
                transport_support="Subsidio transporte público",
                include_phasing=True,
                include_backup=True,
                start_month=1,
            ),
            _scenario(
                name="Escenario C: Nuevo centro/intermedio",
                center_option=OPERATIONAL_OPTION_INTERMEDIATE,
                investment_option_name="Premium",
                transport_support="Transporte corporativo",
                include_phasing=True,
                include_backup=True,
                start_month=1,
            ),
        )

    if preset_name == SCENARIO_PRESET_SVQ1_INVESTMENT:
        return (
            _scenario(
                name="Escenario A: SVQ1 ampliado básico",
                center_option=OPERATIONAL_OPTION_SVQ1_EXPANDED,
                investment_option_name="Básica",
                transport_support="Subsidio transporte público",
                include_phasing=True,
                include_backup=False,
                start_month=1,
            ),
            _scenario(
                name="Escenario B: SVQ1 ampliado estándar",
                center_option=OPERATIONAL_OPTION_SVQ1_EXPANDED,
                investment_option_name="Estándar",
                transport_support="Subsidio transporte público",
                include_phasing=True,
                include_backup=True,
                start_month=1,
            ),
            _scenario(
                name="Escenario C: SVQ1 ampliado premium",
                center_option=OPERATIONAL_OPTION_SVQ1_EXPANDED,
                investment_option_name="Premium",
                transport_support="Transporte corporativo",
                include_phasing=True,
                include_backup=True,
                start_month=1,
            ),
        )

    if preset_name == SCENARIO_PRESET_TRANSITION_RISK:
        return (
            _scenario(
                name="Escenario A: Transición rápida",
                center_option=OPERATIONAL_OPTION_SVQ1_EXPANDED,
                investment_option_name="Estándar",
                transport_support="Sin apoyo",
                include_phasing=False,
                include_backup=False,
                include_training=False,
                include_incentives=False,
                include_insurance=False,
                start_month=10,
            ),
            _scenario(
                name="Escenario B: Transición controlada",
                center_option=OPERATIONAL_OPTION_SVQ1_EXPANDED,
                investment_option_name="Estándar",
                transport_support="Subsidio transporte público",
                include_phasing=True,
                include_backup=True,
                start_month=1,
            ),
            _scenario(
                name="Escenario C: Transición reforzada",
                center_option=OPERATIONAL_OPTION_SVQ1_EXPANDED,
                investment_option_name="Premium",
                transport_support="Transporte corporativo",
                include_phasing=True,
                include_backup=True,
                start_month=1,
            ),
        )

    valid = ", ".join(SCENARIO_PRESETS)
    raise ValueError(f"Preset de escenarios no reconocido: {preset_name}. Opciones: {valid}")


def build_scenario_configs_from_tree(tree_config: ScenarioTreeConfig) -> ScenarioTreeResult:
    """Genera ScenarioConfig desde ejes seleccionados."""

    axes = (
        tree_config.centers,
        tree_config.investment_options,
        tree_config.transport_supports,
        tree_config.transition_modes,
        tree_config.backup_options,
        tree_config.start_months,
    )
    warnings: list[str] = []
    if any(len(axis) == 0 for axis in axes):
        return ScenarioTreeResult(
            scenarios=(),
            total_combinations=0,
            warnings=("Selecciona al menos un valor en cada eje activo.",),
            limit_exceeded=False,
        )

    total_combinations = 1
    for axis in axes:
        total_combinations *= len(axis)

    if total_combinations > tree_config.max_scenarios:
        return ScenarioTreeResult(
            scenarios=(),
            total_combinations=total_combinations,
            warnings=(
                f"El árbol genera {total_combinations} escenarios y supera el límite "
                f"de {tree_config.max_scenarios}. Reduce ejes u opciones antes de calcular.",
            ),
            limit_exceeded=True,
        )

    scenarios = [
        _scenario_from_tree_values(
            center,
            investment,
            support,
            transition,
            backup,
            start_month,
        )
        for center, investment, support, transition, backup, start_month in product(*axes)
    ]
    return ScenarioTreeResult(
        scenarios=tuple(scenarios),
        total_combinations=total_combinations,
        warnings=tuple(warnings),
        limit_exceeded=False,
    )


def _scenario_from_tree_values(
    center_option: str,
    investment_option_name: str,
    transport_support: str,
    transition_mode: str,
    include_backup: bool,
    start_month: int,
) -> ScenarioConfig:
    include_phasing = transition_mode == TRANSITION_PHASED
    return _scenario(
        name=_scenario_name(
            center_option,
            investment_option_name,
            transport_support,
            transition_mode,
            include_backup,
            start_month,
        ),
        center_option=center_option,
        investment_option_name=investment_option_name,
        transport_support=transport_support,
        include_phasing=include_phasing,
        include_backup=include_backup,
        start_month=start_month,
    )


def _scenario(
    *,
    name: str,
    center_option: str,
    investment_option_name: str,
    transport_support: str,
    include_phasing: bool,
    include_backup: bool,
    start_month: int,
    include_training: bool = True,
    include_incentives: bool = True,
    include_insurance: bool = True,
) -> ScenarioConfig:
    return ScenarioConfig(
        name=name,
        center_option=center_option,
        investment_option_name=investment_option_name,
        transport_support=transport_support,
        include_phasing=include_phasing,
        include_backup=include_backup,
        include_training=include_training,
        include_incentives=include_incentives,
        include_insurance=include_insurance,
        start_month=start_month,
        notes=_scenario_notes(center_option),
    )


def _scenario_name(
    center_option: str,
    investment_option_name: str,
    transport_support: str,
    transition_mode: str,
    include_backup: bool,
    start_month: int,
) -> str:
    backup_label = "Respaldo sí" if include_backup else "Respaldo no"
    month_label = _month_label(start_month)
    return (
        f"{center_option} | {investment_option_name} | {transport_support} | "
        f"{transition_mode} | {backup_label} | {month_label}"
    )


def _month_label(month: int) -> str:
    for label, value in TREE_START_MONTHS.items():
        if value == month:
            return label
    return f"Mes {month}"


def _scenario_notes(center_option: str) -> tuple[str, ...]:
    if center_option == OPERATIONAL_OPTION_CURRENT:
        return ("DQA4 se mantiene como centro de ultima milla para el flujo analizado.",)
    if center_option == OPERATIONAL_OPTION_SVQ1_EXPANDED:
        return ("SVQ1 absorbe la ultima milla del flujo SVQ1-DQA4 analizado.",)
    if center_option == OPERATIONAL_OPTION_INTERMEDIATE:
        return (
            "Se selecciona automaticamente y puede usar un depot virtual con "
            "distancias rectas y tiempos estimados internamente.",
        )
    return ()


def resolve_scenario_depot(
    dataset: Dataset,
    scenario: ScenarioConfig,
    auto_location_selection: AutoLocationSelection | None = None,
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
        return resolve_auto_new_location_dataset(
            dataset,
            auto_location_selection=auto_location_selection,
        )

    raise ValueError(f"Alternativa operativa no reconocida: {scenario.center_option}")


def resolve_auto_new_location_dataset(
    dataset: Dataset,
    *,
    auto_location_selection: AutoLocationSelection | None = None,
) -> tuple[Dataset, tuple[str, ...]]:
    """Crea el dataset operativo para la nueva ubicacion automatica."""
    selection = auto_location_selection or select_auto_new_location(dataset)
    evaluation = selection.selected
    candidate = evaluation.candidate
    base_note = (
        f"{AUTO_NEW_LOCATION_NOTE} Resultado: {candidate.name} "
        f"({evaluation.weighted_mean_distance_km:.1f} km medios ponderados)."
    )

    if candidate.node_index is not None:
        dataset_for_run = dataset_with_depot(dataset, int(candidate.node_index))
        return dataset_for_run, (base_note,)

    virtual_name = f"{VIRTUAL_DEPOT_NAME_PREFIX} - {candidate.name}"
    dataset_for_run = dataset_with_virtual_depot(
        dataset,
        name=virtual_name,
        latitude=candidate.latitude,
        longitude=candidate.longitude,
    )
    return dataset_for_run, (base_note, AUTO_NEW_LOCATION_VIRTUAL_WARNING)


def build_scenario_comparison(
    dataset: Dataset,
    pipeline_config: PipelineConfig,
    comparison_config: ScenarioComparisonConfig | None = None,
    *,
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
    auto_location_selection = (
        select_auto_new_location(dataset)
        if any(scenario.center_option == OPERATIONAL_OPTION_INTERMEDIATE for scenario in scenarios)
        else None
    )

    for scenario in scenarios:
        pipeline_result = None
        scenario_warnings: list[str] = []
        dataset_for_run, depot_notes = resolve_scenario_depot(
            dataset,
            scenario,
            auto_location_selection=auto_location_selection,
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
            warnings=_dedupe(
                (
                    *_filter_intermediate_bridge_warnings(
                        result.warnings,
                        scenario,
                    ),
                    *scenario_warnings,
                )
            ),
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


def _filter_intermediate_bridge_warnings(
    warnings: tuple[str, ...],
    scenario: ScenarioConfig,
) -> tuple[str, ...]:
    if scenario.center_option != OPERATIONAL_OPTION_INTERMEDIATE:
        return warnings
    return tuple(
        warning
        for warning in warnings
        if not warning.startswith(LEGACY_INTERMEDIATE_BRIDGE_WARNING_PREFIX)
    )


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
