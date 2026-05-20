"""Tests minimos de la capa ScenarioConfig / ScenarioResult."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.economics_model import (  # noqa: E402
    DEFAULT_OPTIONS,
    AdditionalCostParams,
    FinanceParams,
    OPERATIONAL_OPTION_CURRENT,
    OPERATIONAL_OPTION_SVQ1_EXPANDED,
    compute_economic_result,
)
from src.risk_model import RiskAssessment  # noqa: E402
from src.scenario_model import (  # noqa: E402
    NO_ROUTES_WARNING,
    ScenarioConfig,
    ScenarioResult,
    build_scenario_result,
    scenario_results_frame,
)


def approx(actual: float, expected: float, tolerance: float, msg: str) -> None:
    if abs(actual - expected) > tolerance:
        raise AssertionError(f"{msg}: esperado {expected}, obtenido {actual}")
    print(f"  OK {msg}")


def _fake_pipeline_result(depot_index: int = 0):
    dataset = SimpleNamespace(
        names=["SVQ1", "DQA4", "Nodo A"],
        depot_index=depot_index,
    )
    return SimpleNamespace(
        dataset=dataset,
        packages=np.array([0, 20, 30]),
        total_routes=8,
        vrp_route_count=5,
        dedicated_route_count=3,
        trailer_route_count=1,
        van_dedicated_route_count=2,
        total_distance_km=640.5,
        total_time_min=1_230.0,
        vrp=SimpleNamespace(diesel_count=4, electric_count=1),
    )


def test_build_scenario_result_groups_existing_outputs() -> None:
    print("test_build_scenario_result_groups_existing_outputs")
    config = ScenarioConfig(
        center_option=OPERATIONAL_OPTION_SVQ1_EXPANDED,
        investment_option_name="Estándar",
    )
    result = build_scenario_result(
        config,
        pipeline_result=_fake_pipeline_result(),
        route_params={"seasonality_multiplier": 1.25},
    )
    if not isinstance(result, ScenarioResult):
        raise AssertionError("Debe devolver ScenarioResult")
    if result.economic_result.option_name != "Estándar":
        raise AssertionError("Debe calcular economia con la opcion seleccionada")
    if result.operational_economic_result is None:
        raise AssertionError("Debe calcular lectura operativa si hay pipeline_result")
    if result.labor_result.summary.acceptability not in {"Alta", "Media", "Baja"}:
        raise AssertionError("Debe incluir resultado laboral")
    if result.timeline_result.start_month != config.start_month:
        raise AssertionError("Debe incluir cronograma con start_month del config")
    if not isinstance(result.risk_assessment, RiskAssessment):
        raise AssertionError("Debe incluir evaluacion de riesgos")
    approx(
        result.total_expected_risk_cost,
        result.risk_assessment.total_residual_expected_cost,
        1e-9,
        "Coste de riesgo residual agregado",
    )


def test_without_pipeline_result_adds_warning() -> None:
    print("test_without_pipeline_result_adds_warning")
    result = build_scenario_result(ScenarioConfig(), pipeline_result=None)
    if result.operational_economic_result is not None:
        raise AssertionError("Sin rutas no debe inventar resultado operativo")
    if NO_ROUTES_WARNING not in result.warnings:
        raise AssertionError("Debe avisar que no hay rutas calculadas")
    approx(result.adjusted_operational_saving, 0.0, 1e-9, "Ahorro operativo sin rutas")


def test_default_config_uses_current_structure() -> None:
    print("test_default_config_uses_current_structure")
    config = ScenarioConfig()
    if config.center_option != OPERATIONAL_OPTION_CURRENT:
        raise AssertionError("ScenarioConfig por defecto debe usar Estructura actual")
    print("  OK estructura actual por defecto")


def test_scenario_results_frame_has_summary_row() -> None:
    print("test_scenario_results_frame_has_summary_row")
    result = build_scenario_result(ScenarioConfig(name="Base"), pipeline_result=None)
    frame = scenario_results_frame([result])
    if len(frame) != 1:
        raise AssertionError("Debe generar una fila por escenario")
    row = frame.iloc[0]
    approx(row["CAPEX total"], result.capex_total, 1e-9, "CAPEX en tabla")
    approx(row["Ahorro neto anual"], result.net_savings_annual, 1e-9, "Ahorro neto en tabla")
    approx(row["Coste riesgo"], result.total_expected_risk_cost, 1e-9, "Coste riesgo en tabla")


def test_build_scenario_result_does_not_modify_compute_economic_result() -> None:
    print("test_build_scenario_result_does_not_modify_compute_economic_result")
    additional = AdditionalCostParams()
    finance = FinanceParams()
    before = compute_economic_result(DEFAULT_OPTIONS[1], additional, finance)
    build_scenario_result(ScenarioConfig(), pipeline_result=_fake_pipeline_result())
    after = compute_economic_result(DEFAULT_OPTIONS[1], additional, finance)
    approx(after.capex_total, before.capex_total, 1e-9, "CAPEX estable")
    approx(after.opex_new_annual, before.opex_new_annual, 1e-9, "OPEX estable")
    approx(after.van, before.van, 1e-9, "VAN estable")


def main() -> None:
    test_build_scenario_result_groups_existing_outputs()
    test_without_pipeline_result_adds_warning()
    test_default_config_uses_current_structure()
    test_scenario_results_frame_has_summary_row()
    test_build_scenario_result_does_not_modify_compute_economic_result()
    print("\nTodos los tests de escenario OK")


if __name__ == "__main__":
    main()
