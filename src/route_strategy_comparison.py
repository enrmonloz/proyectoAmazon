"""Comparacion de estrategias de asignacion de rutas.

Este modulo no cambia el solver: ejecuta el pipeline con las estrategias
existentes y resume sus metricas operativas principales.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Iterable

from .pipeline import PipelineConfig, run_pipeline
from .vrp_solver import SolverStrategy


DEFAULT_ROUTE_STRATEGIES: tuple[SolverStrategy, ...] = (
    SolverStrategy.INSERTION,
    SolverStrategy.SAVINGS,
    SolverStrategy.NEAREST_NEIGHBOR,
    SolverStrategy.SWEEP,
    SolverStrategy.CHRISTOFIDES,
)

ROUTE_STRATEGY_LABELS: dict[SolverStrategy, str] = {
    SolverStrategy.INSERTION: "Insercion paralela",
    SolverStrategy.SAVINGS: "Clarke-Wright (Savings)",
    SolverStrategy.NEAREST_NEIGHBOR: "Vecino mas cercano",
    SolverStrategy.SWEEP: "Algoritmo de barrido",
    SolverStrategy.CHRISTOFIDES: "Christofides",
}


def route_strategy_label(strategy: SolverStrategy) -> str:
    return ROUTE_STRATEGY_LABELS.get(strategy, strategy.value)


def compare_route_assignment_strategies(
    dataset,
    base_config: PipelineConfig,
    strategies: Iterable[SolverStrategy] = DEFAULT_ROUTE_STRATEGIES,
) -> list[dict[str, object]]:
    """Ejecuta las estrategias indicadas y devuelve una tabla resumida."""
    rows: list[dict[str, object]] = []
    for strategy in strategies:
        config = replace(base_config, solver_strategy=strategy)
        try:
            result = run_pipeline(dataset, config)
        except Exception as exc:  # pragma: no cover - defensivo para UI
            rows.append(
                {
                    "Tecnica": route_strategy_label(strategy),
                    "Estrategia": strategy.value,
                    "Estado": f"Error: {exc}",
                    "Rutas VRP": None,
                    "Rutas dedicadas": None,
                    "Rutas totales": None,
                    "Distancia total (km)": None,
                    "Tiempo total (min)": None,
                    "Diesel VRP": None,
                    "Electricas VRP": None,
                    "Trailers": None,
                    "Nodos no servidos": None,
                }
            )
            continue

        rows.append(
            {
                "Tecnica": route_strategy_label(strategy),
                "Estrategia": strategy.value,
                "Estado": "OK",
                "Rutas VRP": int(result.vrp_route_count),
                "Rutas dedicadas": int(result.dedicated_route_count),
                "Rutas totales": int(result.total_routes),
                "Distancia total (km)": float(result.total_distance_km),
                "Tiempo total (min)": float(result.total_time_min),
                "Diesel VRP": int(result.vrp.diesel_count),
                "Electricas VRP": int(result.vrp.electric_count),
                "Trailers": int(result.trailer_route_count),
                "Nodos no servidos": int(len(result.vrp.unassigned_nodes)),
            }
        )
    return rows
