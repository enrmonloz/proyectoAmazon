"""Costes operativos medios de rutas para el flujo guiado."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


OFFICIAL_COST_SOURCE_2026 = (
    "Observatorio de Costes del Transporte de Mercancías por Carretera, enero 2026"
)


@dataclass(frozen=True)
class RouteCostRate:
    variable_cost_per_km: float
    time_cost_per_hour: float
    working_days_per_year: int
    source: str


@dataclass(frozen=True)
class RouteCostBreakdown:
    alternative: str
    center_name: str
    route: str
    route_type: str
    vehicle_type: str
    distance_km: float
    time_hours: float
    distance_cost: float
    time_cost: float
    total_cost: float


@dataclass(frozen=True)
class PipelineRouteCostSummary:
    scenario_name: str
    center_name: str
    van_daily_cost: float
    trailer_daily_cost: float
    total_daily_cost: float
    total_annual_cost: float
    annual_packages: float
    cost_per_package: float
    working_days_per_year: int
    breakdown: tuple[RouteCostBreakdown, ...]


FURGONETA_RATE_2026 = RouteCostRate(
    variable_cost_per_km=0.3035,
    time_cost_per_hour=25.47,
    working_days_per_year=225,
    source=OFFICIAL_COST_SOURCE_2026,
)

TRAILER_RATE_2026 = RouteCostRate(
    variable_cost_per_km=0.6670,
    time_cost_per_hour=43.80,
    working_days_per_year=225,
    source=OFFICIAL_COST_SOURCE_2026,
)


def compute_route_cost(distance_km: float, time_min: float, rate: RouteCostRate) -> float:
    """Calcula coste de ruta sin duplicar kilometraje y tiempo."""
    if distance_km < 0:
        raise ValueError("La distancia de ruta no puede ser negativa")
    if time_min < 0:
        raise ValueError("El tiempo de ruta no puede ser negativo")
    return float(distance_km) * rate.variable_cost_per_km + (
        float(time_min) / 60.0
    ) * rate.time_cost_per_hour


def compute_pipeline_route_costs(
    pipeline_result,
    scenario_name: str,
    center_name: str,
    working_days_per_year: int = 225,
) -> PipelineRouteCostSummary:
    """Resume costes diarios y anuales de las rutas de un PipelineResult."""
    if working_days_per_year <= 0:
        raise ValueError("Los dias laborables anuales deben ser positivos")

    breakdown: list[RouteCostBreakdown] = []
    van_daily_cost = 0.0
    trailer_daily_cost = 0.0

    for idx, route in enumerate(pipeline_result.vrp.routes, start=1):
        item = _route_breakdown(
            scenario_name=scenario_name,
            center_name=center_name,
            route_label=f"VRP {idx}",
            route_type="VRP",
            vehicle_type="furgoneta",
            distance_km=route.travel_distance_km,
            time_min=route.total_time_min,
            rate=FURGONETA_RATE_2026,
        )
        breakdown.append(item)
        van_daily_cost += item.total_cost

    for idx, route in enumerate(pipeline_result.split.dedicated_routes, start=1):
        is_trailer = route.vehicle_type == "trailer"
        rate = TRAILER_RATE_2026 if is_trailer else FURGONETA_RATE_2026
        item = _route_breakdown(
            scenario_name=scenario_name,
            center_name=center_name,
            route_label=f"Dedicada {idx}",
            route_type="Dedicada",
            vehicle_type="trailer" if is_trailer else "furgoneta",
            distance_km=route.travel_distance_km,
            time_min=route.total_time_min,
            rate=rate,
        )
        breakdown.append(item)
        if is_trailer:
            trailer_daily_cost += item.total_cost
        else:
            van_daily_cost += item.total_cost

    total_daily_cost = van_daily_cost + trailer_daily_cost
    total_annual_cost = total_daily_cost * float(working_days_per_year)
    annual_packages = _sum_packages(pipeline_result.packages) * float(working_days_per_year)
    cost_per_package = total_annual_cost / annual_packages if annual_packages > 0 else 0.0

    return PipelineRouteCostSummary(
        scenario_name=scenario_name,
        center_name=center_name,
        van_daily_cost=van_daily_cost,
        trailer_daily_cost=trailer_daily_cost,
        total_daily_cost=total_daily_cost,
        total_annual_cost=total_annual_cost,
        annual_packages=annual_packages,
        cost_per_package=cost_per_package,
        working_days_per_year=int(working_days_per_year),
        breakdown=tuple(breakdown),
    )


def _route_breakdown(
    *,
    scenario_name: str,
    center_name: str,
    route_label: str,
    route_type: str,
    vehicle_type: str,
    distance_km: float,
    time_min: float,
    rate: RouteCostRate,
) -> RouteCostBreakdown:
    distance = float(distance_km)
    time = float(time_min)
    distance_cost = distance * rate.variable_cost_per_km
    time_cost = (time / 60.0) * rate.time_cost_per_hour
    total_cost = compute_route_cost(distance, time, rate)
    return RouteCostBreakdown(
        alternative=scenario_name,
        center_name=center_name,
        route=route_label,
        route_type=route_type,
        vehicle_type=vehicle_type,
        distance_km=distance,
        time_hours=time / 60.0,
        distance_cost=distance_cost,
        time_cost=time_cost,
        total_cost=total_cost,
    )


def _sum_packages(packages: Iterable[float]) -> float:
    return float(sum(float(value) for value in packages))
