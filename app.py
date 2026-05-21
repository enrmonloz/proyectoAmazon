"""Streamlit app - VRP por tiempo desde SVQ1.

Interfaz industrial con configuracion arriba (expander + tabs), pantalla
principal centrada en el mapa de rutas y los datos de la resolucion, y
pantallas secundarias accesibles por botones para detalle por vehiculo,
rutas dedicadas, distribucion de turnos y detalle por parada.
"""

from __future__ import annotations

import datetime as _dt
from collections import Counter
from pathlib import Path

import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

# Permite ejecutar `streamlit run app.py` desde la raiz del proyecto.
import sys
THIS_DIR = Path(__file__).resolve().parent
if str(THIS_DIR) not in sys.path:
    sys.path.insert(0, str(THIS_DIR))

from src.data_loader import load_dataset, dataset_with_depot, DEPOT_NAME, SECONDARY_HUB_NAME
from src.economics_model import (
    OPERATIONAL_OPTION_CURRENT,
    OPERATIONAL_OPTION_INTERMEDIATE,
    OPERATIONAL_OPTION_SVQ1_EXPANDED,
)
from src.fleet import FleetConfig, VehicleType
from src.map_view import build_route_map
from src.pipeline import PipelineConfig, run_pipeline
from src.schedule import ScheduleConfig
from src.trailer import DEFAULT_BIG_NODES, TrailerConfig
from src.vrp_solver import SolverStrategy
from src.location_solver import LocationMethod, LocationSolver
from src.scenario_comparator import resolve_auto_new_location_dataset
from src.guided_flow import (
    ROUTABLE_CENTER_ORDER,
    get_routable_center_candidates,
    guided_center_label,
    guided_route_center_to_operational_option,
    resolve_guided_route_dataset,
)
from src.location_view import (
    render_candidate_comparison_view,
    render_comparison_view,
    render_integrated_comparison_view,
)
from src.project_sections import (
    render_economics_section,
    render_guided_flow_section,
    render_risk_section,
    render_scenario_section,
    render_scenario_tree_lab_section,
    render_timeline_section,
    render_warehouse_section,
)


st.set_page_config(
    page_title="Rutas SVQ1",
    page_icon=":truck:",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ---------------------------------------------------------------------------
# Estilos: aspecto industrial (gris oscuro + naranja Amazon, bordes definidos)
# ---------------------------------------------------------------------------
_INDUSTRIAL_CSS = """
<style>
    :root {
        /* Branding (cabecera) */
        --brand-dark: #1a1d23;
        --brand-darker: #11141a;
        --accent: #ff9900;
        --accent-dim: #c97400;
        --accent-soft: #fff4e0;

        /* Cuerpo claro */
        --bg-app: #f5f6f8;
        --bg-card: #ffffff;
        --bg-soft: #eef0f4;
        --text-main: #1f2329;
        --text-dim: #5b6470;
        --border: #d6d9de;
        --border-strong: #b9bdc4;
    }

    /* Fondo principal claro y ancho razonable */
    .stApp {
        background-color: var(--bg-app);
    }
    section.main > div.block-container {
        padding-top: 1.2rem;
        padding-bottom: 2rem;
        max-width: 1400px;
    }

    /* Cabecera oscura como branding industrial */
    .industrial-header {
        background: linear-gradient(90deg, var(--brand-darker) 0%, var(--brand-dark) 100%);
        border-left: 6px solid var(--accent);
        padding: 1.1rem 1.3rem;
        margin-bottom: 1.1rem;
        border-radius: 2px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.18);
    }
    .industrial-header h1 {
        margin: 0;
        font-size: 1.7rem;
        font-weight: 700;
        letter-spacing: 0.04em;
        color: #ffffff;
        text-transform: uppercase;
    }
    .industrial-header .subtitle {
        color: #c9ced6;
        font-size: 0.9rem;
        margin-top: 0.25rem;
        letter-spacing: 0.02em;
    }
    .industrial-tag {
        display: inline-block;
        background: var(--accent);
        color: var(--brand-dark);
        font-weight: 700;
        padding: 0.15rem 0.55rem;
        margin-right: 0.5rem;
        font-size: 0.72rem;
        letter-spacing: 0.1em;
        border-radius: 2px;
    }

    /* Cards de metricas: fondo blanco, borde claro, accent naranja */
    div[data-testid="stMetric"] {
        background: var(--bg-card);
        border: 1px solid var(--border);
        border-left: 4px solid var(--accent);
        padding: 0.85rem 1rem;
        border-radius: 3px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.04);
    }
    div[data-testid="stMetricLabel"] p {
        text-transform: uppercase;
        font-size: 0.74rem !important;
        letter-spacing: 0.08em;
        color: var(--text-dim) !important;
        font-weight: 600 !important;
    }
    div[data-testid="stMetricValue"] {
        font-weight: 700 !important;
        font-size: 1.7rem !important;
        color: var(--text-main) !important;
    }

    /* Boton primario en naranja Amazon */
    div.stButton > button[kind="primary"] {
        background: var(--accent);
        color: var(--brand-dark);
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        border: none;
        border-radius: 2px;
        padding: 0.6rem 1.2rem;
        box-shadow: 0 1px 2px rgba(0,0,0,0.15);
    }
    div.stButton > button[kind="primary"]:hover {
        background: var(--accent-dim);
        color: #ffffff;
    }

    /* Botones secundarios (navegacion) */
    div.stButton > button[kind="secondary"] {
        background: var(--bg-card);
        color: var(--text-main);
        border: 1px solid var(--border-strong);
        border-radius: 2px;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        font-size: 0.78rem;
        font-weight: 600;
        padding: 0.55rem 0.9rem;
    }
    div.stButton > button[kind="secondary"]:hover {
        border-color: var(--accent);
        color: var(--accent-dim);
        background: var(--accent-soft);
    }

    /* Expander de configuracion */
    div[data-testid="stExpander"] {
        background: var(--bg-card);
        border: 1px solid var(--border);
        border-radius: 3px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.04);
    }
    div[data-testid="stExpander"] summary {
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        font-size: 0.85rem;
        color: var(--text-main);
    }
    div[data-testid="stExpander"] summary:hover {
        color: var(--accent-dim);
    }

    /* Tabs internos del expander */
    div[data-baseweb="tab-list"] {
        border-bottom: 1px solid var(--border) !important;
    }
    button[data-baseweb="tab"] {
        font-weight: 600;
        letter-spacing: 0.04em;
        text-transform: uppercase;
        font-size: 0.78rem;
    }
    button[data-baseweb="tab"][aria-selected="true"] {
        color: var(--accent-dim) !important;
        border-bottom-color: var(--accent) !important;
    }

    /* Subtitulos de seccion */
    .section-title {
        text-transform: uppercase;
        letter-spacing: 0.08em;
        font-weight: 700;
        font-size: 0.95rem;
        color: var(--text-main);
        border-bottom: 2px solid var(--accent);
        padding-bottom: 0.3rem;
        margin: 1.2rem 0 0.7rem 0;
    }

    /* Tablas: borde claro y filas legibles */
    div[data-testid="stDataFrame"] {
        border: 1px solid var(--border);
        border-radius: 3px;
        background: var(--bg-card);
    }

    /* Avisos (warning, info) con buen contraste sobre fondo claro */
    div[data-testid="stAlert"] {
        border-radius: 3px;
    }

    /* Inputs y selects: borde claro, fondo blanco */
    div[data-baseweb="input"] input,
    div[data-baseweb="select"] > div,
    div[data-baseweb="time-input"] input {
        background: var(--bg-card) !important;
    }

    /* Captions */
    div[data-testid="stCaptionContainer"], .stCaption {
        color: var(--text-dim) !important;
    }
</style>
"""


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------
def _format_minutes(minutes: float) -> str:
    if minutes is None:
        return "-"
    h = int(minutes // 60)
    m = int(round(minutes - h * 60))
    if h == 0:
        return f"{m} min"
    return f"{h} h {m} min"


@st.cache_data(show_spinner=False)
def _cached_dataset(poblacion_path: str, rutas_path: str):
    return load_dataset(
        poblacion_path=poblacion_path,
        rutas_path=rutas_path,
    )


def _section_title(text: str) -> None:
    st.markdown(f"<div class='section-title'>{text}</div>", unsafe_allow_html=True)


def _go(view: str) -> None:
    st.session_state["view"] = view


# ---------------------------------------------------------------------------
# Serialization helpers (CSV / JSON exports)
# ---------------------------------------------------------------------------
def serialize_vrp_routes_csv(pipeline_result) -> bytes:
    """Serializa rutas VRP + dedicadas a CSV usando pandas y devuelve bytes UTF-8."""
    rows = []
    # VRP routes
    for r_idx, (route, sch) in enumerate(
        zip(pipeline_result.vrp.routes, pipeline_result.vrp_schedules), start=1
    ):
        for stop, stop_sch in zip(route.stops, sch.stops):
            rows.append(
                {
                    "route_type": "vrp",
                    "route_id": r_idx,
                    "vehicle_id": route.vehicle_id,
                    "vehicle_type": route.vehicle_type.name if hasattr(route.vehicle_type, "name") else str(route.vehicle_type),
                    "node_index": int(stop.node_index),
                    "node_name": stop.node_name,
                    "arrival_clock": stop_sch.arrival_clock,
                    "leave_clock": stop_sch.leave_clock,
                    "period": stop_sch.period,
                    "packages": int(stop.packages),
                    "service_time_min": float(stop.service_time_min),
                    "route_travel_time_min": float(route.travel_time_min),
                    "route_service_time_min": float(route.service_time_min),
                    "route_travel_distance_km": float(route.travel_distance_km),
                    "route_total_time_min": float(route.total_time_min),
                }
            )
    # Dedicated routes
    for r_idx, (r, sch) in enumerate(
        zip(pipeline_result.split.dedicated_routes, pipeline_result.dedicated_schedules), start=1
    ):
        for stop_sch in sch.stops:
            rows.append(
                {
                    "route_type": "dedicated",
                    "route_id": r_idx,
                    "vehicle_id": None,
                    "vehicle_type": r.vehicle_type if hasattr(r, "vehicle_type") else "furgoneta",
                    "node_index": int(r.node_index),
                    "node_name": r.node_name,
                    "arrival_clock": stop_sch.arrival_clock,
                    "leave_clock": stop_sch.leave_clock,
                    "period": stop_sch.period,
                    "packages": int(r.packages),
                    "service_time_min": float(r.service_time_min),
                    "route_travel_time_min": float(r.travel_time_min),
                    "route_service_time_min": float(r.service_time_min),
                    "route_travel_distance_km": float(r.travel_distance_km),
                    "route_total_time_min": float(r.total_time_min),
                }
            )

    df = pd.DataFrame(rows)
    return df.to_csv(index=False).encode("utf-8")


def serialize_vrp_summary_json(pipeline_result) -> bytes:
    """Serializa un resumen del pipeline a JSON (bytes UTF-8)."""
    import json

    summary = {
        "total_routes": int(pipeline_result.total_routes),
        "vrp_route_count": int(pipeline_result.vrp_route_count),
        "dedicated_route_count": int(pipeline_result.dedicated_route_count),
        "total_distance_km": float(pipeline_result.total_distance_km),
        "total_time_min": float(pipeline_result.total_time_min),
        "diesel_count": int(pipeline_result.vrp.diesel_count),
        "electric_count": int(pipeline_result.vrp.electric_count),
        "total_packages": int(pipeline_result.packages.sum()) if hasattr(pipeline_result, "packages") else None,
        "objective_value": int(pipeline_result.vrp.objective_value) if getattr(pipeline_result.vrp, "objective_value", None) is not None else None,
    }
    return json.dumps(summary, indent=2, ensure_ascii=False).encode("utf-8")


def serialize_location_result_csv(location_result) -> bytes:
    """Serializa un LocationResult a CSV de una sola fila usando pandas."""
    row = {
        "method": location_result.method.value if hasattr(location_result.method, "value") else str(location_result.method),
        "latitude": float(location_result.latitude),
        "longitude": float(location_result.longitude),
        "weighted_distance": float(location_result.weighted_distance),
        "max_weighted_distance": float(location_result.max_weighted_distance),
        "nearest_municipality": location_result.nearest_municipality,
        "distance_to_nearest_km": float(location_result.distance_to_nearest_km) if location_result.distance_to_nearest_km is not None else None,
        "objective_value": float(location_result.objective_value) if location_result.objective_value is not None else None,
    }
    df = pd.DataFrame([row])
    return df.to_csv(index=False).encode("utf-8")


# ---------------------------------------------------------------------------
# Panel de configuracion (arriba, expander con tabs)
# ---------------------------------------------------------------------------
def render_config_panel() -> dict:
    """Renderiza el panel de configuracion y devuelve los valores elegidos."""
    with st.expander("Configuración principal", expanded=False):
        st.caption(
            "Ajusta las decisiones clave del cálculo. Los detalles técnicos quedan "
            "en bloques avanzados y no cambian el objetivo del proyecto."
        )
        tabs = st.tabs(["Demanda", "Flota", "Trailers", "Horario", "Método de rutas"])

        # --- Tab: Demanda ---
        with tabs[0]:
            st.caption(
                "La demanda se estima a partir de población como aproximación. Puedes "
                "calibrarla con un volumen diario y aplicar estacionalidad; no es una previsión real."
            )
            c1, c2, c3 = st.columns(3)
            market_pct = c1.number_input(
                "Penetracion de mercado (%)",
                min_value=0.001,
                max_value=100.0,
                value=1.064,
                step=0.001,
                format="%.3f",
                help=(
                    "Convierte población en paquetes estimados. Se puede ajustar o "
                    "calibrar con un volumen diario objetivo."
                ),
            )
            seasonality_options = {
                "Base (1.00)": 1.00,
                "Enero-marzo (-15%)": 0.85,
                "Julio-septiembre (+8%)": 1.08,
                "Octubre-diciembre (+25%)": 1.25,
            }
            seasonality_label = c2.selectbox(
                "Estacionalidad",
                options=list(seasonality_options.keys()),
                index=0,
                help="Multiplicador aplicado después de calcular la demanda base.",
            )
            use_target_volume = c3.checkbox(
                "Calibrar volumen diario",
                value=False,
                help="Si se activa, ajusta la estimación para llegar al volumen diario indicado.",
            )
            target_daily_volume = c3.number_input(
                "Volumen objetivo (paquetes/dia)",
                min_value=1.0,
                max_value=1_000_000.0,
                value=38_900.0,
                step=100.0,
                disabled=not use_target_volume,
                help="Volumen diario usado solo cuando la calibración está activa.",
            )
            with st.expander("Ajustes avanzados de demanda", expanded=False):
                st.caption(
                    "Estos tiempos convierten paquetes en minutos de servicio para el cálculo de rutas."
                )
                c1, c2 = st.columns(2)
                service_min = c1.number_input(
                    "Servicio por paquete (min)",
                    min_value=0.0,
                    max_value=30.0,
                    value=1.5,
                    step=0.5,
                    help="Minutos de manipulación asociados a cada paquete.",
                )
                inter_min = c2.number_input(
                    "Conduccion entre paquetes (min)",
                    min_value=0.0,
                    max_value=30.0,
                    value=1.0,
                    step=0.5,
                    help="Tiempo técnico adicional usado para aproximar servicio entre paquetes.",
                )
            new_pops = {}  # Ya no hay nodos nuevos en el XLSX

        # --- Tab: Flota ---
        with tabs[1]:
            st.caption(
                "Estas cotas limitan cuántos vehículos puede usar el cálculo de rutas. "
                "El coste anual de flota se analiza en Economía > Vista avanzada > Flota."
            )
            c1, c2, c3 = st.columns(3)
            max_diesel = c1.number_input(
                "Cota furgonetas diesel",
                min_value=0,
                max_value=500,
                value=75,
                step=5,
                help="Máximo de furgonetas diésel que puede usar el cálculo de rutas.",
            )
            max_electric = c2.number_input(
                "Cota furgonetas electricas",
                min_value=0,
                max_value=500,
                value=45,
                step=5,
                help="Máximo de furgonetas eléctricas disponibles para el cálculo de rutas.",
            )
            electric_range = c3.number_input(
                "Rango electrico (km/jornada)",
                min_value=50.0,
                max_value=1000.0,
                value=350.0,
                step=10.0,
                help="Límite de distancia diario para vehículos eléctricos.",
            )
            with st.expander("Pesos internos del cálculo", expanded=False):
                st.caption(
                    "Ajustes internos para preferir tipos de vehículo; no son el coste anual real."
                )
                cc1, cc2 = st.columns(2)
                diesel_cost = int(
                    cc1.number_input(
                        "Coste fijo diesel", min_value=0, max_value=10_000_000,
                        value=1_050_000, step=10_000,
                    )
                )
                electric_cost = int(
                    cc2.number_input(
                        "Coste fijo electrica", min_value=0, max_value=10_000_000,
                        value=1_000_000, step=10_000,
                    )
                )

        # --- Tab: Trailers ---
        with tabs[2]:
            st.caption(
                "Los trailers se usan cuando un municipio concentra mucha demanda o rutas largas. "
                "Las rutas dedicadas se separan para no mezclar esas cargas con el resto."
            )
            trailer_enabled = st.checkbox(
                "Usar trailers para municipios con mucha demanda (Cadiz, Malaga, Cordoba, Huelva, Granada)",
                value=True,
                help="Activa el tratamiento especial de municipios grandes definidos en el proyecto.",
            )
            with st.expander("Ajustes avanzados de trailers", expanded=False):
                st.caption("Parámetros técnicos usados solo para calcular esas rutas dedicadas.")
                c1, c2 = st.columns(2)
                trailer_capacity = c1.number_input(
                    "Capacidad trailer (paquetes/viaje)",
                    min_value=10,
                    max_value=20_000,
                    value=4_000,
                    step=50,
                    disabled=not trailer_enabled,
                    help="Paquetes máximos que se asignan a cada viaje de trailer.",
                )
                trailer_unloading = c2.number_input(
                    "Tiempo de descarga (min)",
                    min_value=0.0,
                    max_value=240.0,
                    value=90.0,
                    step=5.0,
                    disabled=not trailer_enabled,
                    help="Tiempo añadido al servicio de una ruta con trailer.",
                )

        # --- Tab: Horario ---
        with tabs[3]:
            st.caption(
                "La jornada efectiva es el límite principal del cálculo de rutas. La pausa "
                "solo organiza la visualización de turnos, no añade tiempo disponible."
            )
            c1, c2 = st.columns(2)
            max_workday_hours = c1.number_input(
                "Jornada efectiva (h)",
                min_value=1.0, max_value=14.0, value=7.5, step=0.25,
                help="Tiempo efectivo de trabajo. La pausa no se cuenta aquí.",
            )
            start_clock = c2.time_input(
                "Hora de inicio",
                value=_dt.time(8, 0),
                help="Hora usada para traducir minutos de ruta a reloj de turno.",
            )
            with st.expander("Ajustes avanzados de turnos", expanded=False):
                c1, c2 = st.columns(2)
                morning_max_min = c1.number_input(
                    "Tiempo continuado antes de pausa (min)",
                    min_value=60.0,
                    max_value=480.0,
                    value=240.0,
                    step=15.0,
                    help="Umbral a partir del cual se inserta la pausa para comer.",
                )
                lunch_break_min = c2.number_input(
                    "Duracion pausa para comer (min)",
                    min_value=0.0,
                    max_value=240.0,
                    value=90.0,
                    step=5.0,
                    help="Pausa usada para construir horarios; no cambia la jornada efectiva.",
                )

        # --- Tab: Metodo de rutas ---
        with tabs[4]:
            st.caption(
                "El método calcula rutas factibles con jornada y autonomía eléctrica. "
                "Cambiar el método sirve para comparar sensibilidad, no el objetivo del proyecto."
            )
            strategy_options = {
                "Vecino mas cercano (Nearest Neighbor)": SolverStrategy.NEAREST_NEIGHBOR,
                "Algoritmo de barrido (Sweep)": SolverStrategy.SWEEP,
                "Clarke-Wright (Savings)": SolverStrategy.SAVINGS,
                "Insercion paralela": SolverStrategy.INSERTION,
                "Christofides (3/2-aprox.)": SolverStrategy.CHRISTOFIDES,
            }
            strategy_label = st.selectbox(
                "Metodo de calculo de rutas",
                options=list(strategy_options.keys()),
                index=3,
                help="Elige el método de búsqueda; todos respetan jornada y autonomía.",
            )
            with st.expander("Ajustes avanzados del método", expanded=False):
                time_limit = st.number_input(
                    "Tiempo maximo (s)",
                    min_value=5,
                    max_value=600,
                    value=30,
                    step=5,
                    help="Límite de búsqueda para mejorar la solución.",
                )

    return {
        "market_pct": market_pct,
        "service_min": service_min,
        "inter_min": inter_min,
        "seasonality_multiplier": float(seasonality_options[seasonality_label]),
        "target_daily_volume": float(target_daily_volume) if use_target_volume else None,
        "new_pops": new_pops,
        "max_diesel": int(max_diesel),
        "max_electric": int(max_electric),
        "electric_range": float(electric_range),
        "diesel_cost": diesel_cost,
        "electric_cost": electric_cost,
        "trailer_enabled": bool(trailer_enabled),
        "trailer_capacity": int(trailer_capacity),
        "trailer_unloading": float(trailer_unloading),
        "max_workday_hours": float(max_workday_hours),
        "start_clock": start_clock,
        "morning_max_min": float(morning_max_min),
        "lunch_break_min": float(lunch_break_min),
        "solver_strategy": strategy_options[strategy_label],
        "time_limit": int(time_limit),
    }


def build_pipeline_config(params: dict) -> PipelineConfig:
    fleet = FleetConfig(
        max_diesel=params["max_diesel"],
        max_electric=params["max_electric"],
        electric_max_range_km=params["electric_range"],
        diesel_fixed_cost=params["diesel_cost"],
        electric_fixed_cost=params["electric_cost"],
    )
    trailer = TrailerConfig(
        enabled=params["trailer_enabled"],
        packages_capacity=params["trailer_capacity"],
        unloading_time_min=params["trailer_unloading"],
        big_nodes=DEFAULT_BIG_NODES,
    )
    schedule_cfg = ScheduleConfig(
        start_hour=int(params["start_clock"].hour),
        start_minute=int(params["start_clock"].minute),
        lunch_break_min=params["lunch_break_min"],
        morning_max_min=params["morning_max_min"],
    )
    return PipelineConfig(
        market_penetration=params["market_pct"] / 100.0,
        max_workday_hours=params["max_workday_hours"],
        service_time_per_package_min=params["service_min"],
        inter_package_time_min=params["inter_min"],
        seasonality_multiplier=params["seasonality_multiplier"],
        target_daily_volume=params["target_daily_volume"],
        fleet=fleet,
        trailer=trailer,
        schedule=schedule_cfg,
        solver_strategy=params["solver_strategy"],
        solver_time_limit_seconds=params["time_limit"],
    )


def _resolve_operational_dataset(dataset, center_option: str):
    """Devuelve dataset con depot compatible con la alternativa operativa."""
    notes: list[str] = []
    routable_candidates = get_routable_center_candidates(dataset)
    if center_option in routable_candidates:
        dataset_for_run = resolve_guided_route_dataset(dataset, center_option)
        candidate = routable_candidates[center_option]
        notes.append(
            f"{guided_center_label(center_option)} calcula rutas desde el nodo OD "
            f"{candidate['node_index']} ({candidate['node_name']}) de la matriz v2."
        )
        return dataset_for_run, notes

    if center_option == OPERATIONAL_OPTION_CURRENT:
        notes.append(
            "Estructura actual calcula la última milla desde DQA4 y mantiene la transferencia SVQ1-DQA4."
        )
        return dataset_with_depot(dataset, SECONDARY_HUB_NAME), notes

    if center_option == OPERATIONAL_OPTION_SVQ1_EXPANDED:
        notes.append(
            "SVQ1 ampliado calcula la última milla desde SVQ1; DQA4 sigue operando para otros flujos."
        )
        return dataset_with_depot(dataset, DEPOT_NAME), notes

    if center_option == OPERATIONAL_OPTION_INTERMEDIATE:
        dataset_for_run, auto_notes = resolve_auto_new_location_dataset(dataset)
        notes.extend(auto_notes)
        return dataset_for_run, notes

    raise ValueError(f"Alternativa operativa no reconocida: {center_option}")


def _pipeline_signature(params: dict, center_option: str, dataset_for_run) -> tuple:
    return (
        center_option,
        dataset_for_run.depot_index,
        params["market_pct"],
        params["service_min"],
        params["inter_min"],
        params["seasonality_multiplier"],
        params["target_daily_volume"],
        params["max_diesel"],
        params["max_electric"],
        params["electric_range"],
        params["diesel_cost"],
        params["electric_cost"],
        params["trailer_enabled"],
        params["trailer_capacity"],
        params["trailer_unloading"],
        params["max_workday_hours"],
        params["start_clock"],
        params["morning_max_min"],
        params["lunch_break_min"],
        params["solver_strategy"].value,
        params["time_limit"],
    )


# ---------------------------------------------------------------------------
# Pantallas
# ---------------------------------------------------------------------------
def view_main(result, dataset) -> None:
    """Pantalla principal: resumen + mapa + botones de navegacion."""
    _section_title("Resumen de rutas calculadas")
    st.caption(
        "El resumen muestra cuántas rutas hacen falta para servir la demanda estimada "
        "desde el centro de salida elegido, con jornada efectiva y autonomía eléctrica."
    )
    cols = st.columns(4)
    cols[0].metric("Total rutas", result.total_routes)
    cols[1].metric("Rutas de reparto", result.vrp_route_count)
    cols[2].metric("Rutas dedicadas", result.dedicated_route_count)
    cols[3].metric("Paquetes totales", f"{int(result.packages.sum()):,}")

    cols2 = st.columns(4)
    cols2[0].metric("Distancia total", f"{result.total_distance_km:,.0f} km")
    cols2[1].metric("Tiempo total", _format_minutes(result.total_time_min))
    cols2[2].metric("Diesel (reparto)", result.vrp.diesel_count)
    cols2[3].metric("Electricas (reparto)", result.vrp.electric_count)
    st.caption(
        "Las rutas dedicadas separan municipios con mucha carga o tiempo. "
        "La capacidad física de furgonetas no se usa como límite activo."
    )

    if result.vrp.unassigned_nodes:
        st.warning(
            "Municipios sin asignar: "
            + ", ".join(dataset.names[i] for i in result.vrp.unassigned_nodes)
        )

    _section_title("Mapa de rutas")
    st.caption(
        "Cada color representa una ruta de reparto distinta. Las lineas marrones "
        "son rutas con trailer y las grises punteadas son furgonetas dedicadas. "
        "El mapa es orientativo; haz click para ver detalle."
    )
    fmap = build_route_map(dataset, result)
    st_folium(fmap, height=560, use_container_width=True, returned_objects=[])

    _section_title("Detalle adicional")
    nav = st.columns(4)
    if nav[0].button("Detalle por vehiculo", use_container_width=True):
        _go("vehicles")
        st.rerun()
    if nav[1].button("Rutas dedicadas y trailers", use_container_width=True):
        _go("dedicated")
        st.rerun()
    if nav[2].button("Distribucion de turnos", use_container_width=True):
        _go("shifts")
        st.rerun()
    if nav[3].button("Detalle parada a parada", use_container_width=True):
        _go("stops")
        st.rerun()


def _back_button() -> None:
    if st.button("Volver al resumen", type="secondary"):
        _go("main")
        st.rerun()


def view_location_selector(dataset) -> None:
    """Pantalla principal de localización con selector de técnica mejorado."""
    st.markdown(
        "Esta pestaña compara ubicaciones posibles para un centro unificado. "
        "Distingue entre referencias matemáticas y candidatos reales como SVQ1, DQA4 o un punto intermedio."
    )
    st.caption(
        "La localización orienta por distancia geométrica común; la decisión final depende también "
        "de economía, personas, riesgos y cronograma."
    )

    technique_options = [
        ("gravity_center", "🌍 Centro de Gravedad"),
        ("min_total_distance", "📏 Minimizar Distancia Total"),
        ("minimax", "⚖️ Minimax (Equilibrar distancias)"),
        ("geographic_center", "🗺️ Centro Geográfico"),
        ("k_median", "🎲 K-Median (Iterativo)"),
    ]

    solver = LocationSolver(dataset)
    render_integrated_comparison_view(dataset, solver)

    with st.expander("Detalle por técnica", expanded=False):
        render_comparison_view(dataset, solver)

    with st.expander("Detalle de candidatos por método", expanded=False):
        technique_label = st.selectbox(
            "Método para la referencia matemática",
            options=technique_options,
            format_func=lambda x: x[1],
            key="technique_select",
            help="Método matemático usado para generar la referencia continua.",
        )
        technique = technique_label[0]
        result = solver.solve(LocationMethod(technique))
        st.session_state["last_location_result"] = result
        render_candidate_comparison_view(dataset, solver, result)


def view_vehicles(result) -> None:
    _back_button()
    _section_title("Detalle por vehiculo")
    st.caption(
        "Cada fila es una ruta de reparto asignada a una furgoneta. Revisa tiempo, distancia "
        "y turno para detectar rutas cercanas al límite de jornada."
    )
    if not result.vrp.routes:
        st.info("No se han calculado rutas de reparto.")
        return
    rows = []
    for route, sch in zip(result.vrp.routes, result.vrp_schedules):
        tipo = "Diesel" if route.vehicle_type == VehicleType.DIESEL else "Electrica"
        morning_names = [s.node_name for s in sch.stops if s.period == "manana"]
        afternoon_names = [s.node_name for s in sch.stops if s.period == "tarde"]
        rows.append(
            {
                "Vehiculo": route.vehicle_id,
                "Tipo": tipo,
                "# paradas": len(route.stops),
                "Paquetes": sum(s.packages for s in route.stops),
                "Tiempo total (min)": round(route.total_time_min, 1),
                "Distancia (km)": round(route.travel_distance_km, 1),
                "Inicio": sch.start_clock,
                "Pausa": "-" if not sch.has_lunch_break
                          else f"{sch.morning_end_clock} -> {sch.afternoon_start_clock}",
                "Fin": sch.end_clock,
                "Turno": sch.shift_label,
                "Manana (#)": sch.morning_stops,
                "Tarde (#)": sch.afternoon_stops,
                "Nodos manana": " - ".join(morning_names) if morning_names else "-",
                "Nodos tarde": " - ".join(afternoon_names) if afternoon_names else "-",
            }
        )
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)


def view_dedicated(result) -> None:
    _back_button()
    _section_title("Rutas dedicadas (trailers + furgonetas dedicadas)")
    st.caption(
        "Estas rutas se separan cuando un municipio concentra demasiada demanda o tiempo "
        "para mezclarlo con otras paradas."
    )
    if not result.split.dedicated_routes:
        st.info("Ningun municipio necesita ruta dedicada con los parametros actuales.")
        return
    rows = []
    for r_idx, (r, sch) in enumerate(
        zip(result.split.dedicated_routes, result.dedicated_schedules), start=1
    ):
        rows.append(
            {
                "Ruta": r_idx,
                "Tipo": r.vehicle_type.capitalize(),
                "Nodo": r.node_name,
                "Paquetes": r.packages,
                "Viaje (min)": round(r.travel_time_min, 1),
                "Servicio (min)": round(r.service_time_min, 1),
                "Total (min)": round(r.total_time_min, 1),
                "Distancia (km)": round(r.travel_distance_km, 1),
                "Inicio": sch.start_clock,
                "Pausa": "-" if not sch.has_lunch_break
                          else f"{sch.morning_end_clock} -> {sch.afternoon_start_clock}",
                "Fin": sch.end_clock,
                "Turno": sch.shift_label,
            }
        )
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)


def view_shifts(result) -> None:
    _back_button()
    _section_title("Distribucion de turnos")

    all_schedules = list(result.vrp_schedules) + list(result.dedicated_schedules)
    total = len(all_schedules)
    if total == 0:
        st.info("No hay rutas que mostrar.")
        return

    # Conteo por shift_label completo (los 5 posibles).
    expected_labels = [
        "Solo mañana",
        "Mañana + retorno tarde",
        "Mañana + tarde",
        "Solo tarde",
        "Sin paradas",
    ]
    counts = Counter(s.shift_label for s in all_schedules)

    with_break = sum(1 for s in all_schedules if s.has_lunch_break)
    without_break = total - with_break

    st.caption(
        "Las rutas se clasifican según el tramo de la jornada en que se realizan "
        "las paradas y si hay pausa para comer."
    )

    # Resumen agregado.
    cols = st.columns(3)
    cols[0].metric("Total rutas", total)
    cols[1].metric("Con pausa para comer", with_break)
    cols[2].metric("Sin pausa", without_break)

    # Tabla detallada con TODAS las categorias (suma cuadra con total).
    rows = [
        {
            "Tipo de turno": label,
            "Rutas": int(counts.get(label, 0)),
            "% del total": f"{(counts.get(label, 0) / total * 100):.1f}%",
        }
        for label in expected_labels
    ]
    rows.append(
        {
            "Tipo de turno": "TOTAL",
            "Rutas": total,
            "% del total": "100.0%",
        }
    )
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

    # Barra horizontal sencilla para visualizar.
    chart_df = pd.DataFrame(
        {"Rutas": [counts.get(label, 0) for label in expected_labels]},
        index=expected_labels,
    )
    chart_df = chart_df[chart_df["Rutas"] > 0]
    if not chart_df.empty:
        st.bar_chart(chart_df, horizontal=True)

    # Glosario para que el usuario entienda cada categoria.
    with st.expander("Explicacion de cada tipo de turno"):
        st.markdown(
            "- **Solo mañana**: la ruta termina antes del umbral de pausa; el "
            "conductor no necesita parar a comer.\n"
            "- **Mañana + retorno tarde**: las paradas son todas de mañana, "
            "pero la jornada cruza el umbral y el conductor toma la pausa "
            "antes de regresar al centro de salida.\n"
            "- **Mañana + tarde**: el conductor sirve paradas tanto antes "
            "como despues de la pausa para comer.\n"
            "- **Solo tarde**: todas las paradas son posteriores a la pausa "
            "(no se da habitualmente con inicio matinal).\n"
            "- **Sin paradas**: vehiculo asignado pero sin clientes (no debe "
            "darse en condiciones normales)."
        )


def view_stops(result) -> None:
    _back_button()
    _section_title("Detalle parada a parada")
    st.caption(
        "Lectura operativa de cada ruta: orden de paradas, hora estimada de llegada "
        "y tiempo de servicio asociado a los paquetes."
    )
    if not result.vrp.routes:
        st.info("No hay rutas de reparto.")
        return
    rows = []
    for route, sch in zip(result.vrp.routes, result.vrp_schedules):
        for stop, stop_sch in zip(route.stops, sch.stops):
            rows.append(
                {
                    "Vehiculo": route.vehicle_id,
                    "Tipo": "Diesel" if route.vehicle_type == VehicleType.DIESEL else "Electrica",
                    "Parada": stop_sch.node_name,
                    "Llegada": stop_sch.arrival_clock,
                    "Salida": stop_sch.leave_clock,
                    "Tramo": stop_sch.period.capitalize(),
                    "Paquetes": stop.packages,
                    "Servicio (min)": round(stop.service_time_min, 1),
                }
            )
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
def main() -> None:
    st.markdown(_INDUSTRIAL_CSS, unsafe_allow_html=True)

    st.markdown(
        """
        <div class='industrial-header'>
            <h1>🚀 Proyecto de Amazon</h1>
            <div class='subtitle'>
                Análisis operativo integrado: rutas, localización, cronograma, escenario, almacén, economía y riesgos
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if "view" not in st.session_state:
        st.session_state["view"] = "main"

    # Cargar dataset (necesario para ambas vistas)
    data_dir = THIS_DIR / "data"
    try:
        dataset = _cached_dataset(
            str(data_dir / "poblacion.csv"),
            # Matriz OD de trabajo actual: incluye centros candidatos de rutas.
            str(data_dir / "rutasDistTiempo_v2.csv"),
        )
    except Exception as exc:
        st.error(f"Error cargando datos: {exc}")
        st.stop()

    logistics_centers = sum(1 for name in (DEPOT_NAME, SECONDARY_HUB_NAME) if name in dataset.names)
    st.caption(
        f"✓ Dataset cargado: {dataset.n_nodes} nodos | "
        f"{logistics_centers} centros logísticos ({DEPOT_NAME}, {SECONDARY_HUB_NAME})"
    )

    with st.expander("Glosario rápido", expanded=False):
        st.markdown(
            "- **CAPEX / OPEX**: inversión inicial y costes anuales recurrentes.\n"
            "- **VAN / TIR**: valor económico actualizado y rentabilidad aproximada del proyecto.\n"
            "- **Rutas calculadas (VRP)**: problema de reparto con vehículos; aquí se usa como propuesta de rutas.\n"
            "- **Ruta dedicada**: trayecto separado para municipios con mucha carga o tiempo.\n"
            "- **Estacionalidad / riesgo residual**: meses de baja/normal/alta demanda; riesgo que queda tras aplicar apoyos."
        )

    st.caption(
        "La configuración de rutas es compartida por el flujo guiado y el análisis por módulos."
    )
    params = render_config_panel()
    st.session_state["last_route_params"] = params
    pipeline_config = build_pipeline_config(params)

    for name, pop in params["new_pops"].items():
        if name in dataset.names:
            idx = dataset.names.index(name)
            dataset.poblacion[idx] = int(pop)

    st.divider()
    tab_flujo, tab_modulos = st.tabs(["🧭 Flujo guiado", "🧩 Análisis por módulos"])

    with tab_flujo:
        render_guided_flow_section(
            dataset=dataset,
            pipeline_config=pipeline_config,
            route_params=params,
        )

    with tab_modulos:
        route_center_options = list(ROUTABLE_CENTER_ORDER)
        selected_center_option = st.selectbox(
            "Alternativa operativa / centro de salida",
            options=route_center_options,
            index=0,
            format_func=guided_center_label,
            help=(
                "Estas alternativas usan nodos existentes en la matriz OD v2; "
                "no se usa depot virtual para los centros candidatos 0-3."
            ),
        )
        selected_operational_option = guided_route_center_to_operational_option(
            selected_center_option
        )
        st.session_state["center_option"] = selected_operational_option
        st.caption(
            "La alternativa elegida afecta al centro de salida y a la lectura económica. "
            "Rutas usa la matriz OD real ampliada; localización usa distancia geométrica homogénea."
        )

        (
            tab_vrp,
            tab_localizacion,
            tab_cronograma,
            tab_escenario,
            tab_laboratorio,
            tab_almacen,
            tab_economia,
            tab_riesgos,
        ) = st.tabs(
            [
                "📦 Asignación de rutas",
                "📍 Localización de centro",
                "🗓️ Cronograma",
                "📊 Escenario",
                "🧪 Laboratorio",
                "🏭 Almacén",
                "💶 Economía",
                "⚠️ Riesgos",
            ]
        )

        with tab_localizacion:
            view_location_selector(dataset)

        with tab_cronograma:
            render_timeline_section()

        with tab_escenario:
            render_scenario_section(
                pipeline_result=st.session_state.get("vrp_result"),
                center_option=selected_operational_option,
                route_params=st.session_state.get("last_route_params"),
            )

        with tab_laboratorio:
            render_scenario_tree_lab_section(
                dataset=dataset,
                pipeline_config=pipeline_config,
                route_params=params,
            )

        with tab_almacen:
            render_warehouse_section()

        with tab_vrp:
            st.markdown(
                "Esta pestaña calcula rutas aproximadas desde el centro seleccionado. "
                "Sirve para comparar configuraciones, no para reproducir una operación real."
            )
            with st.expander("Supuestos de esta pestaña", expanded=False):
                st.markdown(
                    "- La restricción principal es el tiempo efectivo de jornada.\n"
                    "- Las furgonetas eléctricas tienen además límite de autonomía.\n"
                    "- Las rutas dedicadas se separan cuando un municipio concentra mucha carga.\n"
                    "- La capacidad física de furgonetas no es un límite activo.\n"
                    "- La demanda se estima con población, calibración y estacionalidad."
                )

            run_col, status_col = st.columns([1, 4])
            run_button = run_col.button("Calcular rutas", type="primary", use_container_width=True)

            state_key = "vrp_result"
            try:
                dataset_for_run, operational_notes = _resolve_operational_dataset(
                    dataset,
                    selected_center_option,
                )
            except Exception as exc:
                st.error(f"No se pudo preparar la alternativa operativa: {exc}")
                st.stop()

            for note in operational_notes:
                st.info(note)

            signature = _pipeline_signature(params, selected_center_option, dataset_for_run)
            signature_key = "vrp_result_signature"
            should_run = (
                run_button
                or state_key not in st.session_state
                or st.session_state.get(signature_key) != signature
            )

            if should_run:
                with st.spinner("Calculando rutas..."):
                    try:
                        result = run_pipeline(dataset_for_run, pipeline_config)
                    except Exception as exc:
                        st.error(f"No se pudieron calcular rutas: {exc}")
                        st.stop()
                st.session_state[state_key] = result
                st.session_state[signature_key] = signature
                st.session_state["view"] = "main"
            else:
                result = st.session_state[state_key]

            target_caption = ""
            if params["target_daily_volume"] is not None:
                target_caption = f"Volumen objetivo: **{int(params['target_daily_volume']):,}** | "
            status_col.caption(
                f"Metodo: **{params['solver_strategy'].value}** | "
                f"Penetracion: **{params['market_pct']:.3f}%** | "
                f"Estacionalidad: **x{params['seasonality_multiplier']:.2f}** | "
                f"{target_caption}"
                f"Jornada: **{params['max_workday_hours']:.2f} h** efectiva | "
                f"Trailers: **{'ON' if params['trailer_enabled'] else 'OFF'}** | "
                f"Centro de salida: **{dataset_for_run.names[dataset_for_run.depot_index]}**"
            )

            view = st.session_state.get("view", "main")
            if view == "main":
                view_main(result, result.dataset)
            elif view == "vehicles":
                view_vehicles(result)
            elif view == "dedicated":
                view_dedicated(result)
            elif view == "shifts":
                view_shifts(result)
            elif view == "stops":
                view_stops(result)
            else:
                view_main(result, result.dataset)
            if result is not None:
                col_a, col_b = st.columns(2)
                with col_a:
                    st.download_button(
                        "Exportar rutas (CSV)",
                        data=serialize_vrp_routes_csv(result),
                        file_name="vrp_routes.csv",
                        mime="text/csv",
                    )
                with col_b:
                    st.download_button(
                        "Exportar resumen (JSON)",
                        data=serialize_vrp_summary_json(result),
                        file_name="vrp_summary.json",
                        mime="application/json",
                    )

        with tab_economia:
            render_economics_section(
                pipeline_result=st.session_state.get("vrp_result"),
                center_option=selected_operational_option,
            )

        with tab_riesgos:
            render_risk_section(
                pipeline_result=st.session_state.get("vrp_result"),
                center_option=selected_operational_option,
                route_params=st.session_state.get("last_route_params"),
            )
    
    # Footer informativo
    st.divider()
    col1, col2, col3 = st.columns(3)
    col1.caption("🏢 **Centro**: SVQ1, Sevilla")
    col2.caption("📊 **Versión**: 2.6 Flujo guiado + análisis por módulos")
    col3.caption("⚙️ **Motor**: herramientas de cálculo en Python (OR-Tools y SciPy)")


if __name__ == "__main__":
    main()
