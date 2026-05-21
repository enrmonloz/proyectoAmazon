"""Tests for guided-flow routable centers backed by the OD v2 matrix."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.data_loader import DEPOT_NAME, SECONDARY_HUB_NAME, Dataset, load_dataset  # noqa: E402
from src.guided_flow import (  # noqa: E402
    ROUTE_CENTER_CURRENT_DQA4,
    ROUTE_CENTER_HEURISTIC_INTERMEDIATE,
    ROUTE_CENTER_OPTIMAL_REFERENCE,
    ROUTE_CENTER_SVQ1_EXPANDED,
    get_routable_center_candidates,
    resolve_guided_route_dataset,
)
from src.project_sections import (  # noqa: E402
    _compute_guided_route_records,
    _guided_calculated_route_map_options,
)


DATA_DIR = ROOT / "data"


def _small_dataset() -> Dataset:
    matrix = np.array(
        [
            [0.0, 4.0, 5.0, 6.0, 10.0],
            [4.0, 0.0, 3.0, 4.0, 8.0],
            [5.0, 3.0, 0.0, 2.0, 6.0],
            [6.0, 4.0, 2.0, 0.0, 7.0],
            [10.0, 8.0, 6.0, 7.0, 0.0],
        ]
    )
    return Dataset(
        names=[
            DEPOT_NAME,
            SECONDARY_HUB_NAME,
            "Centro óptimo / referencia",
            "Intermedio heurístico",
            "Nodo A",
        ],
        latitudes=np.array([0.0, 1.0, 0.5, 0.75, 2.0]),
        longitudes=np.array([0.0, 1.0, 0.5, 0.75, 2.0]),
        restringe_camion=np.array([0, 0, 0, 0, 0]),
        poblacion=np.array([0, 0, 0, 0, 100]),
        distance_matrix=matrix,
        time_matrix=matrix * 2,
        depot_index=0,
    )


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)
    print(f"  OK {message}")


def test_od_v2_loads_with_candidate_centers() -> None:
    print("test_od_v2_loads_with_candidate_centers")
    dataset = load_dataset(
        poblacion_path=DATA_DIR / "poblacion.csv",
        rutas_path=DATA_DIR / "rutasDistTiempo_v2.csv",
    )
    _assert(dataset.n_nodes == 124, "carga 124 nodos con centros candidatos")
    _assert(dataset.distance_matrix.shape == (124, 124), "matriz distancia v2 completa")
    _assert(dataset.time_matrix.shape == (124, 124), "matriz tiempo v2 completa")
    _assert(dataset.names[0] == DEPOT_NAME, "indice 0 es SVQ1 en los datos cargados")
    _assert(dataset.names[1] == SECONDARY_HUB_NAME, "indice 1 es DQA4 en los datos cargados")
    _assert(dataset.poblacion[2] == 0 and dataset.poblacion[3] == 0, "centros 2 y 3 sin demanda")


def test_routable_centers_resolve_expected_depots() -> None:
    print("test_routable_centers_resolve_expected_depots")
    dataset = _small_dataset()
    candidates = get_routable_center_candidates(dataset)
    expected = {
        ROUTE_CENTER_CURRENT_DQA4,
        ROUTE_CENTER_SVQ1_EXPANDED,
        ROUTE_CENTER_OPTIMAL_REFERENCE,
        ROUTE_CENTER_HEURISTIC_INTERMEDIATE,
    }
    _assert(set(candidates) == expected, "expone los cuatro centros enrutables")
    _assert(resolve_guided_route_dataset(dataset, ROUTE_CENTER_CURRENT_DQA4).depot_index == 1, "DQA4 usa depot 1")
    _assert(resolve_guided_route_dataset(dataset, ROUTE_CENTER_SVQ1_EXPANDED).depot_index == 0, "SVQ1 usa depot 0")
    _assert(resolve_guided_route_dataset(dataset, ROUTE_CENTER_OPTIMAL_REFERENCE).depot_index == 2, "optimo usa depot 2")
    _assert(resolve_guided_route_dataset(dataset, ROUTE_CENTER_HEURISTIC_INTERMEDIATE).depot_index == 3, "intermedio usa depot 3")


def test_guided_route_records_can_cover_multiple_centers() -> None:
    print("test_guided_route_records_can_cover_multiple_centers")
    import src.project_sections as sections

    dataset = _small_dataset()
    calls: list[int] = []

    def fake_run_pipeline(dataset_for_run, pipeline_config):
        calls.append(dataset_for_run.depot_index)
        return object()

    original = sections.run_pipeline
    sections.run_pipeline = fake_run_pipeline
    try:
        records = _compute_guided_route_records(
            dataset,
            pipeline_config=object(),
            center_options=(
                ROUTE_CENTER_CURRENT_DQA4,
                ROUTE_CENTER_SVQ1_EXPANDED,
                ROUTE_CENTER_OPTIMAL_REFERENCE,
            ),
        )
    finally:
        sections.run_pipeline = original

    _assert(calls == [1, 0, 2], "calcula rutas con los depots seleccionados")
    _assert(set(records) == {ROUTE_CENTER_CURRENT_DQA4, ROUTE_CENTER_SVQ1_EXPANDED, ROUTE_CENTER_OPTIMAL_REFERENCE}, "registros por centro")
    _assert(all(record["pipeline_result"] is not None for record in records.values()), "guarda resultados calculados")


def test_route_map_options_only_include_calculated_routes() -> None:
    print("test_route_map_options_only_include_calculated_routes")
    center_options = (ROUTE_CENTER_CURRENT_DQA4, ROUTE_CENTER_SVQ1_EXPANDED)
    _assert(_guided_calculated_route_map_options({}, center_options) == [], "sin rutas no hay mapas")
    options = _guided_calculated_route_map_options(
        {ROUTE_CENTER_CURRENT_DQA4: {"pipeline_result": object()}},
        center_options,
    )
    _assert(options == [ROUTE_CENTER_CURRENT_DQA4], "solo muestra rutas calculadas")


def main() -> None:
    test_od_v2_loads_with_candidate_centers()
    test_routable_centers_resolve_expected_depots()
    test_guided_route_records_can_cover_multiple_centers()
    test_route_map_options_only_include_calculated_routes()
    print("\nTodos los tests de centros de rutas guiadas OK")


if __name__ == "__main__":
    main()
