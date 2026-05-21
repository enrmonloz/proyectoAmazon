"""Helpers for the simple academic guided flow.

This module keeps the guided Streamlit page as a thin presentation layer.  It
builds only the selected academic alternatives and provides cache signatures so
route calculations can be reused when users edit purely economic decisions.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np

from .economics_model import (
    DEFAULT_DQA4_ATTRIBUTABLE_SHARE,
    OPERATIONAL_OPTION_CURRENT,
    OPERATIONAL_OPTION_INTERMEDIATE,
    OPERATIONAL_OPTION_SVQ1_EXPANDED,
    OPERATIONAL_OPTIONS,
)
from .pipeline import PipelineConfig, PipelineResult
from .scenario_model import ScenarioConfig, ScenarioResult, build_scenario_result


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
    include_phasing: bool = True
    include_backup: bool = True
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
        "guided_flow_routes_v1",
        normalize_guided_center_options(center_options),
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
        bool(config.include_phasing),
        bool(config.include_backup),
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
            "Centro de contraste seleccionado automaticamente; puede usar depot virtual.",
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
