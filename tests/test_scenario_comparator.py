"""Tests minimos del comparador de escenarios."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.data_loader import (  # noqa: E402
    DEPOT_NAME,
    SECONDARY_HUB_NAME,
    VIRTUAL_DEPOT_NAME_PREFIX,
    Dataset,
    dataset_with_virtual_depot,
)
from src.economics_model import (  # noqa: E402
    OPERATIONAL_OPTION_CURRENT,
    OPERATIONAL_OPTION_SVQ1_EXPANDED,
)
from src.scenario_comparator import (  # noqa: E402
    AUTO_NEW_LOCATION_NOTE,
    AUTO_NEW_LOCATION_VIRTUAL_WARNING,
    SCENARIO_PRESET_BASIC,
    SCENARIO_PRESET_SVQ1_INVESTMENT,
    SCENARIO_PRESET_TRANSITION_RISK,
    SCENARIO_PRESETS,
    TRANSITION_DIRECT,
    TRANSITION_PHASED,
    ScenarioComparisonConfig,
    ScenarioTreeConfig,
    build_default_scenario_configs,
    build_preset_scenario_configs,
    build_scenario_configs_from_tree,
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


def test_tree_generates_cartesian_combinations() -> None:
    print("test_tree_generates_cartesian_combinations")
    result = build_scenario_configs_from_tree(
        ScenarioTreeConfig(
            centers=(OPERATIONAL_OPTION_SVQ1_EXPANDED,),
            investment_options=("Básica", "Estándar"),
            transport_supports=("Sin apoyo", "Subsidio transporte público"),
            transition_modes=(TRANSITION_PHASED,),
            backup_options=(True,),
            start_months=(1,),
            max_scenarios=12,
        )
    )
    _assert(result.total_combinations == 4, "cuenta combinaciones")
    _assert(len(result.scenarios) == 4, "genera cuatro escenarios")
    names = {scenario.name for scenario in result.scenarios}
    _assert(
        "SVQ1 ampliado | Básica | Sin apoyo | Por fases | Respaldo sí | Enero" in names,
        "nombre determinista de escenario",
    )


def test_tree_svq1_three_investments_generates_three_scenarios() -> None:
    print("test_tree_svq1_three_investments_generates_three_scenarios")
    result = build_scenario_configs_from_tree(
        ScenarioTreeConfig(
            centers=(OPERATIONAL_OPTION_SVQ1_EXPANDED,),
            investment_options=("Básica", "Estándar", "Premium"),
            transport_supports=("Subsidio transporte público",),
            transition_modes=(TRANSITION_PHASED,),
            backup_options=(True,),
            start_months=(1,),
            max_scenarios=12,
        )
    )
    _assert(len(result.scenarios) == 3, "SVQ1 x tres inversiones genera tres")
    _assert(
        {scenario.investment_option_name for scenario in result.scenarios}
        == {"Básica", "Estándar", "Premium"},
        "mantiene inversiones seleccionadas",
    )


def test_presets_generate_valid_scenarios() -> None:
    print("test_presets_generate_valid_scenarios")
    for preset in SCENARIO_PRESETS:
        scenarios = build_preset_scenario_configs(preset)
        _assert(len(scenarios) > 0, f"{preset} genera escenarios")
        _assert(all(scenario.name for scenario in scenarios), f"{preset} tiene nombres")
    basic = build_preset_scenario_configs(SCENARIO_PRESET_BASIC)
    _assert(basic[0].name == "Escenario A: Estructura actual", "preset básico conserva A")
    _assert(len(SCENARIO_PRESETS) == 3, "solo hay tres presets principales")


def test_strategic_preset_matches_main_decision_scenarios() -> None:
    print("test_strategic_preset_matches_main_decision_scenarios")
    scenarios = build_preset_scenario_configs(SCENARIO_PRESET_BASIC)
    _assert(len(scenarios) == 3, "estratégico genera A B C")
    current, svq1, intermediate = scenarios
    _assert(current.center_option == OPERATIONAL_OPTION_CURRENT, "A usa estructura actual")
    _assert(current.investment_option_name == "Básica", "A inversión básica")
    _assert(not current.include_phasing and not current.include_backup, "A sin fases ni respaldo")
    _assert(not current.include_training and not current.include_incentives, "A sin formación ni incentivos")
    _assert(svq1.center_option == OPERATIONAL_OPTION_SVQ1_EXPANDED, "B usa SVQ1 ampliado")
    _assert(svq1.investment_option_name == "Estándar", "B inversión estándar")
    _assert(svq1.transport_support == "Subsidio transporte público", "B subsidio público")
    _assert(svq1.include_phasing and svq1.include_backup, "B con fases y respaldo")
    _assert(intermediate.investment_option_name == "Premium", "C usa inversión premium")
    _assert(intermediate.transport_support == "Transporte corporativo", "C transporte corporativo")


def test_svq1_investment_preset_matches_requested_sensitivity() -> None:
    print("test_svq1_investment_preset_matches_requested_sensitivity")
    scenarios = build_preset_scenario_configs(SCENARIO_PRESET_SVQ1_INVESTMENT)
    investments = [scenario.investment_option_name for scenario in scenarios]
    _assert(investments == ["Básica", "Estándar", "Premium"], "sensibilidad por inversión")
    _assert(not scenarios[0].include_backup, "SVQ1 básico con respaldo no/limitado")
    _assert(scenarios[2].transport_support == "Transporte corporativo", "SVQ1 premium con transporte")


def test_transition_risk_preset_matches_requested_cases() -> None:
    print("test_transition_risk_preset_matches_requested_cases")
    scenarios = build_preset_scenario_configs(SCENARIO_PRESET_TRANSITION_RISK)
    fast, controlled, reinforced = scenarios
    _assert(fast.start_month == 10, "transición rápida empieza en octubre")
    _assert(not fast.include_phasing and not fast.include_backup, "rápida sin fases ni respaldo")
    _assert(not fast.include_training and not fast.include_incentives, "rápida sin formación ni incentivos")
    _assert(controlled.start_month == 1 and controlled.include_phasing, "controlada enero por fases")
    _assert(reinforced.investment_option_name == "Premium", "reforzada premium")


def test_tree_limit_exceeded_warns_and_does_not_generate() -> None:
    print("test_tree_limit_exceeded_warns_and_does_not_generate")
    result = build_scenario_configs_from_tree(
        ScenarioTreeConfig(
            centers=(OPERATIONAL_OPTION_CURRENT, OPERATIONAL_OPTION_SVQ1_EXPANDED),
            investment_options=("Básica", "Estándar", "Premium"),
            transport_supports=("Sin apoyo", "Subsidio transporte público"),
            transition_modes=(TRANSITION_DIRECT, TRANSITION_PHASED),
            backup_options=(True, False),
            start_months=(1, 7),
            max_scenarios=12,
        )
    )
    _assert(result.limit_exceeded, "activa límite excedido")
    _assert(len(result.scenarios) == 0, "no genera escenarios al exceder límite")
    _assert(bool(result.warnings), "incluye warning de límite")


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


def test_comparison_accepts_tree_generated_scenarios() -> None:
    print("test_comparison_accepts_tree_generated_scenarios")
    calls: list[str] = []
    tree = build_scenario_configs_from_tree(
        ScenarioTreeConfig(
            centers=(OPERATIONAL_OPTION_SVQ1_EXPANDED,),
            investment_options=("Básica", "Estándar", "Premium"),
            transport_supports=("Subsidio transporte público",),
            transition_modes=(TRANSITION_PHASED,),
            backup_options=(True,),
            start_months=(1,),
            max_scenarios=12,
        )
    )
    comparison = build_scenario_comparison(
        _dataset(),
        pipeline_config=object(),
        comparison_config=ScenarioComparisonConfig(scenarios=tree.scenarios),
        pipeline_runner=_runner(calls),
    )
    _assert(len(comparison.results) == 3, "compara escenarios del árbol")
    _assert(calls == [DEPOT_NAME, DEPOT_NAME, DEPOT_NAME], "rutas SVQ1 para los tres")


def test_virtual_depot_preserves_existing_od_matrices() -> None:
    print("test_virtual_depot_preserves_existing_od_matrices")
    dataset = _dataset()
    virtual = dataset_with_virtual_depot(
        dataset,
        name=f"{VIRTUAL_DEPOT_NAME_PREFIX} test",
        latitude=0.5,
        longitude=0.5,
    )
    _assert(virtual.n_nodes == dataset.n_nodes + 1, "añade un nodo virtual")
    _assert(virtual.depot_index == dataset.n_nodes, "depot virtual queda al final")
    _assert(virtual.poblacion[virtual.depot_index] == 0, "depot virtual sin demanda")
    _assert(
        np.allclose(
            virtual.distance_matrix[: dataset.n_nodes, : dataset.n_nodes],
            dataset.distance_matrix,
        ),
        "conserva matriz de distancia original",
    )
    _assert(
        np.allclose(
            virtual.time_matrix[: dataset.n_nodes, : dataset.n_nodes],
            dataset.time_matrix,
        ),
        "conserva matriz de tiempo original",
    )
    _assert(
        np.all(virtual.distance_matrix[virtual.depot_index, : dataset.n_nodes] >= 0),
        "calcula distancias desde depot virtual",
    )


def test_intermediate_auto_location_uses_virtual_depot() -> None:
    print("test_intermediate_auto_location_uses_virtual_depot")
    calls: list[str] = []
    comparison = build_scenario_comparison(
        _dataset(),
        pipeline_config=object(),
        comparison_config=ScenarioComparisonConfig(
            scenarios=build_default_scenario_configs(include_intermediate=True)
        ),
        pipeline_runner=_runner(calls),
    )
    intermediate = comparison.results[-1]
    _assert(
        intermediate.operational_economic_result is not None,
        "calcula rutas con depot virtual automatico",
    )
    _assert(
        calls[-1].startswith(VIRTUAL_DEPOT_NAME_PREFIX),
        "usa depot virtual para nueva ubicacion continua",
    )
    _assert(
        any(warning.startswith(AUTO_NEW_LOCATION_NOTE) for warning in intermediate.warnings),
        "documenta seleccion automatica",
    )
    _assert(
        AUTO_NEW_LOCATION_VIRTUAL_WARNING in intermediate.warnings,
        "documenta tiempos estimados internamente",
    )


def test_resolve_scenario_depot_uses_expected_hubs() -> None:
    print("test_resolve_scenario_depot_uses_expected_hubs")
    dataset = _dataset()
    current = build_default_scenario_configs(include_intermediate=False)[0]
    expanded = build_default_scenario_configs(include_intermediate=False)[1]
    intermediate = build_default_scenario_configs(include_intermediate=True)[2]
    current_dataset, _ = resolve_scenario_depot(dataset, current)
    expanded_dataset, _ = resolve_scenario_depot(dataset, expanded)
    intermediate_dataset, notes = resolve_scenario_depot(dataset, intermediate)
    _assert(
        current_dataset.names[current_dataset.depot_index] == SECONDARY_HUB_NAME,
        "estructura actual usa DQA4",
    )
    _assert(
        expanded_dataset.names[expanded_dataset.depot_index] == DEPOT_NAME,
        "SVQ1 ampliado usa SVQ1",
    )
    _assert(
        intermediate_dataset.names[intermediate_dataset.depot_index].startswith(
            VIRTUAL_DEPOT_NAME_PREFIX
        ),
        "nuevo centro usa seleccion automatica",
    )
    _assert(any(note.startswith(AUTO_NEW_LOCATION_NOTE) for note in notes), "devuelve nota automatica")


def main() -> None:
    test_default_scenarios_include_current_and_svq1()
    test_tree_generates_cartesian_combinations()
    test_tree_svq1_three_investments_generates_three_scenarios()
    test_presets_generate_valid_scenarios()
    test_strategic_preset_matches_main_decision_scenarios()
    test_svq1_investment_preset_matches_requested_sensitivity()
    test_transition_risk_preset_matches_requested_cases()
    test_tree_limit_exceeded_warns_and_does_not_generate()
    test_comparison_builds_multiple_scenario_results()
    test_comparison_frame_contains_key_columns()
    test_comparison_accepts_tree_generated_scenarios()
    test_virtual_depot_preserves_existing_od_matrices()
    test_intermediate_auto_location_uses_virtual_depot()
    test_resolve_scenario_depot_uses_expected_hubs()
    print("\nTodos los tests del comparador de escenarios OK")


if __name__ == "__main__":
    main()
