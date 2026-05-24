#!/usr/bin/env python3
"""Export final reproducible assets for the technical memory.

The script is intentionally an orchestration layer: it reuses the existing
demand, routing, route-cost, location and guided-economics modules without
changing their formulas or solver behavior.
"""

from __future__ import annotations

import argparse
import json
import math
import shlex
import sys
from datetime import datetime
from html import escape
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.data_loader import load_dataset  # noqa: E402
from src.demand import DemandConfig, compute_node_service_time, compute_packages  # noqa: E402
from src.fleet import FleetConfig  # noqa: E402
from src.guided_economics import (  # noqa: E402
    CURRENT_TOTAL_ANNUAL_COST,
    GUIDED_DISCOUNT_RATE,
    GUIDED_HORIZON_YEARS,
    GuidedEconomicInputs,
    compute_investment_comparison,
)
from src.guided_flow import (  # noqa: E402
    ROUTE_CENTER_CURRENT_DQA4,
    ROUTE_CENTER_SVQ1_EXPANDED,
    guided_center_label,
    resolve_guided_route_dataset,
)
from src.location_solver import build_full_location_comparison  # noqa: E402
from src.pipeline import PipelineConfig, PipelineResult, run_pipeline  # noqa: E402
from src.route_costs import PipelineRouteCostSummary, compute_pipeline_route_costs  # noqa: E402
from src.service_area import (  # noqa: E402
    DEFAULT_ACTIVE_PROVINCE_NODES,
    apply_province_node_filter,
    validate_od_alignment_for_known_nodes,
)
from src.trailer import TrailerConfig  # noqa: E402
from src.vrp_solver import SolverStrategy  # noqa: E402


DEFAULT_OUTPUT_DIR = ROOT / "memoria_final" / "assets"
TABLE_DIRNAME = "tables"
FIGURE_DIRNAME = "figures"
TARGET_DAILY_VOLUME = 38_900.0
WORKING_DAYS_PER_YEAR = 225
SVG_CAPTION = "Elaboración propia a partir del modelo computacional."


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = ROOT / output_dir
    tables_dir = output_dir / TABLE_DIRNAME
    figures_dir = output_dir / FIGURE_DIRNAME
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    warnings: list[str] = []
    generated_files: list[Path] = []
    generated_tables: list[Path] = []
    generated_figures: list[dict[str, str]] = []
    pending_figures: list[dict[str, str]] = []

    run_timestamp = datetime.now().astimezone().isoformat(timespec="seconds")
    command_used = _command_used()

    raw_dataset = load_dataset()
    dataset = apply_province_node_filter(raw_dataset, DEFAULT_ACTIVE_PROVINCE_NODES)
    warnings.extend(
        validate_od_alignment_for_known_nodes(dataset, DEFAULT_ACTIVE_PROVINCE_NODES)
    )

    active_population = _active_population(dataset)
    market_penetration = _calibrated_market_penetration(
        active_population=active_population,
        target_daily_volume=float(args.target_daily_volume),
        seasonality_multiplier=float(args.seasonality_multiplier),
    )

    pipeline_config = _reference_pipeline_config(
        market_penetration=market_penetration,
        seasonality_multiplier=float(args.seasonality_multiplier),
        solver_time_limit_seconds=int(args.solver_time_limit),
    )
    demand_config = pipeline_config.to_demand_config()
    packages = compute_packages(dataset.poblacion, demand_config, dataset.depot_index)
    service_time = compute_node_service_time(packages, demand_config)
    obtained_daily_volume = int(packages.sum())

    if abs(float(args.target_daily_volume) - TARGET_DAILY_VOLUME) > 1e-9:
        warnings.append(
            f"El objetivo diario configurado no es 38.900: {args.target_daily_volume:.0f}."
        )
    if not (0.0153 <= market_penetration <= 0.0157):
        warnings.append(
            "La penetración calculada queda fuera del intervalo esperado "
            f"para x1,00: {market_penetration * 100:.4f}%."
        )
    if abs(obtained_daily_volume - int(args.target_daily_volume)) > 5:
        warnings.append(
            "La demanda redondeada se aleja del objetivo en más de 5 paquetes: "
            f"{obtained_daily_volume} frente a {int(args.target_daily_volume)}."
        )

    route_records = _run_reference_routes(dataset, pipeline_config, warnings)
    cost_summaries = _compute_route_cost_summaries(route_records, warnings)
    route_differential = _route_differential(route_records, cost_summaries)
    economics = _compute_reference_economics(cost_summaries, warnings)
    if economics is not None and route_differential:
        diff_for_economics = economics.route_overcost_annual
        diff_from_routes = float(route_differential["annual_route_cost_eur_delta"])
        if abs(diff_for_economics - diff_from_routes) > 1e-6:
            warnings.append(
                "El diferencial de rutas usado en economía no coincide con la "
                f"comparación DQA4 vs SVQ1 ({diff_for_economics:.2f} vs {diff_from_routes:.2f})."
            )

    location_frame = build_full_location_comparison(dataset)

    tables = _build_tables(
        dataset=dataset,
        packages=packages,
        service_time=service_time,
        active_population=active_population,
        market_penetration=market_penetration,
        pipeline_config=pipeline_config,
        route_records=route_records,
        cost_summaries=cost_summaries,
        route_differential=route_differential,
        economics=economics,
        location_frame=location_frame,
        warnings=warnings,
    )
    for table_name, frame in tables.items():
        paths = _write_table_pair(tables_dir, table_name, frame)
        generated_tables.extend(paths)
        generated_files.extend(paths)

    figure_specs = [
        (
            "mapa_demanda.svg",
            "Mapa de demanda",
            "Distribución territorial de los paquetes diarios calculados.",
            lambda path: _write_demand_map(path, dataset, packages),
        ),
        (
            "mapa_comparativa_localizacion.svg",
            "Mapa comparativo de localización",
            "Comparación geográfica de referencias y candidatos de localización.",
            lambda path: _write_location_map(path, dataset, location_frame),
        ),
        (
            "mapa_rutas_dqa4.svg",
            "Mapa de rutas DQA4",
            "Rutas calculadas tomando DQA4 como centro de salida.",
            lambda path: _write_route_map(
                path, route_records[ROUTE_CENTER_CURRENT_DQA4]["pipeline_result"]
            ),
        ),
        (
            "mapa_rutas_svq1.svg",
            "Mapa de rutas SVQ1",
            "Rutas calculadas tomando SVQ1 como centro de salida.",
            lambda path: _write_route_map(
                path, route_records[ROUTE_CENTER_SVQ1_EXPANDED]["pipeline_result"]
            ),
        ),
        (
            "grafico_comparativo_rutas.svg",
            "Gráfico comparativo de rutas",
            "Comparación de rutas, kilómetros, tiempo y coste anual.",
            lambda path: _write_route_comparison_chart(path, route_records, cost_summaries),
        ),
        (
            "grafico_economico_van_tir_payback.svg",
            "Gráfico económico VAN/TIR/payback",
            "Comparación económica de Básica, Estándar y Premium.",
            lambda path: _write_economic_chart(path, economics),
        ),
        (
            "curva_flujos_acumulados_pert.svg",
            "Curva de flujos acumulados PERT",
            "Evolución acumulada de los flujos PERT por opción.",
            lambda path: _write_pert_cashflow_chart(path, economics),
        ),
        (
            "matriz_riesgos_residuales.svg",
            "Matriz de riesgos residuales",
            "Probabilidad residual e impacto de riesgos del caso de referencia.",
            lambda path: _write_risk_matrix(path, economics),
        ),
    ]

    for filename, title, description, writer in figure_specs:
        output_path = figures_dir / filename
        try:
            writer(output_path)
            generated_figures.append(
                {
                    "file": _relative(output_path),
                    "title": title,
                    "description": description,
                    "suggested_caption": SVG_CAPTION,
                }
            )
            generated_files.append(output_path)
        except Exception as exc:  # pragma: no cover - exercised by real export failures
            message = str(exc)
            warnings.append(f"No se pudo generar {filename}: {message}")
            pending_figures.append(
                {
                    "name": title,
                    "file": filename,
                    "should_show": description,
                    "depends_on": _figure_dependency_hint(filename),
                    "manual_method": _manual_figure_hint(filename),
                    "error": message,
                }
            )

    snapshot = _build_snapshot(
        run_timestamp=run_timestamp,
        command_used=command_used,
        active_population=active_population,
        market_penetration=market_penetration,
        target_daily_volume=float(args.target_daily_volume),
        obtained_daily_volume=obtained_daily_volume,
        dataset=dataset,
        packages=packages,
        service_time=service_time,
        pipeline_config=pipeline_config,
        location_frame=location_frame,
        route_records=route_records,
        cost_summaries=cost_summaries,
        route_differential=route_differential,
        economics=economics,
        warnings=warnings,
    )
    snapshot_path = output_dir / "results_snapshot_38900.json"
    snapshot_path.write_text(
        json.dumps(_jsonable(snapshot), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    generated_files.append(snapshot_path)

    manifest_path = output_dir / "assets_manifest.md"
    manifest_files = [*generated_files, manifest_path]
    assets_ready = _assets_ready(warnings, pending_figures, route_records, economics)
    manifest_path.write_text(
        _build_manifest(
            run_timestamp=run_timestamp,
            command_used=command_used,
            pipeline_config=pipeline_config,
            active_population=active_population,
            market_penetration=market_penetration,
            target_daily_volume=float(args.target_daily_volume),
            obtained_daily_volume=obtained_daily_volume,
            generated_files=manifest_files,
            generated_tables=generated_tables,
            generated_figures=generated_figures,
            pending_figures=pending_figures,
            warnings=warnings,
            assets_ready=assets_ready,
        ),
        encoding="utf-8",
    )

    print(f"Assets exportados en: {_relative(output_dir)}")
    print(f"Snapshot: {_relative(snapshot_path)}")
    print(f"Manifest: {_relative(manifest_path)}")
    print(f"Objetivo diario: {int(args.target_daily_volume)} paquetes")
    print(f"Paquetes tras redondeo: {obtained_daily_volume}")
    print(f"Penetración calculada: {market_penetration * 100:.6f}%")
    print(f"Apto para memoria final: {'sí' if assets_ready else 'no'}")
    if warnings:
        print("Advertencias:")
        for warning in warnings:
            print(f"- {warning}")
    return 0


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Exporta tablas, figuras y snapshot para la memoria final."
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR.relative_to(ROOT)),
        help="Carpeta destino de assets.",
    )
    parser.add_argument(
        "--target-daily-volume",
        type=float,
        default=TARGET_DAILY_VOLUME,
        help="Volumen diario objetivo usado para calibrar penetración.",
    )
    parser.add_argument(
        "--seasonality-multiplier",
        type=float,
        default=1.0,
        help="Multiplicador de estacionalidad aplicado al escenario.",
    )
    parser.add_argument(
        "--solver-time-limit",
        type=int,
        default=30,
        help="Límite de tiempo por corrida VRP en segundos.",
    )
    return parser.parse_args(argv)


def _command_used() -> str:
    return " ".join(shlex.quote(part) for part in [sys.executable, *sys.argv])


def _active_population(dataset) -> float:
    population = np.asarray(dataset.poblacion, dtype=float).copy()
    population[int(dataset.depot_index)] = 0.0
    return float(population.sum())


def _calibrated_market_penetration(
    *,
    active_population: float,
    target_daily_volume: float,
    seasonality_multiplier: float,
) -> float:
    if active_population <= 0:
        raise ValueError("No se puede calibrar demanda sin población activa positiva.")
    if target_daily_volume <= 0:
        raise ValueError("El objetivo diario debe ser positivo.")
    if seasonality_multiplier <= 0:
        raise ValueError("La estacionalidad debe ser positiva.")
    return float(target_daily_volume) / (float(active_population) * float(seasonality_multiplier))


def _reference_pipeline_config(
    *,
    market_penetration: float,
    seasonality_multiplier: float,
    solver_time_limit_seconds: int,
) -> PipelineConfig:
    return PipelineConfig(
        market_penetration=float(market_penetration),
        max_workday_hours=7.5,
        service_time_per_package_min=1.5,
        inter_package_time_min=1.0,
        seasonality_multiplier=float(seasonality_multiplier),
        target_daily_volume=None,
        fleet=FleetConfig(
            max_diesel=75,
            max_electric=45,
            electric_max_range_km=350.0,
        ),
        trailer=TrailerConfig(
            enabled=True,
            packages_capacity=4_000,
            unloading_time_min=90.0,
        ),
        solver_strategy=SolverStrategy.INSERTION,
        solver_time_limit_seconds=int(solver_time_limit_seconds),
    )


def _run_reference_routes(
    dataset,
    pipeline_config: PipelineConfig,
    warnings: list[str],
) -> dict[str, dict[str, object]]:
    route_records: dict[str, dict[str, object]] = {}
    for route_key in (ROUTE_CENTER_CURRENT_DQA4, ROUTE_CENTER_SVQ1_EXPANDED):
        try:
            route_dataset = resolve_guided_route_dataset(dataset, route_key)
            result = run_pipeline(route_dataset, pipeline_config)
            route_records[route_key] = {
                "label": guided_center_label(route_key),
                "pipeline_result": result,
                "error": None,
            }
            if result.vrp.unassigned_nodes:
                names = ", ".join(result.dataset.names[i] for i in result.vrp.unassigned_nodes)
                warnings.append(
                    f"{guided_center_label(route_key)} deja nodos sin asignar: {names}."
                )
        except Exception as exc:
            route_records[route_key] = {
                "label": guided_center_label(route_key),
                "pipeline_result": None,
                "error": str(exc),
            }
            warnings.append(f"No se pudieron calcular rutas para {guided_center_label(route_key)}: {exc}")
    return route_records


def _compute_route_cost_summaries(
    route_records: dict[str, dict[str, object]],
    warnings: list[str],
) -> dict[str, PipelineRouteCostSummary]:
    summaries: dict[str, PipelineRouteCostSummary] = {}
    for route_key, record in route_records.items():
        result = record.get("pipeline_result")
        if result is None:
            continue
        try:
            summaries[route_key] = compute_pipeline_route_costs(
                result,
                scenario_name=guided_center_label(route_key),
                center_name=result.dataset.names[result.dataset.depot_index],
                working_days_per_year=WORKING_DAYS_PER_YEAR,
            )
        except Exception as exc:
            warnings.append(
                f"No se pudieron calcular costes de rutas para {guided_center_label(route_key)}: {exc}"
            )
    return summaries


def _route_differential(
    route_records: dict[str, dict[str, object]],
    cost_summaries: dict[str, PipelineRouteCostSummary],
) -> dict[str, float] | None:
    dqa4 = route_records.get(ROUTE_CENTER_CURRENT_DQA4, {}).get("pipeline_result")
    svq1 = route_records.get(ROUTE_CENTER_SVQ1_EXPANDED, {}).get("pipeline_result")
    dqa4_cost = cost_summaries.get(ROUTE_CENTER_CURRENT_DQA4)
    svq1_cost = cost_summaries.get(ROUTE_CENTER_SVQ1_EXPANDED)
    if dqa4 is None or svq1 is None or dqa4_cost is None or svq1_cost is None:
        return None
    return {
        "routes_total_delta": float(svq1.total_routes - dqa4.total_routes),
        "vrp_routes_delta": float(svq1.vrp_route_count - dqa4.vrp_route_count),
        "dedicated_routes_delta": float(svq1.dedicated_route_count - dqa4.dedicated_route_count),
        "trailer_routes_delta": float(svq1.trailer_route_count - dqa4.trailer_route_count),
        "distance_km_day_delta": float(svq1.total_distance_km - dqa4.total_distance_km),
        "time_min_day_delta": float(svq1.total_time_min - dqa4.total_time_min),
        "annual_route_cost_eur_delta": float(
            svq1_cost.total_annual_cost - dqa4_cost.total_annual_cost
        ),
        "daily_route_cost_eur_delta": float(
            svq1_cost.total_daily_cost - dqa4_cost.total_daily_cost
        ),
        "cost_per_package_eur_delta": float(
            svq1_cost.cost_per_package - dqa4_cost.cost_per_package
        ),
    }


def _compute_reference_economics(
    cost_summaries: dict[str, PipelineRouteCostSummary],
    warnings: list[str],
):
    dqa4_cost = cost_summaries.get(ROUTE_CENTER_CURRENT_DQA4)
    svq1_cost = cost_summaries.get(ROUTE_CENTER_SVQ1_EXPANDED)
    if dqa4_cost is None or svq1_cost is None:
        warnings.append("La economía no se pudo recalcular porque faltan costes de rutas.")
        return None
    return compute_investment_comparison(
        GuidedEconomicInputs(
            alternative=guided_center_label(ROUTE_CENTER_SVQ1_EXPANDED),
            transport_support="Subsidio transporte público",
            route_cost_annual=svq1_cost.total_annual_cost,
            route_cost_reference_annual=dqa4_cost.total_annual_cost,
            include_training=True,
            include_dqa4_value_loss=True,
            include_phasing=True,
            include_backup=True,
            include_insurance=False,
            include_incentives=False,
            horizon_years=GUIDED_HORIZON_YEARS,
            discount_rate=GUIDED_DISCOUNT_RATE,
        )
    )


def _build_tables(
    *,
    dataset,
    packages: np.ndarray,
    service_time: np.ndarray,
    active_population: float,
    market_penetration: float,
    pipeline_config: PipelineConfig,
    route_records: dict[str, dict[str, object]],
    cost_summaries: dict[str, PipelineRouteCostSummary],
    route_differential: dict[str, float] | None,
    economics,
    location_frame: pd.DataFrame,
    warnings: list[str],
) -> dict[str, pd.DataFrame]:
    tables: dict[str, pd.DataFrame] = {}
    target = TARGET_DAILY_VOLUME
    tables["supuestos_referencia"] = pd.DataFrame(
        [
            ("Demanda", "Provincias agregadas activas", ", ".join(DEFAULT_ACTIVE_PROVINCE_NODES), ""),
            ("Demanda", "Población activa", active_population, "habitantes"),
            ("Demanda", "Paquetes/día objetivo", target, "paquetes/día"),
            ("Demanda", "Paquetes/día tras redondeo", int(packages.sum()), "paquetes/día"),
            ("Demanda", "Penetración calculada", market_penetration * 100.0, "%"),
            ("Demanda", "Estacionalidad", pipeline_config.seasonality_multiplier, "multiplicador"),
            ("Servicio", "Servicio por paquete", pipeline_config.service_time_per_package_min, "min/paquete"),
            ("Servicio", "Tiempo técnico entre paquetes", pipeline_config.inter_package_time_min, "min/paquete"),
            ("Rutas", "Jornada efectiva", pipeline_config.max_workday_hours, "h"),
            ("Rutas", "Furgonetas diésel máximas", pipeline_config.fleet.max_diesel, "vehículos"),
            ("Rutas", "Furgonetas eléctricas máximas", pipeline_config.fleet.max_electric, "vehículos"),
            ("Rutas", "Autonomía eléctrica", pipeline_config.fleet.electric_max_range_km, "km/jornada"),
            ("Rutas", "Trailers para nodos grandes", "Activados", ""),
            ("Rutas", "Capacidad trailer", pipeline_config.trailer.packages_capacity, "paquetes/viaje"),
            ("Rutas", "Descarga trailer", pipeline_config.trailer.unloading_time_min, "min"),
            ("Rutas", "Método de rutas", "Inserción paralela", ""),
            ("Economía", "Horizonte económico", GUIDED_HORIZON_YEARS, "años"),
            ("Economía", "Tasa de descuento", GUIDED_DISCOUNT_RATE * 100.0, "%"),
            ("Economía", "Apoyo laboral", "Subsidio transporte público", ""),
            ("Economía", "Mitigaciones activas", "Formación; pérdida valor DQA4; implantación por fases; sistemas de respaldo", ""),
        ],
        columns=["Bloque", "Parámetro", "Valor", "Unidad/nota"],
    )

    demand_rows = []
    total_packages = float(packages.sum())
    for index, amount in sorted(
        [(idx, int(value)) for idx, value in enumerate(packages) if int(value) > 0],
        key=lambda item: item[1],
        reverse=True,
    ):
        demand_rows.append(
            {
                "Nodo": dataset.names[index],
                "Población activa usada": int(dataset.poblacion[index]),
                "Paquetes/día": amount,
                "Peso paquetes (%)": amount / total_packages * 100.0 if total_packages else 0.0,
                "Tiempo servicio diario (min)": float(service_time[index]),
            }
        )
    tables["demanda_principales_nodos"] = pd.DataFrame(demand_rows)

    tables["comparacion_localizacion"] = location_frame.copy()
    tables["comparacion_rutas_dqa4_vs_svq1"] = _route_comparison_frame(
        route_records, cost_summaries, route_differential
    )
    tables["costes_rutas"] = _route_cost_frame(cost_summaries, route_differential)
    if economics is not None:
        tables["comparacion_economica_basica_estandar_premium"] = _economics_frame(economics)
        tables["riesgos_residuales"] = _risk_frame(economics)
        tables["flujos_pert_svq1"] = _cashflow_frame(economics)
    else:
        tables["comparacion_economica_basica_estandar_premium"] = pd.DataFrame()
        tables["riesgos_residuales"] = pd.DataFrame()
        tables["flujos_pert_svq1"] = pd.DataFrame()

    pending_rows = (
        [{"Pendiente": warning, "Motivo": "Advertencia de exportación"} for warning in warnings]
        if warnings
        else [{"Pendiente": "Sin pendientes de recálculo", "Motivo": "Todos los bloques principales se calcularon"}]
    )
    tables["pendientes_recalculo"] = pd.DataFrame(pending_rows)
    return tables


def _route_comparison_frame(
    route_records: dict[str, dict[str, object]],
    cost_summaries: dict[str, PipelineRouteCostSummary],
    route_differential: dict[str, float] | None,
) -> pd.DataFrame:
    rows = []
    for route_key in (ROUTE_CENTER_CURRENT_DQA4, ROUTE_CENTER_SVQ1_EXPANDED):
        result = route_records.get(route_key, {}).get("pipeline_result")
        cost = cost_summaries.get(route_key)
        if result is None:
            continue
        rows.append(
            {
                "Alternativa": guided_center_label(route_key),
                "Centro salida": result.dataset.names[result.dataset.depot_index],
                "Paquetes/día": int(result.packages.sum()),
                "Rutas totales": result.total_routes,
                "Rutas VRP": result.vrp_route_count,
                "Rutas dedicadas": result.dedicated_route_count,
                "Rutas trailer": result.trailer_route_count,
                "Furgonetas diésel VRP": result.vrp.diesel_count,
                "Furgonetas eléctricas VRP": result.vrp.electric_count,
                "Distancia diaria (km)": result.total_distance_km,
                "Tiempo diario (min)": result.total_time_min,
                "Coste anual rutas (€)": cost.total_annual_cost if cost else None,
                "Nodos no asignados": len(result.vrp.unassigned_nodes),
            }
        )
    if route_differential:
        rows.append(
            {
                "Alternativa": "Diferencial SVQ1 - DQA4",
                "Centro salida": "",
                "Paquetes/día": 0,
                "Rutas totales": route_differential["routes_total_delta"],
                "Rutas VRP": route_differential["vrp_routes_delta"],
                "Rutas dedicadas": route_differential["dedicated_routes_delta"],
                "Rutas trailer": route_differential["trailer_routes_delta"],
                "Furgonetas diésel VRP": None,
                "Furgonetas eléctricas VRP": None,
                "Distancia diaria (km)": route_differential["distance_km_day_delta"],
                "Tiempo diario (min)": route_differential["time_min_day_delta"],
                "Coste anual rutas (€)": route_differential["annual_route_cost_eur_delta"],
                "Nodos no asignados": None,
            }
        )
    return pd.DataFrame(rows)


def _route_cost_frame(
    cost_summaries: dict[str, PipelineRouteCostSummary],
    route_differential: dict[str, float] | None,
) -> pd.DataFrame:
    rows = []
    for route_key in (ROUTE_CENTER_CURRENT_DQA4, ROUTE_CENTER_SVQ1_EXPANDED):
        cost = cost_summaries.get(route_key)
        if cost is None:
            continue
        rows.append(
            {
                "Alternativa": guided_center_label(route_key),
                "Centro salida": cost.center_name,
                "Coste diario furgonetas (€)": cost.van_daily_cost,
                "Coste diario trailers (€)": cost.trailer_daily_cost,
                "Coste diario total (€)": cost.total_daily_cost,
                "Coste anual total (€)": cost.total_annual_cost,
                "Paquetes/año": cost.annual_packages,
                "Coste por paquete (€)": cost.cost_per_package,
                "Días laborables/año": cost.working_days_per_year,
            }
        )
    if route_differential:
        rows.append(
            {
                "Alternativa": "Diferencial SVQ1 - DQA4",
                "Centro salida": "",
                "Coste diario furgonetas (€)": None,
                "Coste diario trailers (€)": None,
                "Coste diario total (€)": route_differential["daily_route_cost_eur_delta"],
                "Coste anual total (€)": route_differential["annual_route_cost_eur_delta"],
                "Paquetes/año": None,
                "Coste por paquete (€)": route_differential["cost_per_package_eur_delta"],
                "Días laborables/año": WORKING_DAYS_PER_YEAR,
            }
        )
    return pd.DataFrame(rows)


def _economics_frame(economics) -> pd.DataFrame:
    rows = []
    for analysis in economics.analyses:
        rows.append(
            {
                "Opción": analysis.investment_option_name,
                "Ahorro base anual (€)": analysis.investment_profile.annual_saving_base,
                "Diferencial rutas vs DQA4 (€)": analysis.route_overcost_annual,
                "Coste inicial total (€)": analysis.initial_cost_total,
                "Coste anual estimado PERT (€)": analysis.estimated_absolute_annual_cost_pert,
                "VAN PERT (€)": analysis.van_pert,
                "TIR PERT": analysis.tir_pert,
                "Payback PERT (años)": analysis.payback_pert,
                "VAN pesimista (€)": analysis.van_pessimistic,
                "Sigma ahorro PERT (€)": analysis.sigma,
                "Puntuación decisión": economics.scores[analysis.investment_option_name],
            }
        )
    return pd.DataFrame(rows)


def _risk_frame(economics) -> pd.DataFrame:
    rows = []
    for analysis in economics.analyses:
        for risk in analysis.risk_lines:
            rows.append(
                {
                    "Opción": analysis.investment_option_name,
                    "Riesgo": risk.name,
                    "Tipo": risk.risk_kind,
                    "Probabilidad base": risk.probability,
                    "Probabilidad residual": risk.residual_probability,
                    "Impacto (€)": risk.impact,
                    "Coste esperado base (€)": risk.expected_cost,
                    "Coste esperado residual (€)": risk.residual_expected_cost,
                    "Mitigaciones": ", ".join(risk.mitigation_names) or "Sin mitigación",
                }
            )
    return pd.DataFrame(rows)


def _cashflow_frame(economics) -> pd.DataFrame:
    rows = []
    for analysis in economics.analyses:
        cumulative = 0.0
        for year, flow in enumerate(analysis.cash_flows_pert):
            cumulative += float(flow)
            rows.append(
                {
                    "Opción": analysis.investment_option_name,
                    "Año": year,
                    "Flujo PERT (€)": float(flow),
                    "Flujo acumulado PERT (€)": cumulative,
                }
            )
    return pd.DataFrame(rows)


def _write_table_pair(tables_dir: Path, table_name: str, frame: pd.DataFrame) -> list[Path]:
    csv_path = tables_dir / f"{table_name}.csv"
    md_path = tables_dir / f"{table_name}.md"
    export_frame = _rounded_frame(frame)
    export_frame.to_csv(csv_path, index=False, encoding="utf-8")
    md_path.write_text(_markdown_table(export_frame), encoding="utf-8")
    return [csv_path, md_path]


def _rounded_frame(frame: pd.DataFrame) -> pd.DataFrame:
    if frame is None or frame.empty:
        return pd.DataFrame(frame)
    rounded = frame.copy()
    for column in rounded.columns:
        if pd.api.types.is_float_dtype(rounded[column]):
            rounded[column] = rounded[column].map(
                lambda value: "" if pd.isna(value) else round(float(value), 6)
            )
    return rounded


def _markdown_table(frame: pd.DataFrame) -> str:
    if frame is None or frame.empty:
        return "_Tabla sin filas._\n"
    headers = [str(column) for column in frame.columns]
    rows = []
    for _, row in frame.iterrows():
        rows.append([_cell_to_markdown(row[column]) for column in frame.columns])
    lines = [
        "| " + " | ".join(_escape_md_cell(header) for header in headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(_escape_md_cell(value) for value in row) + " |")
    return "\n".join(lines) + "\n"


def _cell_to_markdown(value: object) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except TypeError:
        pass
    if isinstance(value, float):
        return _plain_number(value)
    return str(value)


def _plain_number(value: float) -> str:
    if not math.isfinite(float(value)):
        return ""
    absolute = abs(float(value))
    if absolute >= 100_000:
        text = f"{float(value):.2f}"
    elif absolute >= 100:
        text = f"{float(value):.3f}"
    else:
        text = f"{float(value):.6f}"
    return text.rstrip("0").rstrip(".")


def _escape_md_cell(value: str) -> str:
    return str(value).replace("|", "\\|").replace("\n", "<br>")


def _build_snapshot(
    *,
    run_timestamp: str,
    command_used: str,
    active_population: float,
    market_penetration: float,
    target_daily_volume: float,
    obtained_daily_volume: int,
    dataset,
    packages: np.ndarray,
    service_time: np.ndarray,
    pipeline_config: PipelineConfig,
    location_frame: pd.DataFrame,
    route_records: dict[str, dict[str, object]],
    cost_summaries: dict[str, PipelineRouteCostSummary],
    route_differential: dict[str, float] | None,
    economics,
    warnings: list[str],
) -> dict[str, object]:
    demand_rows = [
        {
            "node": dataset.names[index],
            "population": int(dataset.poblacion[index]),
            "packages_day": int(packages[index]),
            "service_time_min_day": float(service_time[index]),
        }
        for index in np.argsort(packages)[::-1]
        if int(packages[index]) > 0
    ]
    return {
        "execution_date": run_timestamp,
        "command": command_used,
        "parameters": _pipeline_parameters(pipeline_config),
        "active_aggregated_provinces": list(DEFAULT_ACTIVE_PROVINCE_NODES),
        "active_population": active_population,
        "calculated_market_penetration": market_penetration,
        "calculated_market_penetration_pct": market_penetration * 100.0,
        "target_packages_day": target_daily_volume,
        "obtained_packages_day_after_rounding": obtained_daily_volume,
        "demand_results": {
            "nodes_with_demand": len(demand_rows),
            "total_service_time_min_day": float(service_time.sum()),
            "main_nodes": demand_rows[:25],
        },
        "location_results": {
            "best_by_weighted_mean_distance": _frame_records(location_frame.head(1)),
            "comparison": _frame_records(location_frame),
        },
        "routes_dqa4": _pipeline_summary(
            route_records.get(ROUTE_CENTER_CURRENT_DQA4, {}).get("pipeline_result"),
            cost_summaries.get(ROUTE_CENTER_CURRENT_DQA4),
        ),
        "routes_svq1": _pipeline_summary(
            route_records.get(ROUTE_CENTER_SVQ1_EXPANDED, {}).get("pipeline_result"),
            cost_summaries.get(ROUTE_CENTER_SVQ1_EXPANDED),
        ),
        "svq1_vs_dqa4_differential": route_differential or {},
        "economics_basica_estandar_premium": _economics_records(economics),
        "residual_risks": _risk_records(economics),
        "warnings": list(warnings),
    }


def _pipeline_parameters(config: PipelineConfig) -> dict[str, object]:
    return {
        "market_penetration": config.market_penetration,
        "market_penetration_pct": config.market_penetration * 100.0,
        "seasonality_multiplier": config.seasonality_multiplier,
        "target_daily_volume": TARGET_DAILY_VOLUME,
        "service_time_per_package_min": config.service_time_per_package_min,
        "inter_package_time_min": config.inter_package_time_min,
        "max_workday_hours": config.max_workday_hours,
        "fleet": {
            "max_diesel": config.fleet.max_diesel,
            "max_electric": config.fleet.max_electric,
            "electric_max_range_km": config.fleet.electric_max_range_km,
        },
        "trailer": {
            "enabled": config.trailer.enabled,
            "packages_capacity": config.trailer.packages_capacity,
            "unloading_time_min": config.trailer.unloading_time_min,
            "big_nodes": list(config.trailer.big_nodes),
        },
        "solver_strategy": config.solver_strategy.value,
        "solver_time_limit_seconds": config.solver_time_limit_seconds,
        "economic_horizon_years": GUIDED_HORIZON_YEARS,
        "economic_discount_rate": GUIDED_DISCOUNT_RATE,
        "labor_support": "Subsidio transporte público",
        "active_mitigations": [
            "Formación",
            "Pérdida de valor DQA4",
            "Implantación por fases",
            "Sistemas de respaldo",
        ],
    }


def _pipeline_summary(
    result: PipelineResult | None,
    cost_summary: PipelineRouteCostSummary | None,
) -> dict[str, object]:
    if result is None:
        return {}
    unassigned = [result.dataset.names[index] for index in result.vrp.unassigned_nodes]
    return {
        "center": result.dataset.names[result.dataset.depot_index],
        "packages_day": int(result.packages.sum()),
        "routes_total": int(result.total_routes),
        "vrp_routes": int(result.vrp_route_count),
        "dedicated_routes": int(result.dedicated_route_count),
        "trailer_routes": int(result.trailer_route_count),
        "van_dedicated_routes": int(result.van_dedicated_route_count),
        "vrp_diesel_routes": int(result.vrp.diesel_count),
        "vrp_electric_routes": int(result.vrp.electric_count),
        "distance_km_day": float(result.total_distance_km),
        "time_min_day": float(result.total_time_min),
        "unassigned_nodes": unassigned,
        "route_costs": {
            "daily_total_eur": float(cost_summary.total_daily_cost) if cost_summary else None,
            "annual_total_eur": float(cost_summary.total_annual_cost) if cost_summary else None,
            "cost_per_package_eur": float(cost_summary.cost_per_package) if cost_summary else None,
        },
    }


def _economics_records(economics) -> list[dict[str, object]]:
    if economics is None:
        return []
    return [
        {
            "option": analysis.investment_option_name,
            "annual_saving_base_eur": analysis.investment_profile.annual_saving_base,
            "route_overcost_annual_eur": analysis.route_overcost_annual,
            "initial_cost_total_eur": analysis.initial_cost_total,
            "estimated_absolute_annual_cost_pert_eur": analysis.estimated_absolute_annual_cost_pert,
            "van_pert_eur": analysis.van_pert,
            "tir_pert": analysis.tir_pert,
            "payback_pert_years": analysis.payback_pert,
            "van_pessimistic_eur": analysis.van_pessimistic,
            "decision_score": economics.scores[analysis.investment_option_name],
            "cash_flows_pert": list(analysis.cash_flows_pert),
        }
        for analysis in economics.analyses
    ]


def _risk_records(economics) -> list[dict[str, object]]:
    if economics is None:
        return []
    return [
        {
            "option": analysis.investment_option_name,
            "risk": risk.name,
            "risk_kind": risk.risk_kind,
            "base_probability": risk.probability,
            "residual_probability": risk.residual_probability,
            "impact_eur": risk.impact,
            "expected_cost_eur": risk.expected_cost,
            "residual_expected_cost_eur": risk.residual_expected_cost,
            "mitigations": list(risk.mitigation_names),
        }
        for analysis in economics.analyses
        for risk in analysis.risk_lines
    ]


def _frame_records(frame: pd.DataFrame) -> list[dict[str, object]]:
    if frame is None or frame.empty:
        return []
    return frame.where(pd.notna(frame), None).to_dict(orient="records")


def _jsonable(value):
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, np.ndarray):
        return value.tolist()
    if pd.isna(value) if isinstance(value, float) else False:
        return None
    return value


def _write_demand_map(path: Path, dataset, packages: np.ndarray) -> None:
    canvas = _Canvas(dataset, width=1050, height=720, right_panel=260)
    positive = [idx for idx, value in enumerate(packages) if int(value) > 0]
    max_packages = max(float(packages[idx]) for idx in positive) if positive else 1.0
    body: list[str] = [_svg_background(canvas)]
    body.append(_svg_title("Mapa de demanda calibrada", canvas.width))
    body.append(_svg_subtitle("38.900 paquetes/día objetivo; demanda redondeada por nodo", canvas.width))
    body.append(_svg_axes_note(canvas))
    for idx in positive:
        x, y = canvas.xy(dataset.longitudes[idx], dataset.latitudes[idx])
        radius = 3.0 + 24.0 * math.sqrt(float(packages[idx]) / max_packages)
        body.append(
            f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{radius:.2f}" '
            'fill="#2f78a0" fill-opacity="0.58" stroke="#184963" stroke-width="0.7"/>'
        )
    _draw_hubs(body, canvas, dataset)
    top = sorted(positive, key=lambda idx: int(packages[idx]), reverse=True)[:9]
    for idx in top:
        x, y = canvas.xy(dataset.longitudes[idx], dataset.latitudes[idx])
        body.append(_text(x + 8, y - 8, f"{dataset.names[idx]} · {int(packages[idx])}", 12, "#1b2a32"))
    body.append(_legend_panel(canvas, "Nodos principales", [
        (dataset.names[idx], f"{int(packages[idx]):,}".replace(",", ".") + " paq./día")
        for idx in top[:8]
    ]))
    path.write_text(_svg(canvas.width, canvas.height, body), encoding="utf-8")


def _write_location_map(path: Path, dataset, location_frame: pd.DataFrame) -> None:
    canvas = _Canvas(dataset, width=1100, height=730, right_panel=315)
    body: list[str] = [_svg_background(canvas)]
    body.append(_svg_title("Comparativa de localización", canvas.width))
    body.append(_svg_subtitle("Referencias continuas y candidatos evaluados en distancia geométrica común", canvas.width))
    demand_indices = [idx for idx, value in enumerate(dataset.poblacion) if int(value) > 0]
    max_pop = max(float(dataset.poblacion[idx]) for idx in demand_indices) if demand_indices else 1.0
    for idx in demand_indices:
        x, y = canvas.xy(dataset.longitudes[idx], dataset.latitudes[idx])
        radius = 2.4 + 10.0 * math.sqrt(float(dataset.poblacion[idx]) / max_pop)
        body.append(
            f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{radius:.2f}" '
            'fill="#8db3c7" fill-opacity="0.35" stroke="none"/>'
        )
    colors = {
        "Técnica continua": "#2b8a3e",
        "Candidato": "#c95d2e",
    }
    for idx, row in location_frame.iterrows():
        x, y = canvas.xy(float(row["Longitud"]), float(row["Latitud"]))
        color = colors.get(str(row["Clase"]), "#6b5fb5")
        size = 9 if idx == 0 else 6
        if idx == 0:
            body.append(
                f'<polygon points="{x:.2f},{y-size:.2f} {x+size:.2f},{y:.2f} '
                f'{x:.2f},{y+size:.2f} {x-size:.2f},{y:.2f}" '
                f'fill="{color}" stroke="#152515" stroke-width="1.2"/>'
            )
        else:
            body.append(
                f'<rect x="{x-size/2:.2f}" y="{y-size/2:.2f}" width="{size:.2f}" '
                f'height="{size:.2f}" fill="{color}" stroke="#24313a" stroke-width="0.8"/>'
            )
    _draw_hubs(body, canvas, dataset)
    top_rows = location_frame.head(8)
    body.append(_legend_panel(canvas, "Mejor distancia media", [
        (str(row["Nombre"]), f'{float(row["Distancia media (km)"]):.2f} km')
        for _, row in top_rows.iterrows()
    ]))
    path.write_text(_svg(canvas.width, canvas.height, body), encoding="utf-8")


def _write_route_map(path: Path, result: PipelineResult | None) -> None:
    if result is None:
        raise ValueError("No hay resultado de rutas disponible.")
    dataset = result.dataset
    canvas = _Canvas(dataset, width=1120, height=760, right_panel=270)
    body: list[str] = [_svg_background(canvas)]
    depot_name = dataset.names[dataset.depot_index]
    body.append(_svg_title(f"Mapa de rutas desde {depot_name}", canvas.width))
    body.append(_svg_subtitle("Líneas rectas de apoyo visual; los cálculos usan la matriz OD", canvas.width))
    demand_indices = [idx for idx, value in enumerate(result.packages) if int(value) > 0]
    for idx in demand_indices:
        x, y = canvas.xy(dataset.longitudes[idx], dataset.latitudes[idx])
        body.append(
            f'<circle cx="{x:.2f}" cy="{y:.2f}" r="2.6" fill="#bcc7cc" fill-opacity="0.65"/>'
        )
    depot_x, depot_y = canvas.xy(dataset.longitudes[dataset.depot_index], dataset.latitudes[dataset.depot_index])
    palette = ["#20639b", "#3caea3", "#f6a821", "#b23a48", "#6f5fb5", "#227c4a", "#ab5e2a"]
    for route_index, route in enumerate(result.vrp.routes):
        points = [(depot_x, depot_y)]
        points.extend(
            canvas.xy(dataset.longitudes[stop.node_index], dataset.latitudes[stop.node_index])
            for stop in route.stops
        )
        points.append((depot_x, depot_y))
        body.append(
            _polyline(points, palette[route_index % len(palette)], width=1.0, opacity=0.28)
        )
    for route in result.split.dedicated_routes:
        x, y = canvas.xy(dataset.longitudes[route.node_index], dataset.latitudes[route.node_index])
        is_trailer = route.vehicle_type == "trailer"
        body.append(
            _line(
                depot_x,
                depot_y,
                x,
                y,
                "#7a3c20" if is_trailer else "#4a4f55",
                width=2.2 if is_trailer else 1.2,
                opacity=0.66,
                dash="" if is_trailer else "5 5",
            )
        )
        body.append(
            f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{6 if is_trailer else 4}" '
            f'fill="{"#c97345" if is_trailer else "#70767c"}" fill-opacity="0.85"/>'
        )
    body.append(
        f'<rect x="{depot_x - 8:.2f}" y="{depot_y - 8:.2f}" width="16" height="16" '
        'fill="#d1495b" stroke="#5f1722" stroke-width="1.2"/>'
    )
    body.append(_text(depot_x + 10, depot_y - 10, depot_name, 13, "#2b1b1f", bold=True))
    stats = [
        ("Paquetes/día", f"{int(result.packages.sum()):,}".replace(",", ".")),
        ("Rutas totales", str(result.total_routes)),
        ("Rutas VRP", str(result.vrp_route_count)),
        ("Rutas dedicadas", str(result.dedicated_route_count)),
        ("Trailers", str(result.trailer_route_count)),
        ("Distancia diaria", f"{result.total_distance_km:,.0f} km".replace(",", ".")),
        ("Tiempo diario", f"{result.total_time_min / 60.0:,.1f} h".replace(",", ".")),
    ]
    body.append(_legend_panel(canvas, "Resumen", stats))
    path.write_text(_svg(canvas.width, canvas.height, body), encoding="utf-8")


def _write_route_comparison_chart(
    path: Path,
    route_records: dict[str, dict[str, object]],
    cost_summaries: dict[str, PipelineRouteCostSummary],
) -> None:
    dqa4 = route_records[ROUTE_CENTER_CURRENT_DQA4]["pipeline_result"]
    svq1 = route_records[ROUTE_CENTER_SVQ1_EXPANDED]["pipeline_result"]
    if dqa4 is None or svq1 is None:
        raise ValueError("Faltan resultados de rutas.")
    metrics = [
        ("Rutas totales", dqa4.total_routes, svq1.total_routes, ""),
        ("km/día", dqa4.total_distance_km, svq1.total_distance_km, "km"),
        ("h/día", dqa4.total_time_min / 60.0, svq1.total_time_min / 60.0, "h"),
        (
            "Coste anual",
            cost_summaries[ROUTE_CENTER_CURRENT_DQA4].total_annual_cost / 1e6,
            cost_summaries[ROUTE_CENTER_SVQ1_EXPANDED].total_annual_cost / 1e6,
            "M€",
        ),
    ]
    body = [_svg_background_simple(980, 640), _svg_title("Comparativa de rutas DQA4 vs SVQ1", 980)]
    for panel_index, (label, value_a, value_b, unit) in enumerate(metrics):
        x = 70 + (panel_index % 2) * 450
        y = 120 + (panel_index // 2) * 235
        body.extend(_bar_pair_panel(x, y, 360, 165, label, value_a, value_b, unit))
    path.write_text(_svg(980, 640, body), encoding="utf-8")


def _write_economic_chart(path: Path, economics) -> None:
    if economics is None:
        raise ValueError("No hay resultados económicos.")
    analyses = economics.analyses
    body = [_svg_background_simple(1040, 700), _svg_title("VAN, TIR y payback por opción", 1040)]
    van_values = [
        (analysis.investment_option_name, analysis.van_pert / 1e6, analysis.van_pessimistic / 1e6)
        for analysis in analyses
    ]
    body.extend(_grouped_bar_panel(70, 125, 430, 250, "VAN PERT y pesimista (M€)", van_values, "M€"))
    tir_values = [(analysis.investment_option_name, (analysis.tir_pert or 0.0) * 100.0) for analysis in analyses]
    body.extend(_single_bar_panel(570, 125, 370, 210, "TIR PERT (%)", tir_values, "%"))
    payback_values = [
        (analysis.investment_option_name, analysis.payback_pert or 0.0)
        for analysis in analyses
    ]
    body.extend(_single_bar_panel(570, 405, 370, 210, "Payback PERT (años)", payback_values, "años"))
    path.write_text(_svg(1040, 700, body), encoding="utf-8")


def _write_pert_cashflow_chart(path: Path, economics) -> None:
    if economics is None:
        raise ValueError("No hay resultados económicos.")
    lines = []
    for analysis in economics.analyses:
        cumulative = []
        total = 0.0
        for flow in analysis.cash_flows_pert:
            total += float(flow)
            cumulative.append(total / 1e6)
        lines.append((analysis.investment_option_name, cumulative))
    body = [_svg_background_simple(1050, 650), _svg_title("Flujo acumulado PERT", 1050)]
    body.extend(_line_chart_panel(95, 120, 815, 400, lines, "Año", "M€ acumulados"))
    path.write_text(_svg(1050, 650, body), encoding="utf-8")


def _write_risk_matrix(path: Path, economics) -> None:
    if economics is None:
        raise ValueError("No hay resultados económicos.")
    best = economics.best_analysis
    body = [_svg_background_simple(980, 660), _svg_title(f"Matriz de riesgos residuales · {best.investment_option_name}", 980)]
    body.extend(_risk_matrix_panel(95, 120, 760, 420, best.risk_lines))
    path.write_text(_svg(980, 660, body), encoding="utf-8")


class _Canvas:
    def __init__(self, dataset, width: int, height: int, right_panel: int = 0) -> None:
        self.width = width
        self.height = height
        self.right_panel = right_panel
        self.padding_left = 55
        self.padding_right = 55 + right_panel
        self.padding_top = 78
        self.padding_bottom = 45
        self.min_lon = float(np.nanmin(dataset.longitudes))
        self.max_lon = float(np.nanmax(dataset.longitudes))
        self.min_lat = float(np.nanmin(dataset.latitudes))
        self.max_lat = float(np.nanmax(dataset.latitudes))
        if self.min_lon == self.max_lon:
            self.max_lon += 0.01
        if self.min_lat == self.max_lat:
            self.max_lat += 0.01

    def xy(self, longitude: float, latitude: float) -> tuple[float, float]:
        x_min = self.padding_left
        x_max = self.width - self.padding_right
        y_min = self.padding_top
        y_max = self.height - self.padding_bottom
        x = x_min + (float(longitude) - self.min_lon) / (self.max_lon - self.min_lon) * (x_max - x_min)
        y = y_max - (float(latitude) - self.min_lat) / (self.max_lat - self.min_lat) * (y_max - y_min)
        return x, y


def _svg(width: int, height: int, body: Iterable[str]) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img">\n'
        "<style>text{font-family:Arial,Helvetica,sans-serif}</style>\n"
        + "\n".join(body)
        + "\n</svg>\n"
    )


def _svg_background(canvas: _Canvas) -> str:
    return _svg_background_simple(canvas.width, canvas.height)


def _svg_background_simple(width: int, height: int) -> str:
    return f'<rect width="{width}" height="{height}" fill="#f7f6f2"/>'


def _svg_title(title: str, width: int) -> str:
    return _text(width / 2, 38, title, 23, "#17242c", anchor="middle", bold=True)


def _svg_subtitle(subtitle: str, width: int) -> str:
    return _text(width / 2, 62, subtitle, 13, "#53616a", anchor="middle")


def _svg_axes_note(canvas: _Canvas) -> str:
    left = canvas.padding_left
    top = canvas.padding_top
    right = canvas.width - canvas.padding_right
    bottom = canvas.height - canvas.padding_bottom
    return (
        f'<rect x="{left}" y="{top}" width="{right-left}" height="{bottom-top}" '
        'fill="#ffffff" fill-opacity="0.34" stroke="#d7d2c8" stroke-width="1"/>'
    )


def _draw_hubs(body: list[str], canvas: _Canvas, dataset) -> None:
    for name, color in (("SVQ1", "#d1495b"), ("DQA4", "#e59f3a")):
        if name not in dataset.names:
            continue
        idx = dataset.names.index(name)
        x, y = canvas.xy(dataset.longitudes[idx], dataset.latitudes[idx])
        body.append(
            f'<rect x="{x - 7:.2f}" y="{y - 7:.2f}" width="14" height="14" '
            f'fill="{color}" stroke="#4c2c2b" stroke-width="1.1"/>'
        )
        body.append(_text(x + 10, y + 4, name, 12, "#2d2d2d", bold=True))


def _legend_panel(canvas: _Canvas, title: str, rows: list[tuple[str, str]]) -> str:
    x = canvas.width - canvas.right_panel + 18 if canvas.right_panel else canvas.width - 265
    y = 98
    width = canvas.right_panel - 34 if canvas.right_panel else 240
    height = 48 + max(1, len(rows)) * 34
    parts = [
        f'<rect x="{x}" y="{y}" width="{width}" height="{height}" rx="7" '
        'fill="#ffffff" fill-opacity="0.88" stroke="#d8d3c9"/>',
        _text(x + 16, y + 28, title, 14, "#192a33", bold=True),
    ]
    for idx, (label, value) in enumerate(rows):
        yy = y + 58 + idx * 34
        parts.append(_text(x + 16, yy, str(label)[:34], 12, "#263941"))
        parts.append(_text(x + width - 16, yy, str(value), 12, "#263941", anchor="end", bold=True))
    return "\n".join(parts)


def _text(
    x: float,
    y: float,
    value: object,
    size: int,
    color: str,
    *,
    anchor: str = "start",
    bold: bool = False,
) -> str:
    weight = " font-weight=\"700\"" if bold else ""
    return (
        f'<text x="{x:.2f}" y="{y:.2f}" font-size="{size}" fill="{color}" '
        f'text-anchor="{anchor}"{weight}>{escape(str(value))}</text>'
    )


def _line(
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    color: str,
    *,
    width: float,
    opacity: float,
    dash: str = "",
) -> str:
    dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
    return (
        f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" '
        f'stroke="{color}" stroke-width="{width}" stroke-opacity="{opacity}" '
        f'fill="none"{dash_attr}/>'
    )


def _polyline(points: Iterable[tuple[float, float]], color: str, *, width: float, opacity: float) -> str:
    point_text = " ".join(f"{x:.2f},{y:.2f}" for x, y in points)
    return (
        f'<polyline points="{point_text}" fill="none" stroke="{color}" '
        f'stroke-width="{width}" stroke-opacity="{opacity}"/>'
    )


def _bar_pair_panel(
    x: float,
    y: float,
    width: float,
    height: float,
    title: str,
    dqa4_value: float,
    svq1_value: float,
    unit: str,
) -> list[str]:
    max_value = max(abs(float(dqa4_value)), abs(float(svq1_value)), 1.0)
    bar_max = width - 145
    rows = [("DQA4", dqa4_value, "#2f78a0"), ("SVQ1", svq1_value, "#c95d2e")]
    parts = [
        f'<rect x="{x}" y="{y}" width="{width}" height="{height}" rx="7" fill="#ffffff" stroke="#ddd6ca"/>',
        _text(x + 16, y + 28, title, 14, "#17242c", bold=True),
    ]
    for idx, (label, value, color) in enumerate(rows):
        yy = y + 62 + idx * 48
        bar_w = abs(float(value)) / max_value * bar_max
        parts.append(_text(x + 18, yy + 18, label, 12, "#32434b"))
        parts.append(f'<rect x="{x+82}" y="{yy}" width="{bar_w:.2f}" height="24" fill="{color}" fill-opacity="0.82"/>')
        parts.append(
            _text(
                x + 92 + bar_w,
                yy + 18,
                _fmt_value(value, unit),
                12,
                "#22313a",
                bold=True,
            )
        )
    return parts


def _grouped_bar_panel(
    x: float,
    y: float,
    width: float,
    height: float,
    title: str,
    values: list[tuple[str, float, float]],
    unit: str,
) -> list[str]:
    all_values = [item for _, a, b in values for item in (a, b)]
    min_value = min(min(all_values), 0.0)
    max_value = max(max(all_values), 0.0)
    if min_value == max_value:
        max_value += 1.0
    plot_x = x + 56
    plot_y = y + 42
    plot_w = width - 78
    plot_h = height - 82
    zero_y = plot_y + (max_value / (max_value - min_value)) * plot_h
    parts = [
        f'<rect x="{x}" y="{y}" width="{width}" height="{height}" rx="7" fill="#ffffff" stroke="#ddd6ca"/>',
        _text(x + 16, y + 26, title, 14, "#17242c", bold=True),
        _line(plot_x, zero_y, plot_x + plot_w, zero_y, "#79858d", width=0.9, opacity=0.75),
    ]
    group_w = plot_w / len(values)
    for idx, (label, van_pert, van_pess) in enumerate(values):
        cx = plot_x + idx * group_w + group_w / 2
        for offset, value, color in ((-14, van_pert, "#2f78a0"), (14, van_pess, "#c95d2e")):
            bar_h = abs(float(value)) / (max_value - min_value) * plot_h
            if value >= 0:
                yy = zero_y - bar_h
            else:
                yy = zero_y
            parts.append(
                f'<rect x="{cx+offset-10:.2f}" y="{yy:.2f}" width="20" height="{bar_h:.2f}" '
                f'fill="{color}" fill-opacity="0.84"/>'
            )
            parts.append(_text(cx + offset, yy - 5 if value >= 0 else yy + bar_h + 14, f"{value:.1f}", 10, "#28353b", anchor="middle"))
        parts.append(_text(cx, y + height - 20, label, 11, "#28353b", anchor="middle"))
    parts.append(_text(x + width - 18, y + 25, unit, 11, "#59666e", anchor="end"))
    return parts


def _single_bar_panel(
    x: float,
    y: float,
    width: float,
    height: float,
    title: str,
    values: list[tuple[str, float]],
    unit: str,
) -> list[str]:
    max_value = max([float(value) for _, value in values] + [1.0])
    parts = [
        f'<rect x="{x}" y="{y}" width="{width}" height="{height}" rx="7" fill="#ffffff" stroke="#ddd6ca"/>',
        _text(x + 16, y + 26, title, 14, "#17242c", bold=True),
    ]
    bar_w = (width - 90) / len(values)
    for idx, (label, value) in enumerate(values):
        h = float(value) / max_value * (height - 82)
        bx = x + 52 + idx * bar_w
        by = y + height - 42 - h
        parts.append(f'<rect x="{bx:.2f}" y="{by:.2f}" width="{bar_w*0.54:.2f}" height="{h:.2f}" fill="#4b8f8c" fill-opacity="0.86"/>')
        parts.append(_text(bx + bar_w * 0.27, by - 7, _fmt_value(value, unit), 10, "#263941", anchor="middle"))
        parts.append(_text(bx + bar_w * 0.27, y + height - 18, label, 11, "#263941", anchor="middle"))
    return parts


def _line_chart_panel(
    x: float,
    y: float,
    width: float,
    height: float,
    lines: list[tuple[str, list[float]]],
    x_label: str,
    y_label: str,
) -> list[str]:
    all_values = [value for _, values in lines for value in values]
    min_value = min(all_values + [0.0])
    max_value = max(all_values + [0.0])
    if min_value == max_value:
        max_value += 1.0
    years = max(len(values) for _, values in lines) - 1
    colors = ["#2f78a0", "#c95d2e", "#4b8f8c", "#8b6fc7"]
    parts = [
        f'<rect x="{x}" y="{y}" width="{width}" height="{height}" rx="7" fill="#ffffff" stroke="#ddd6ca"/>',
        _text(x + 18, y + 28, f"{x_label} / {y_label}", 14, "#17242c", bold=True),
    ]
    plot_x = x + 70
    plot_y = y + 55
    plot_w = width - 110
    plot_h = height - 105
    zero_y = plot_y + (max_value / (max_value - min_value)) * plot_h
    parts.append(_line(plot_x, zero_y, plot_x + plot_w, zero_y, "#7e888f", width=0.9, opacity=0.75))

    def point(index: int, value: float) -> tuple[float, float]:
        xx = plot_x + index / years * plot_w if years else plot_x
        yy = plot_y + (max_value - value) / (max_value - min_value) * plot_h
        return xx, yy

    for line_idx, (label, values) in enumerate(lines):
        color = colors[line_idx % len(colors)]
        pts = [point(idx, value) for idx, value in enumerate(values)]
        parts.append(_polyline(pts, color, width=2.4, opacity=0.92))
        for xx, yy in pts:
            parts.append(f'<circle cx="{xx:.2f}" cy="{yy:.2f}" r="3" fill="{color}"/>')
        lx, ly = pts[-1]
        parts.append(_text(lx + 8, ly + 4, label, 12, color, bold=True))
    for year in range(years + 1):
        xx, _ = point(year, 0)
        parts.append(_text(xx, y + height - 20, str(year), 10, "#4c5961", anchor="middle"))
    parts.append(_text(plot_x - 12, plot_y + 6, f"{max_value:.0f}", 10, "#4c5961", anchor="end"))
    parts.append(_text(plot_x - 12, plot_y + plot_h, f"{min_value:.0f}", 10, "#4c5961", anchor="end"))
    return parts


def _risk_matrix_panel(x: float, y: float, width: float, height: float, risk_lines) -> list[str]:
    max_impact = max(float(risk.impact) for risk in risk_lines) / 1e6
    max_prob = max(float(risk.residual_probability) for risk in risk_lines)
    max_impact = max(max_impact, 1.0)
    max_prob = max(max_prob, 0.10)
    parts = [
        f'<rect x="{x}" y="{y}" width="{width}" height="{height}" rx="7" fill="#ffffff" stroke="#ddd6ca"/>',
        _text(x + 18, y + 28, "Probabilidad residual / impacto", 14, "#17242c", bold=True),
    ]
    plot_x = x + 80
    plot_y = y + 55
    plot_w = width - 130
    plot_h = height - 105
    parts.append(f'<rect x="{plot_x}" y="{plot_y}" width="{plot_w}" height="{plot_h}" fill="#f9f7f1" stroke="#d5d0c6"/>')
    parts.append(_line(plot_x + plot_w / 2, plot_y, plot_x + plot_w / 2, plot_y + plot_h, "#d6c8ad", width=1, opacity=1))
    parts.append(_line(plot_x, plot_y + plot_h / 2, plot_x + plot_w, plot_y + plot_h / 2, "#d6c8ad", width=1, opacity=1))
    for risk in risk_lines:
        px = plot_x + float(risk.residual_probability) / max_prob * plot_w
        py = plot_y + plot_h - (float(risk.impact) / 1e6) / max_impact * plot_h
        radius = 5 + min(18, math.sqrt(float(risk.residual_expected_cost) / 1e6) * 6)
        color = "#c95d2e" if risk.risk_kind == "construction" else "#2f78a0"
        parts.append(f'<circle cx="{px:.2f}" cy="{py:.2f}" r="{radius:.2f}" fill="{color}" fill-opacity="0.72" stroke="#22313a" stroke-width="0.8"/>')
        parts.append(_text(px + radius + 4, py + 4, risk.name, 11, "#263941"))
    parts.append(_text(plot_x + plot_w / 2, y + height - 22, "Probabilidad residual", 12, "#4c5961", anchor="middle"))
    parts.append(_text(plot_x - 12, plot_y + 10, "Impacto", 12, "#4c5961", anchor="end"))
    return parts


def _fmt_value(value: float, unit: str) -> str:
    if unit == "M€":
        return f"{float(value):.2f} M€"
    if unit == "%":
        return f"{float(value):.1f}%"
    if unit == "años":
        return f"{float(value):.2f}"
    if unit == "h":
        return f"{float(value):.1f} h"
    if unit == "km":
        return f"{float(value):,.0f} km".replace(",", ".")
    return f"{float(value):,.0f}".replace(",", ".")


def _figure_dependency_hint(filename: str) -> str:
    if "rutas" in filename:
        return "Resultados de rutas DQA4/SVQ1 y costes de rutas."
    if "economico" in filename or "flujos" in filename:
        return "Comparación económica Básica/Estándar/Premium."
    if "riesgos" in filename:
        return "Riesgos residuales del cálculo económico guiado."
    if "localizacion" in filename:
        return "Comparación integrada de localización."
    return "Resultados de demanda calibrada."


def _manual_figure_hint(filename: str) -> str:
    if "rutas_dqa4" in filename:
        return "Abrir la app, calcular rutas del flujo guiado y visualizar DQA4 actual."
    if "rutas_svq1" in filename:
        return "Abrir la app, calcular rutas del flujo guiado y visualizar SVQ1 ampliado."
    if "localizacion" in filename:
        return "Abrir la app en localización y usar la comparativa integrada."
    if "economico" in filename or "flujos" in filename:
        return "Abrir el análisis económico guiado tras recalcular rutas."
    if "riesgos" in filename:
        return "Abrir el bloque de riesgos o el detalle económico de la alternativa."
    return "Abrir el bloque de demanda calibrada en el flujo guiado."


def _build_manifest(
    *,
    run_timestamp: str,
    command_used: str,
    pipeline_config: PipelineConfig,
    active_population: float,
    market_penetration: float,
    target_daily_volume: float,
    obtained_daily_volume: int,
    generated_files: list[Path],
    generated_tables: list[Path],
    generated_figures: list[dict[str, str]],
    pending_figures: list[dict[str, str]],
    warnings: list[str],
    assets_ready: bool,
) -> str:
    lines = [
        "# Assets de memoria final",
        "",
        f"- Fecha de ejecución: {run_timestamp}",
        f"- Comando usado: `{command_used}`",
        f"- Escenario apto para memoria final: {'Sí' if assets_ready else 'No'}",
        "",
        "## Parámetros del escenario",
        "",
        f"- Paquetes/día objetivo: {target_daily_volume:.0f}",
        f"- Paquetes/día tras redondeo: {obtained_daily_volume}",
        f"- Población activa: {active_population:.0f}",
        f"- Penetración calculada: {market_penetration * 100:.6f} %",
        f"- Estacionalidad: x{pipeline_config.seasonality_multiplier:.2f}",
        "- Provincias agregadas activas: Cádiz y Huelva",
        "- Servicio por paquete: 1,5 min/paquete",
        "- Tiempo técnico entre paquetes: 1,0 min",
        "- Jornada efectiva: 7,5 h",
        "- Flota máxima: 75 diésel y 45 eléctricas",
        "- Autonomía eléctrica: 350 km/jornada",
        "- Trailers: activados, 4.000 paquetes/viaje y 90 min de descarga",
        "- Método de rutas: inserción paralela",
        "- Economía: 10 años, 7 % de descuento",
        "- Apoyo laboral: subsidio de transporte público",
        "- Mitigaciones activas: formación, pérdida de valor DQA4, implantación por fases y sistemas de respaldo",
        "",
        "## Archivos generados",
        "",
    ]
    for path in sorted({_relative(path) for path in generated_files}):
        lines.append(f"- `{path}`")

    lines.extend(["", "## Tablas", ""])
    for path in sorted({_relative(path) for path in generated_tables}):
        lines.append(f"- `{path}`")

    lines.extend(["", "## Figuras creadas", ""])
    if generated_figures:
        for figure in generated_figures:
            lines.append(f"- `{figure['file']}`: {figure['description']}")
            lines.append(f"  - Pie sugerido: {figure['suggested_caption']}")
    else:
        lines.append("- No se generaron figuras.")

    lines.extend(["", "## Figuras pendientes", ""])
    if pending_figures:
        for figure in pending_figures:
            lines.append(f"- {figure['name']}")
            lines.append(f"  - Qué debería mostrar: {figure['should_show']}")
            lines.append(f"  - Depende de: {figure['depends_on']}")
            lines.append(f"  - Cómo obtenerla manualmente: {figure['manual_method']}")
            lines.append(f"  - Error: {figure['error']}")
    else:
        lines.append("- Sin figuras pendientes.")

    lines.extend(["", "## Advertencias", ""])
    if warnings:
        for warning in warnings:
            lines.append(f"- {warning}")
    else:
        lines.append("- Sin advertencias.")

    lines.extend(
        [
            "",
            "## Validación",
            "",
            f"- Escenario usa 38.900 paquetes/día: {'Sí' if abs(target_daily_volume - TARGET_DAILY_VOLUME) <= 1e-9 else 'No'}",
            f"- Penetración aproximadamente 1,548 %: {'Sí' if 0.0153 <= market_penetration <= 0.0157 else 'No'}",
            "- Rutas y economía recalculadas con esta demanda: ver snapshot y tablas exportadas.",
            "- El diferencial económico de rutas se calcula como coste anual SVQ1 menos coste anual DQA4.",
            "",
            "## Nota de uso",
            "",
            "Estos resultados son una salida reproducible del modelo para la memoria técnica. No son una previsión real de Amazon.",
        ]
    )
    return "\n".join(lines) + "\n"


def _assets_ready(
    warnings: list[str],
    pending_figures: list[dict[str, str]],
    route_records: dict[str, dict[str, object]],
    economics,
) -> bool:
    if pending_figures:
        return False
    if economics is None:
        return False
    for key in (ROUTE_CENTER_CURRENT_DQA4, ROUTE_CENTER_SVQ1_EXPANDED):
        if route_records.get(key, {}).get("pipeline_result") is None:
            return False
    blocking = [warning for warning in warnings if "No se pudo" in warning or "no se pudo" in warning]
    return not blocking


def _relative(path: Path) -> str:
    try:
        return str(Path(path).resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


if __name__ == "__main__":
    raise SystemExit(main())
