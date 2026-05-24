"""Tests for the one-page academic guided flow helpers."""

from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.data_loader import DEPOT_NAME, SECONDARY_HUB_NAME, Dataset  # noqa: E402
from src.economics_model import (  # noqa: E402
    OPERATIONAL_OPTION_CURRENT,
    OPERATIONAL_OPTION_INTERMEDIATE,
    OPERATIONAL_OPTION_SVQ1_EXPANDED,
)
from src.guided_flow import (  # noqa: E402
    GuidedFlowConfig,
    build_guided_flow_scenarios,
    guided_economics_signature,
    guided_route_signature,
    normalize_guided_center_options,
)
from src.pipeline import PipelineConfig  # noqa: E402


def _dataset() -> Dataset:
    distance = np.array(
        [
            [0.0, 10.0, 20.0],
            [10.0, 0.0, 12.0],
            [20.0, 12.0, 0.0],
        ]
    )
    time = np.array(
        [
            [0.0, 15.0, 30.0],
            [15.0, 0.0, 18.0],
            [30.0, 18.0, 0.0],
        ]
    )
    return Dataset(
        names=[DEPOT_NAME, SECONDARY_HUB_NAME, "Nodo A"],
        latitudes=np.array([0.0, 1.0, 2.0]),
        longitudes=np.array([0.0, 1.0, 2.0]),
        restringe_camion=np.array([0, 0, 0]),
        poblacion=np.array([0, 0, 100]),
        distance_matrix=distance,
        time_matrix=time,
        depot_index=0,
    )


def _pipeline_config() -> PipelineConfig:
    return PipelineConfig(
        market_penetration=0.01,
        max_workday_hours=7.5,
        service_time_per_package_min=1.5,
        inter_package_time_min=1.0,
    )


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)
    print(f"  OK {message}")


def test_current_structure_is_mandatory_and_first() -> None:
    print("test_current_structure_is_mandatory_and_first")
    centers = normalize_guided_center_options((OPERATIONAL_OPTION_SVQ1_EXPANDED,))
    _assert(centers[0] == OPERATIONAL_OPTION_CURRENT, "estructura actual obligatoria")
    _assert(OPERATIONAL_OPTION_SVQ1_EXPANDED in centers, "mantiene SVQ1 seleccionado")


def test_guided_scenarios_do_not_build_combinatorial_tree() -> None:
    print("test_guided_scenarios_do_not_build_combinatorial_tree")
    scenarios = build_guided_flow_scenarios(
        GuidedFlowConfig(
            center_options=(
                OPERATIONAL_OPTION_CURRENT,
                OPERATIONAL_OPTION_SVQ1_EXPANDED,
            ),
            investment_option_name="Premium",
            transport_support="Transporte corporativo",
        )
    )
    _assert(len(scenarios) == 2, "solo genera alternativas elegidas")
    _assert(
        [scenario.center_option for scenario in scenarios]
        == [OPERATIONAL_OPTION_CURRENT, OPERATIONAL_OPTION_SVQ1_EXPANDED],
        "no expande ejes combinatorios",
    )
    _assert(scenarios[0].investment_option_name == "Básica", "referencia sin inversión nueva")
    _assert(scenarios[1].investment_option_name == "Premium", "alternativa usa inversión elegida")


def test_intermediate_is_only_included_when_selected() -> None:
    print("test_intermediate_is_only_included_when_selected")
    without_intermediate = build_guided_flow_scenarios(GuidedFlowConfig())
    with_intermediate = build_guided_flow_scenarios(
        GuidedFlowConfig(
            center_options=(
                OPERATIONAL_OPTION_CURRENT,
                OPERATIONAL_OPTION_SVQ1_EXPANDED,
                OPERATIONAL_OPTION_INTERMEDIATE,
            )
        )
    )
    _assert(
        OPERATIONAL_OPTION_INTERMEDIATE
        not in {scenario.center_option for scenario in without_intermediate},
        "intermedio no aparece por defecto",
    )
    _assert(
        OPERATIONAL_OPTION_INTERMEDIATE
        in {scenario.center_option for scenario in with_intermediate},
        "intermedio aparece al seleccionarlo",
    )


def test_economic_choices_do_not_change_route_signature() -> None:
    print("test_economic_choices_do_not_change_route_signature")
    dataset = _dataset()
    pipeline_config = _pipeline_config()
    centers = (OPERATIONAL_OPTION_CURRENT, OPERATIONAL_OPTION_SVQ1_EXPANDED)
    route_signature = guided_route_signature(centers, dataset, pipeline_config)

    basic = GuidedFlowConfig(center_options=centers, investment_option_name="Básica")
    premium = GuidedFlowConfig(
        center_options=centers,
        investment_option_name="Premium",
        transport_support="Transporte corporativo",
        include_backup=False,
        start_month=10,
    )
    horizon_changed = GuidedFlowConfig(center_options=centers, economic_horizon_years=12)
    rate_changed = GuidedFlowConfig(center_options=centers, economic_discount_rate=0.09)
    _assert(
        guided_route_signature(centers, dataset, pipeline_config) == route_signature,
        "firma de rutas estable ante decisiones económicas",
    )
    _assert(
        guided_economics_signature(basic, route_signature)
        != guided_economics_signature(premium, route_signature),
        "firma económica sí cambia",
    )
    _assert(
        guided_economics_signature(basic, route_signature)
        != guided_economics_signature(horizon_changed, route_signature),
        "firma económica cambia con horizonte",
    )
    _assert(
        guided_economics_signature(basic, route_signature)
        != guided_economics_signature(rate_changed, route_signature),
        "firma económica cambia con tasa",
    )


def test_route_choices_change_route_signature() -> None:
    print("test_route_choices_change_route_signature")
    dataset = _dataset()
    config = _pipeline_config()
    centers = (OPERATIONAL_OPTION_CURRENT, OPERATIONAL_OPTION_SVQ1_EXPANDED)
    base = guided_route_signature(centers, dataset, config)
    demand_changed = guided_route_signature(
        centers,
        dataset,
        replace(config, market_penetration=0.02),
    )
    workday_changed = guided_route_signature(
        centers,
        dataset,
        replace(config, max_workday_hours=8.0),
    )
    _assert(base != demand_changed, "cambiar demanda invalida rutas")
    _assert(base != workday_changed, "cambiar jornada invalida rutas")


def main() -> None:
    test_current_structure_is_mandatory_and_first()
    test_guided_scenarios_do_not_build_combinatorial_tree()
    test_intermediate_is_only_included_when_selected()
    test_economic_choices_do_not_change_route_signature()
    test_route_choices_change_route_signature()
    print("\nTodos los tests de flujo guiado OK")


if __name__ == "__main__":
    main()
