"""Tests minimos del comparador de escenarios."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.data_loader import DEPOT_NAME, SECONDARY_HUB_NAME, Dataset  # noqa: E402
from src.economics_model import (  # noqa: E402
    OPERATIONAL_OPTION_CURRENT,
    OPERATIONAL_OPTION_SVQ1_EXPANDED,
)
from src.scenario_comparator import (  # noqa: E402
    INTERMEDIATE_NO_OD_WARNING,
    ScenarioComparisonConfig,
    build_default_scenario_configs,
    build_scenario_comparison,
    resolve_scenario_depot,
)
from src.scenario_model import ScenarioResult  # noqa: E402


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
        names=[DEPOT_NAME, SECONDARY_HUB_NAME, "Nodo intermedio"],
        latitudes=np.array([0.0, 1.0, 2.0]),
        longitudes=np.array([0.0, 1.0, 2.0]),
        restringe_camion=np.array([0, 0, 0]),
        poblacion=np.array([0, 0, 100]),
        distance_matrix=distance,
        time_matrix=time,
        depot_index=0,
    )


def _fake_pipeline_result(dataset: Dataset):
    return SimpleNamespace(
        dataset=dataset,
        packages=np.array([0, 0, 50]),
        total_routes=4,
        vrp_route_count=3,
        dedicated_route_count=1,
        trailer_route_count=0,
        van_dedicated_route_count=1,
        total_distance_km=123.0 + dataset.depot_index,
        total_time_min=345.0 + dataset.depot_index,
        vrp=SimpleNamespace(diesel_count=2, electric_count=1),
    )


def _runner(calls: list[str]):
    def run(dataset: Dataset, _config):
        calls.append(dataset.names[dataset.depot_index])
        return _fake_pipeline_result(dataset)

    return run


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)
    print(f"  OK {message}")


def test_default_scenarios_include_current_and_svq1() -> None:
    print("test_default_scenarios_include_current_and_svq1")
    scenarios = build_default_scenario_configs(include_intermediate=False)
    options = {scenario.center_option for scenario in scenarios}
    _assert(OPERATIONAL_OPTION_CURRENT in options, "incluye estructura actual")
    _assert(OPERATIONAL_OPTION_SVQ1_EXPANDED in options, "incluye SVQ1 ampliado")


def test_comparison_builds_multiple_scenario_results() -> None:
    print("test_comparison_builds_multiple_scenario_results")
    calls: list[str] = []
    config = ScenarioComparisonConfig(
        scenarios=build_default_scenario_configs(include_intermediate=False)
    )
    comparison = build_scenario_comparison(
        _dataset(),
        pipeline_config=object(),
        comparison_config=config,
        route_params={"seasonality_multiplier": 1.0},
        pipeline_runner=_runner(calls),
    )
    _assert(len(comparison.results) == 2, "construye dos escenarios")
    _assert(
        all(isinstance(result, ScenarioResult) for result in comparison.results),
        "cada resultado es ScenarioResult",
    )
    _assert(calls == [SECONDARY_HUB_NAME, DEPOT_NAME], "usa DQA4 y despues SVQ1")


def test_comparison_frame_contains_key_columns() -> None:
    print("test_comparison_frame_contains_key_columns")
    comparison = build_scenario_comparison(
        _dataset(),
        pipeline_config=object(),
        comparison_config=ScenarioComparisonConfig(
            scenarios=build_default_scenario_configs(include_intermediate=False)
        ),
        pipeline_runner=_runner([]),
    )
    expected = {
        "Escenario",
        "Centro de reparto",
        "Rutas totales",
        "CAPEX total",
        "Ahorro neto anual",
        "Coste medio de riesgos",
        "Aceptabilidad laboral",
        "Viabilidad preliminar",
        "Warnings",
    }
    _assert(expected.issubset(set(comparison.comparison_frame.columns)), "columnas clave")


def test_intermediate_without_od_node_emits_warning() -> None:
    print("test_intermediate_without_od_node_emits_warning")
    comparison = build_scenario_comparison(
        _dataset(),
        pipeline_config=object(),
        comparison_config=ScenarioComparisonConfig(
            scenarios=build_default_scenario_configs(include_intermediate=True)
        ),
        pipeline_runner=_runner([]),
    )
    intermediate = comparison.results[-1]
    _assert(INTERMEDIATE_NO_OD_WARNING in intermediate.warnings, "warning sin nodo OD")
    _assert(
        intermediate.operational_economic_result is None,
        "no calcula rutas intermedias sin nodo OD",
    )


def test_resolve_scenario_depot_uses_expected_hubs() -> None:
    print("test_resolve_scenario_depot_uses_expected_hubs")
    dataset = _dataset()
    current = build_default_scenario_configs(include_intermediate=False)[0]
    expanded = build_default_scenario_configs(include_intermediate=False)[1]
    current_dataset, _ = resolve_scenario_depot(dataset, current)
    expanded_dataset, _ = resolve_scenario_depot(dataset, expanded)
    _assert(
        current_dataset.names[current_dataset.depot_index] == SECONDARY_HUB_NAME,
        "estructura actual usa DQA4",
    )
    _assert(
        expanded_dataset.names[expanded_dataset.depot_index] == DEPOT_NAME,
        "SVQ1 ampliado usa SVQ1",
    )


def main() -> None:
    test_default_scenarios_include_current_and_svq1()
    test_comparison_builds_multiple_scenario_results()
    test_comparison_frame_contains_key_columns()
    test_intermediate_without_od_node_emits_warning()
    test_resolve_scenario_depot_uses_expected_hubs()
    print("\nTodos los tests del comparador de escenarios OK")


if __name__ == "__main__":
    main()
