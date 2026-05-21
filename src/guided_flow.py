"""Helpers for the simple academic guided flow.

This module keeps the guided Streamlit page as a thin presentation layer.  It
builds only the selected academic alternatives and provides cache signatures so
route calculations can be reused when users edit purely economic decisions.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np

from .data_loader import DEPOT_NAME, SECONDARY_HUB_NAME, dataset_with_depot
from .economics_model import (
    DEFAULT_DQA4_ATTRIBUTABLE_SHARE,
    OPERATIONAL_OPTION_CURRENT,
    OPERATIONAL_OPTION_INTERMEDIATE,
    OPERATIONAL_OPTION_SVQ1_EXPANDED,
    OPERATIONAL_OPTIONS,
)
from .pipeline import PipelineConfig, PipelineResult
from .scenario_model import ScenarioConfig, ScenarioResult, build_scenario_result


ROUTE_CENTER_CURRENT_DQA4 = "current_dqa4"
ROUTE_CENTER_SVQ1_EXPANDED = "svq1_expanded"
ROUTE_CENTER_OPTIMAL_REFERENCE = "optimal_reference"
ROUTE_CENTER_HEURISTIC_INTERMEDIATE = "heuristic_intermediate"

ROUTABLE_CENTER_ORDER: tuple[str, ...] = (
    ROUTE_CENTER_CURRENT_DQA4,
    ROUTE_CENTER_SVQ1_EXPANDED,
    ROUTE_CENTER_OPTIMAL_REFERENCE,
    ROUTE_CENTER_HEURISTIC_INTERMEDIATE,
)

ROUTABLE_CENTER_CANDIDATES: dict[str, dict[str, object]] = {
    ROUTE_CENTER_CURRENT_DQA4: {
        "node_index": 1,
        "label": "DQA4 actual",
        "description": "Referencia operativa actual de ultima milla.",
    },
    ROUTE_CENTER_SVQ1_EXPANDED: {
        "node_index": 0,
        "label": "SVQ1 ampliado",
        "description": "Escenario de fusion operativa en SVQ1.",
    },
    ROUTE_CENTER_OPTIMAL_REFERENCE: {
        "node_index": 2,
        "label": "Centro optimo / referencia",
        "description": "Centro obtenido como referencia de localizacion.",
    },
    ROUTE_CENTER_HEURISTIC_INTERMEDIATE: {
        "node_index": 3,
        "label": "Intermedio heuristico",
        "description": "Centro intermedio de contraste.",
    },
}

GUIDED_CENTER_ORDER: tuple[str, ...] = (
    OPERATIONAL_OPTION_CURRENT,
    OPERATIONAL_OPTION_SVQ1_EXPANDED,
    OPERATIONAL_OPTION_INTERMEDIATE,
)


@dataclass(frozen=True)
class GuidedFlowConfig:
    """Simple decisions exposed by the academic guided flow."""

    center_options: tuple[str, ...] = (
        OPERATIONAL_OPTION_CURRENT,
        OPERATIONAL_OPTION_SVQ1_EXPANDED,
    )
    investment_option_name: str = "Estándar"
    transport_support: str = "Subsidio transporte público"
    include_training: bool = True
    include_phasing: bool = True
    include_backup: bool = True
    include_insurance: bool = False
    include_incentives: bool = False
    start_month: int = 1
    dqa4_attributable_share: float = DEFAULT_DQA4_ATTRIBUTABLE_SHARE


@dataclass(frozen=True)
class GuidedFlowRun:
    """One guided alternative, including route and integrated scenario output."""

    scenario: ScenarioConfig
    result: ScenarioResult
    pipeline_result: PipelineResult | None
    notes: tuple[str, ...] = ()
    error: str | None = None


def normalize_guided_center_options(center_options: Iterable[str]) -> tuple[str, ...]:
    """Return selected centers in guided order, always keeping current as base."""

    selected = {str(option) for option in center_options}
    selected.add(OPERATIONAL_OPTION_CURRENT)
    unknown = selected.difference(OPERATIONAL_OPTIONS)
    if unknown:
        valid = ", ".join(OPERATIONAL_OPTIONS)
        raise ValueError(f"Alternativas no reconocidas: {sorted(unknown)}. Opciones: {valid}")
    return tuple(option for option in GUIDED_CENTER_ORDER if option in selected)


def normalize_guided_route_center_keys(center_keys: Iterable[str]) -> tuple[str, ...]:
    """Return selected routable centers in fixed order, always keeping DQA4."""

    selected = {_coerce_route_center_key(str(option)) for option in center_keys}
    selected.add(ROUTE_CENTER_CURRENT_DQA4)
    unknown = selected.difference(ROUTABLE_CENTER_CANDIDATES)
    if unknown:
        valid = ", ".join(ROUTABLE_CENTER_CANDIDATES)
        raise ValueError(f"Centros de rutas no reconocidos: {sorted(unknown)}. Opciones: {valid}")
    return tuple(option for option in ROUTABLE_CENTER_ORDER if option in selected)


def guided_center_label(center_key: str) -> str:
    """Human label for a routable center key."""

    center_key = _coerce_route_center_key(center_key)
    candidate = ROUTABLE_CENTER_CANDIDATES.get(center_key)
    if candidate is None:
        return str(center_key)
    return str(candidate["label"])


def get_routable_center_candidates(dataset) -> dict[str, dict[str, object]]:
    """Validate and return the routable centers available in the loaded OD matrix."""

    candidates: dict[str, dict[str, object]] = {}
    for key, definition in ROUTABLE_CENTER_CANDIDATES.items():
        node_index = int(definition["node_index"])
        if node_index < 0 or node_index >= dataset.n_nodes:
            raise ValueError(
                f"El centro '{definition['label']}' usa node_index {node_index}, "
                f"pero el dataset solo tiene {dataset.n_nodes} nodos"
            )
        candidates[key] = {
            **definition,
            "node_index": node_index,
            "node_name": dataset.names[node_index],
        }

    if dataset.names[int(candidates[ROUTE_CENTER_CURRENT_DQA4]["node_index"])] != SECONDARY_HUB_NAME:
        raise ValueError("La matriz OD v2 no tiene DQA4 en el indice esperado para FG")
    if dataset.names[int(candidates[ROUTE_CENTER_SVQ1_EXPANDED]["node_index"])] != DEPOT_NAME:
        raise ValueError("La matriz OD v2 no tiene SVQ1 en el indice esperado para FG")
    return candidates


def resolve_guided_route_dataset(dataset, center_key: str):
    """Return a dataset view with the selected routable center as depot."""

    center_key = _coerce_route_center_key(center_key)
    candidates = get_routable_center_candidates(dataset)
    if center_key not in candidates:
        valid = ", ".join(candidates)
        raise ValueError(f"Centro de rutas no reconocido: {center_key}. Opciones: {valid}")
    return dataset_with_depot(dataset, int(candidates[center_key]["node_index"]))


def guided_route_center_to_operational_option(center_key: str) -> str:
    """Map a route-center key to the existing economic/scenario option set."""

    center_key = _coerce_route_center_key(center_key)
    if center_key == ROUTE_CENTER_CURRENT_DQA4:
        return OPERATIONAL_OPTION_CURRENT
    if center_key == ROUTE_CENTER_SVQ1_EXPANDED:
        return OPERATIONAL_OPTION_SVQ1_EXPANDED
    if center_key in {
        ROUTE_CENTER_OPTIMAL_REFERENCE,
        ROUTE_CENTER_HEURISTIC_INTERMEDIATE,
    }:
        return OPERATIONAL_OPTION_INTERMEDIATE
    raise ValueError(f"Centro de rutas no reconocido: {center_key}")


def guided_route_centers_to_operational_options(center_keys: Iterable[str]) -> tuple[str, ...]:
    """Collapse selected route centers to the existing economic options."""

    selected: list[str] = []
    for center_key in normalize_guided_route_center_keys(center_keys):
        option = guided_route_center_to_operational_option(center_key)
        if option not in selected:
            selected.append(option)
    return normalize_guided_center_options(selected)


def build_guided_flow_scenarios(config: GuidedFlowConfig) -> tuple[ScenarioConfig, ...]:
    """Build only the alternatives selected in the one-page guided flow."""

    return tuple(
        _guided_scenario_for_center(center_option, config)
        for center_option in normalize_guided_center_options(config.center_options)
    )


def make_guided_flow_run(
    scenario: ScenarioConfig,
    *,
    pipeline_result: PipelineResult | None,
    route_params: dict | None = None,
    notes: tuple[str, ...] = (),
    error: str | None = None,
) -> GuidedFlowRun:
    """Create a guided run without recalculating routes."""

    result = build_scenario_result(
        scenario,
        pipeline_result=pipeline_result,
        route_params=route_params,
    )
    return GuidedFlowRun(
        scenario=scenario,
        result=result,
        pipeline_result=pipeline_result,
        notes=tuple(notes),
        error=error,
    )


def guided_route_signature(
    center_options: Iterable[str],
    dataset,
    pipeline_config: PipelineConfig,
) -> tuple:
    """Signature for route cache; it intentionally excludes economic choices."""

    return (
        "guided_flow_routes_v2",
        normalize_guided_route_center_keys(center_options),
        _dataset_signature(dataset),
        _pipeline_route_signature(pipeline_config),
    )


def guided_economics_signature(
    config: GuidedFlowConfig,
    route_signature: tuple,
) -> tuple:
    """Signature for integrated economics built on top of cached routes."""

    return (
        "guided_flow_economics_v1",
        route_signature,
        normalize_guided_center_options(config.center_options),
        config.investment_option_name,
        config.transport_support,
        bool(config.include_training),
        bool(config.include_phasing),
        bool(config.include_backup),
        bool(config.include_insurance),
        bool(config.include_incentives),
        int(config.start_month),
        float(config.dqa4_attributable_share),
    )


def _guided_scenario_for_center(
    center_option: str,
    config: GuidedFlowConfig,
) -> ScenarioConfig:
    if center_option == OPERATIONAL_OPTION_CURRENT:
        return ScenarioConfig(
            name="Referencia: estructura actual (DQA4)",
            center_option=OPERATIONAL_OPTION_CURRENT,
            investment_option_name="Básica",
            transport_support="Sin apoyo",
            include_phasing=False,
            include_backup=False,
            include_training=False,
            include_incentives=False,
            include_insurance=False,
            start_month=1,
            notes=("DQA4 se mantiene como centro de ultima milla para el flujo analizado.",),
        )

    if center_option == OPERATIONAL_OPTION_SVQ1_EXPANDED:
        name = "Alternativa: SVQ1 ampliado"
        notes = ("SVQ1 absorbe la ultima milla del flujo SVQ1-DQA4 analizado.",)
    elif center_option == OPERATIONAL_OPTION_INTERMEDIATE:
        name = "Contraste académico: nuevo centro/intermedio"
        notes = (
            "Centro de contraste academico; en FG las rutas usan el nodo OD v2 seleccionado.",
        )
    else:
        valid = ", ".join(OPERATIONAL_OPTIONS)
        raise ValueError(f"Alternativa operativa no reconocida: {center_option}. Opciones: {valid}")

    return ScenarioConfig(
        name=name,
        center_option=center_option,
        investment_option_name=config.investment_option_name,
        transport_support=config.transport_support,
        include_phasing=config.include_phasing,
        include_backup=config.include_backup,
        include_training=True,
        include_incentives=True,
        include_insurance=True,
        start_month=int(config.start_month),
        dqa4_attributable_share=float(config.dqa4_attributable_share),
        notes=notes,
    )


def _coerce_route_center_key(value: str) -> str:
    if value == OPERATIONAL_OPTION_CURRENT:
        return ROUTE_CENTER_CURRENT_DQA4
    if value == OPERATIONAL_OPTION_SVQ1_EXPANDED:
        return ROUTE_CENTER_SVQ1_EXPANDED
    if value == OPERATIONAL_OPTION_INTERMEDIATE:
        return ROUTE_CENTER_OPTIMAL_REFERENCE
    return value


def _dataset_signature(dataset) -> tuple:
    return (
        tuple(str(name) for name in dataset.names),
        tuple(int(value) for value in np.asarray(dataset.poblacion).tolist()),
        int(dataset.depot_index),
    )


def _pipeline_route_signature(config: PipelineConfig) -> tuple:
    return (
        float(config.market_penetration),
        float(config.max_workday_hours),
        float(config.service_time_per_package_min),
        float(config.inter_package_time_min),
        float(config.seasonality_multiplier),
        None if config.target_daily_volume is None else float(config.target_daily_volume),
        repr(config.fleet),
        repr(config.trailer),
        repr(config.schedule),
        str(config.solver_strategy),
        int(config.solver_time_limit_seconds),
    )
