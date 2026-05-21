"""Vistas Streamlit para los modelos integrados del proyecto Amazon.

Las pestañas de almacén y economía no muestran resultados fijos: llaman a
modelos Python parametrizables que reproducen la lógica de los scripts MATLAB
incluidos en ``codes/``.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from .data_loader import DEPOT_NAME, SECONDARY_HUB_NAME, VIRTUAL_DEPOT_NAME_PREFIX
from .demand import compute_packages
from .economics_model import (
    DEFAULT_OPTIONS,
    DEFAULT_RISKS,
    DEFAULT_DQA4_ATTRIBUTABLE_SHARE,
    AdditionalCostParams,
    CurrentCostParams,
    FinanceParams,
    InvestmentOption,
    OPERATIONAL_OPTION_CURRENT,
    OPERATIONAL_OPTION_INTERMEDIATE,
    OPERATIONAL_OPTION_SVQ1_EXPANDED,
    Risk,
    VehicleCostParams,
    additional_capex_opex,
    analyze_options,
    compute_economic_result,
    compute_economic_results,
    current_cost_frame,
    dqa4_current_cost,
    economic_results_frame,
    estimate_operational_cost_bridge,
    labor_cost_frame,
    labor_policy_result_from_additional,
    labor_risk_frame,
    recommend_option,
    risk_frame,
    total_current_cost,
    transfer_unit_cost,
    vehicle_cost_frame,
    vehicle_totals,
)
from .location_solver import LocationMethod, LocationSolver
from .pipeline import run_pipeline
from .risk_model import RiskDecisionInputs, assess_risks, risk_results_frame
from .scenario_comparator import (
    AUTO_NEW_LOCATION_VIRTUAL_WARNING,
    DEFAULT_MAX_TREE_SCENARIOS,
    LEGACY_INTERMEDIATE_BRIDGE_WARNING_PREFIX,
    SCENARIO_PRESET_BASIC,
    SCENARIO_PRESETS,
    TRANSITION_DIRECT,
    TRANSITION_PHASED,
    TREE_START_MONTHS,
    ScenarioComparisonConfig,
    ScenarioTreeConfig,
    ScenarioTreeResult,
    build_preset_scenario_configs,
    build_scenario_configs_from_tree,
    build_scenario_comparison,
    preliminary_viability,
    resolve_scenario_depot,
)
from .scenario_model import ScenarioConfig, build_scenario_result
from .timeline_model import MONTH_NAMES, build_timeline
from .warehouse_model import (
    ALMACEN_1FLOOR_DOORS,
    ALMACEN_3FLOOR_DOORS,
    ALMACEN_VS_DOORS,
    DimensionParams,
    Door,
    LayoutParams,
    assign_abc_global,
    category_summary,
    compute_dimension,
    floor_cost_summary,
    solve_layout,
    sweep_abc_layout,
)


def _section_title(text: str) -> None:
    st.markdown(f"<div class='section-title'>{text}</div>", unsafe_allow_html=True)


def _fmt_int(value: float) -> str:
    return f"{value:,.0f}".replace(",", ".")


def _fmt_num(value: float, decimals: int = 2) -> str:
    return f"{value:,.{decimals}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _fmt_money(value: float, decimals: int = 2) -> str:
    return f"{_fmt_num(value / 1e6, decimals)} M€"


def _fmt_years(value: float) -> str:
    return "∞" if np.isinf(value) else f"{_fmt_num(value, 2)} años"


def _fmt_pct(value: float) -> str:
    return "-" if pd.isna(value) else f"{value:.2%}".replace(".", ",")


def _money_df(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    out = df.copy()
    for col in columns:
        if col in out.columns:
            out[col] = out[col].apply(_fmt_money)
    return out


def _pct_df(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    out = df.copy()
    for col in columns:
        if col in out.columns:
            out[col] = out[col].apply(lambda x: f"{x:.1%}" if pd.notna(x) else "-")
    return out


def _yes_no(value: bool) -> str:
    return "Sí" if value else "No"


def _is_virtual_depot_name(depot_name: str | None) -> bool:
    return bool(depot_name) and str(depot_name).startswith(VIRTUAL_DEPOT_NAME_PREFIX)


def _filter_display_warnings(
    warnings: tuple[str, ...],
    center_option: str,
) -> tuple[str, ...]:
    if center_option != OPERATIONAL_OPTION_INTERMEDIATE:
        return warnings
    return tuple(
        warning
        for warning in warnings
        if not warning.startswith(LEGACY_INTERMEDIATE_BRIDGE_WARNING_PREFIX)
    )


def _timeline_months_frame(result) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Mes proyecto": month.project_month,
                "Mes calendario": month.calendar_month,
                "Nombre": month.month_name,
                "Fase": month.phase,
                "Multiplicador": f"x{month.multiplier:.2f}",
                "Nivel estacional": month.risk_level,
                "Temporada alta": _yes_no(month.in_high_season),
            }
            for month in result.months
        ]
    )


def _timeline_milestones_frame(result) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Hito": milestone.name,
                "Mes proyecto": milestone.project_month,
                "Mes calendario": milestone.calendar_month,
                "Nombre": milestone.month_name,
                "Multiplicador": f"x{milestone.multiplier:.2f}",
                "Nivel estacional": milestone.risk_level,
                "Temporada alta": _yes_no(milestone.in_high_season),
            }
            for milestone in result.milestones
        ]
    )


def _timeline_warnings_frame(result) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Código": warning.code,
                "Severidad": warning.severity,
                "Mensaje": _friendly_timeline_warning(warning.message),
            }
            for warning in result.warnings
        ]
    )


def _friendly_timeline_warning(message: str) -> str:
    return message.replace("cierre de DQA4", "cierre de la transición")


def render_timeline_section() -> None:
    """Renderiza el cronograma estacional de transicion."""
    st.markdown(
        "Este bloque muestra cómo una transición estándar de 17 meses se cruza con meses "
        "de baja, normal y alta demanda. Usa meses discretos; no es un calendario real."
    )
    st.caption(
        "Este bloque solo avisa si fases o hitos caen en meses de mucha demanda. "
        "No decide por sí solo si el proyecto es viable."
    )

    c1, c2 = st.columns([1, 3])
    start_month = c1.selectbox(
        "Mes de inicio",
        options=list(MONTH_NAMES.keys()),
        index=0,
        format_func=lambda value: MONTH_NAMES[value],
        key="timeline_start_month",
        help="Mes calendario en el que arranca la fase de preparación.",
    )
    result = build_timeline(int(start_month))
    c2.info(result.summary)
    st.caption("Octubre-diciembre es el pico de demanda; conviene evitar cambios críticos en esos meses.")

    _section_title("Lectura rápida")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Duración total", f"{result.total_duration_months} meses")
    c2.metric("Temporada alta", f"{result.high_season_month_count} meses")
    c3.metric("Alertas altas", result.high_severity_warning_count)
    c4.metric("Mes alternativo", result.suggested_start_month_name or "Sin mejora clara")
    st.caption("El mes alternativo sugiere un inicio con menos meses críticos, si existe.")

    if result.high_severity_warning_count:
        st.warning(
            "Hay fases o hitos en meses de mayor demanda. Úsalo como alerta, no como decisión final."
        )
    else:
        st.success("No hay alertas de severidad alta con las reglas actuales.")

    _section_title("Cronograma mensual")
    st.dataframe(_timeline_months_frame(result), hide_index=True, use_container_width=True)

    _section_title("Hitos críticos")
    st.dataframe(_timeline_milestones_frame(result), hide_index=True, use_container_width=True)

    with st.expander("Alertas y notas del cronograma", expanded=True):
        st.dataframe(_timeline_warnings_frame(result), hide_index=True, use_container_width=True)


def _abc_heatmap(matrix: np.ndarray, title: str, doors: tuple[Door, ...] = ()) -> go.Figure:
    colorscale = [
        [0.00, "#38a169"],
        [0.32, "#38a169"],
        [0.33, "#f6c343"],
        [0.65, "#f6c343"],
        [0.66, "#d95f5f"],
        [1.00, "#d95f5f"],
    ]
    fig = go.Figure(
        data=go.Heatmap(
            z=matrix,
            x=list(range(1, matrix.shape[1] + 1)),
            y=list(range(1, matrix.shape[0] + 1)),
            zmin=1,
            zmax=3,
            colorscale=colorscale,
            colorbar=dict(tickvals=[1, 2, 3], ticktext=["A", "B", "C"]),
            hovertemplate="Fila %{y}<br>Columna %{x}<br>Zona %{z}<extra></extra>",
        )
    )
    if doors:
        fig.add_trace(
            go.Scatter(
                x=[d.col for d in doors],
                y=[d.row for d in doors],
                mode="markers+text",
                marker=dict(symbol="x", size=12, color="black", line=dict(width=2)),
                text=[f"P{i}" for i, _ in enumerate(doors, start=1)],
                textposition="middle right",
                name="Puertas",
            )
        )
    fig.update_layout(title=title, height=430, margin=dict(l=10, r=10, t=45, b=10))
    fig.update_yaxes(autorange="reversed", title="Filas")
    fig.update_xaxes(title="Columnas", constrain="domain")
    return fig


def _f_heatmap(matrix: np.ndarray, title: str, doors: tuple[Door, ...] = ()) -> go.Figure:
    fig = go.Figure(
        data=go.Heatmap(
            z=matrix,
            x=list(range(1, matrix.shape[1] + 1)),
            y=list(range(1, matrix.shape[0] + 1)),
            colorscale="Turbo",
            colorbar=dict(title="Índice f"),
            hovertemplate="Fila %{y}<br>Columna %{x}<br>f=%{z:.2f}<extra></extra>",
        )
    )
    if doors:
        fig.add_trace(
            go.Scatter(
                x=[d.col for d in doors],
                y=[d.row for d in doors],
                mode="markers+text",
                marker=dict(symbol="x", size=12, color="white", line=dict(width=2)),
                text=[f"P{i}" for i, _ in enumerate(doors, start=1)],
                textposition="middle right",
                name="Puertas",
            )
        )
    fig.update_layout(title=title, height=430, margin=dict(l=10, r=10, t=45, b=10))
    fig.update_yaxes(autorange="reversed", title="Filas")
    fig.update_xaxes(title="Columnas", constrain="domain")
    return fig


def _bar_chart(df: pd.DataFrame, x: str, y: list[str], title: str) -> go.Figure:
    fig = go.Figure()
    for col in y:
        fig.add_trace(go.Bar(x=df[x], y=df[col], name=col))
    fig.update_layout(title=title, barmode="group", height=390, margin=dict(l=10, r=10, t=45, b=10))
    return fig


def _dimension_controls() -> DimensionParams:
    with st.expander("Parámetros de dimensionamiento", expanded=False):
        st.caption(
            "Ajustes físicos del almacén. Mantén los defaults para leer la capacidad base; "
            "edítalos solo para sensibilidad."
        )
        c1, c2, c3 = st.columns(3)
        building_length = c1.number_input("Largo edificio (m)", 50.0, 1_000.0, 300.0, 10.0)
        building_width = c2.number_input("Ancho edificio (m)", 50.0, 1_000.0, 150.0, 10.0)
        floors = c3.number_input("Plantas", 1, 10, 3, 1)

        c1, c2, c3 = st.columns(3)
        robotics_length = c1.number_input("Largo Robotics Area (m)", 10.0, 1_000.0, 210.0, 5.0)
        robotics_width = c2.number_input("Ancho Robotics Area (m)", 10.0, 1_000.0, 95.0, 5.0)
        use_override = c3.checkbox("Forzar área robotizada redondeada", value=True)
        robotics_override = (
            c3.number_input("Área robotizada usada (m²)", 1_000.0, 500_000.0, 20_000.0, 500.0)
            if use_override
            else None
        )

        c1, c2, c3, c4 = st.columns(4)
        shelf_length = c1.number_input("Largo estantería (m)", 0.5, 10.0, 1.5, 0.1)
        shelf_width = c2.number_input("Ancho estantería (m)", 0.5, 10.0, 1.5, 0.1)
        useful_area = c3.slider("Área útil (%)", 5.0, 100.0, 50.0, 1.0) / 100.0
        occupancy = c4.slider("Ocupación real (%)", 1.0, 100.0, 67.0, 1.0) / 100.0

        c1, c2, c3 = st.columns(3)
        use_shelves_override = c1.checkbox("Forzar estanterías/planta", value=True)
        shelves_override = (
            c1.number_input("Estanterías de diseño/planta", 1, 100_000, 5_000, 100)
            if use_shelves_override
            else None
        )
        packages_per_slot = c2.number_input("Paquetes por hueco", 1, 200, 12, 1)
        c3.caption("Huecos = a*b*c + d*e")
        slot_a = c3.number_input("a", 1, 50, 7, 1, key="slot_a")
        slot_b = c3.number_input("b", 1, 50, 3, 1, key="slot_b")
        slot_c = c3.number_input("c", 1, 50, 2, 1, key="slot_c")
        slot_d = c3.number_input("d", 1, 50, 7, 1, key="slot_d")
        slot_e = c3.number_input("e", 1, 50, 2, 1, key="slot_e")

        c1, c2 = st.columns(2)
        pct_a = c1.slider("Inventario zona A (%)", 0.0, 90.0, 15.0, 1.0) / 100.0
        max_b = max(0.0, 100.0 - pct_a * 100.0)
        pct_b = c2.slider("Inventario zona B (%)", 0.0, max_b, min(15.0, max_b), 1.0) / 100.0

    return DimensionParams(
        building_length_m=building_length,
        building_width_m=building_width,
        robotics_length_m=robotics_length,
        robotics_width_m=robotics_width,
        robotics_area_override_m2=robotics_override,
        shelf_length_m=shelf_length,
        shelf_width_m=shelf_width,
        useful_area_pct=useful_area,
        shelves_per_floor_override=shelves_override,
        shelf_slots_main_a=slot_a,
        shelf_slots_main_b=slot_b,
        shelf_slots_main_c=slot_c,
        shelf_slots_extra_a=slot_d,
        shelf_slots_extra_b=slot_e,
        packages_per_slot=packages_per_slot,
        occupancy_pct=occupancy,
        floors=floors,
        pct_a=pct_a,
        pct_b=pct_b,
    )


def _layout_controls(prefix: str) -> LayoutParams:
    with st.expander("Parámetros del método f", expanded=False):
        st.caption(
            "El índice f aproxima el coste de mover productos desde puertas y plantas. "
            "Los parámetros detallados quedan aquí para experimentar con el layout."
        )
        presets = {
            "Almacen_3floor.m - layout 3D con cinta": ("3floor", 3, ALMACEN_3FLOOR_DOORS),
            "Almacen_1floor.m - una planta": ("1floor", 1, ALMACEN_1FLOOR_DOORS),
        }
        preset_label = st.selectbox(
            "Preset del script MATLAB",
            list(presets.keys()),
            index=0,
            key=f"{prefix}_preset",
        )
        preset_key, default_floors, preset_doors = presets[preset_label]

        c1, c2, c3 = st.columns(3)
        rows = c1.number_input("Filas", 5, 250, 50, 5, key=f"{prefix}_{preset_key}_rows")
        cols = c2.number_input("Columnas", 5, 250, 100, 5, key=f"{prefix}_{preset_key}_cols")
        floors = c3.number_input(
            "Plantas layout",
            1,
            8,
            default_floors,
            1,
            key=f"{prefix}_{preset_key}_floors",
        )

        c1, c2, c3, c4 = st.columns(4)
        pct_a = c1.slider("Zona A inventario (%)", 0.0, 90.0, 15.0, 1.0, key=f"{prefix}_{preset_key}_pct_a") / 100.0
        max_pct_b = max(0.0, 100.0 - pct_a * 100.0)
        pct_b = c2.slider("Zona B inventario (%)", 0.0, max_pct_b, min(15.0, max_pct_b), 1.0, key=f"{prefix}_{preset_key}_pct_b") / 100.0
        move_a = c3.slider("Movimientos A (%)", 0.0, 100.0, 80.0, 1.0, key=f"{prefix}_{preset_key}_move_a") / 100.0
        max_move_b = max(0.0, 100.0 - move_a * 100.0)
        move_b = c4.slider("Movimientos B (%)", 0.0, max_move_b, min(15.0, max_move_b), 1.0, key=f"{prefix}_{preset_key}_move_b") / 100.0

        c1, c2, c3 = st.columns(3)
        cell_size = c1.number_input("Tamaño celda (m)", 0.1, 20.0, 1.5, 0.1, key=f"{prefix}_{preset_key}_cell_size")
        conveyor_speed = c2.number_input("Velocidad cinta (m/s)", 0.1, 10.0, 1.2, 0.1, key=f"{prefix}_{preset_key}_conveyor_speed")
        seconds_per_floor = c3.number_input("Tiempo por planta (s)", 0.0, 300.0, 15.0, 1.0, key=f"{prefix}_{preset_key}_seconds_per_floor")

        st.markdown("**Puertas / puntos de entrada-salida**")
        c1, c2 = st.columns([1, 3])
        door_count = c1.number_input("Número de puertas", 1, 6, len(preset_doors), 1, key=f"{prefix}_{preset_key}_door_count")
        normalize = c1.checkbox("Normalizar pesos", value=True, key=f"{prefix}_{preset_key}_normalize")
        doors: list[Door] = []
        default_doors = [
            (min(d.row, rows), min(d.col, cols), d.weight)
            for d in preset_doors
        ]
        for idx in range(door_count):
            drow, dcol, dweight = default_doors[idx] if idx < len(default_doors) else (rows, cols, 1.0 / door_count)
            cc1, cc2, cc3 = c2.columns(3)
            row = cc1.number_input(f"Fila P{idx + 1}", 1, rows, int(min(drow, rows)), 1, key=f"{prefix}_{preset_key}_door_row_{idx}")
            col = cc2.number_input(f"Columna P{idx + 1}", 1, cols, int(min(dcol, cols)), 1, key=f"{prefix}_{preset_key}_door_col_{idx}")
            weight = cc3.number_input(f"Peso P{idx + 1}", 0.0, 1.0, float(dweight), 0.05, key=f"{prefix}_{preset_key}_door_weight_{idx}")
            doors.append(Door(row=row, col=col, weight=weight))

    return LayoutParams(
        rows=rows,
        cols=cols,
        floors=floors,
        doors=tuple(doors),
        pct_a=pct_a,
        pct_b=pct_b,
        move_a=move_a,
        move_b=move_b,
        cell_size_m=cell_size,
        conveyor_speed_m_s=conveyor_speed,
        seconds_per_floor=seconds_per_floor,
        normalize_door_weights=normalize,
    )


def _vs_controls(prefix: str) -> LayoutParams:
    with st.expander("Parámetros de comparación ABC (`Almacen_vs.m`)", expanded=False):
        st.caption(
            "Usa estos controles para sensibilidad. La comparación principal está en los costes resultantes."
        )
        c1, c2, c3 = st.columns(3)
        rows = c1.number_input("Filas", 5, 250, 50, 5, key=f"{prefix}_rows")
        cols = c2.number_input("Columnas", 5, 250, 100, 5, key=f"{prefix}_cols")
        floors = c3.number_input("Plantas", 2, 8, 3, 1, key=f"{prefix}_floors")

        c1, c2, c3, c4 = st.columns(4)
        pct_a = c1.slider("Inventario A (%)", 0.0, 90.0, 15.0, 1.0, key=f"{prefix}_pct_a") / 100.0
        max_pct_b = max(0.0, 100.0 - pct_a * 100.0)
        pct_b = c2.slider("Inventario B (%)", 0.0, max_pct_b, min(15.0, max_pct_b), 1.0, key=f"{prefix}_pct_b") / 100.0
        move_a = c3.slider("Movimientos A (%)", 0.0, 100.0, 80.0, 1.0, key=f"{prefix}_move_a") / 100.0
        max_move_b = max(0.0, 100.0 - move_a * 100.0)
        move_b = c4.slider("Movimientos B (%)", 0.0, max_move_b, min(15.0, max_move_b), 1.0, key=f"{prefix}_move_b") / 100.0

        c1, c2, c3 = st.columns(3)
        cell_size = c1.number_input("Tamaño celda (m)", 0.1, 20.0, 1.5, 0.1, key=f"{prefix}_cell_size")
        conveyor_speed = c2.number_input("Velocidad cinta (m/s)", 0.1, 10.0, 1.2, 0.1, key=f"{prefix}_conveyor_speed")
        seconds_per_floor = c3.number_input("Tiempo por planta (s)", 0.0, 300.0, 15.0, 1.0, key=f"{prefix}_seconds")

        st.markdown("**Puertas del script de comparación**")
        doors: list[Door] = []
        for idx, default in enumerate(ALMACEN_VS_DOORS):
            cc1, cc2, cc3 = st.columns(3)
            row = cc1.number_input(
                f"Fila P{idx + 1}",
                1,
                rows,
                int(min(default.row, rows)),
                1,
                key=f"{prefix}_door_row_{idx}",
            )
            col = cc2.number_input(
                f"Columna P{idx + 1}",
                1,
                cols,
                int(min(default.col, cols)),
                1,
                key=f"{prefix}_door_col_{idx}",
            )
            weight = cc3.number_input(
                f"Peso P{idx + 1}",
                0.0,
                1.0,
                float(default.weight),
                0.05,
                key=f"{prefix}_door_weight_{idx}",
            )
            doors.append(Door(row=row, col=col, weight=weight))
        normalize = st.checkbox("Normalizar pesos de puertas", value=True, key=f"{prefix}_normalize")

    return LayoutParams(
        rows=rows,
        cols=cols,
        floors=floors,
        doors=tuple(doors),
        pct_a=pct_a,
        pct_b=pct_b,
        move_a=move_a,
        move_b=move_b,
        cell_size_m=cell_size,
        conveyor_speed_m_s=conveyor_speed,
        seconds_per_floor=seconds_per_floor,
        normalize_door_weights=normalize,
    )


def render_warehouse_section() -> None:
    """Renderiza la herramienta paramétrica de almacén y layout."""
    st.markdown(
        "Esta pestaña ayuda a dimensionar y ordenar el almacén por dentro. "
        "Es una aproximación de diseño, no el plano definitivo de un centro unificado."
    )
    st.caption(
        "Los modelos sirven para leer capacidad, zonas ABC y recorridos internos; "
        "el diseño final se definiría más adelante."
    )
    with st.expander("Supuestos del bloque de almacén", expanded=False):
        st.markdown(
            "- El dimensionamiento traduce área, estanterías y ocupación en capacidad aproximada.\n"
            "- El layout ABC acerca las zonas de mayor movimiento para reducir recorridos.\n"
            "- El indicador f aproxima el esfuerzo interno por distancia a puertas y plantas.\n"
            "- La mejora indica menos recorrido interno bajo estos supuestos."
        )
    tab_dimension, tab_layout, tab_vs, tab_sensitivity = st.tabs(
        ["Dimensionamiento", "Layout ABC", "Comparación ABC", "Sensibilidad ABC"]
    )

    with tab_dimension:
        st.caption(
            "Responde si el almacén tiene capacidad suficiente bajo los supuestos físicos definidos."
        )
        params = _dimension_controls()
        result = compute_dimension(params)
        _section_title("Resultado de capacidad")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Capacidad total", _fmt_int(result.total_capacity))
        c2.metric("Capacidad/planta", _fmt_int(result.capacity_per_floor))
        c3.metric("Estanterías/planta", _fmt_int(result.shelves_per_floor))
        c4.metric("Huecos/estantería", _fmt_int(result.slots_per_shelf))

        st.dataframe(result.metrics_frame(), hide_index=True, use_container_width=True)
        st.caption("La tabla desglosa de dónde sale la capacidad: área útil, estanterías, huecos y ocupación.")

        abc = result.abc_frame()
        abc["Paquetes"] = abc["Paquetes"].apply(_fmt_int)
        st.dataframe(abc, hide_index=True, use_container_width=True)
        st.caption("El reparto ABC divide la capacidad por importancia operativa de inventario.")

    with tab_layout:
        st.caption(
            "Compara cómo se distribuyen las zonas A/B/C dentro del edificio para reducir recorridos internos."
        )
        params = _layout_controls("layout")
        layout = solve_layout(params)
        _section_title("Resultado del layout")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Coste ABC global", _fmt_num(layout.cost_global, 2))
        c2.metric("Penalización/planta", f"{layout.vertical_penalty_cells:.2f} celdas")
        c3.metric("Inventario C", f"{params.pct_c:.1%}")
        c4.metric("Movimientos C", f"{params.move_c:.1%}")
        st.caption(
            "Menor coste ABC global indica una asignación con menor esfuerzo ponderado de movimiento."
        )

        floor_summary = floor_cost_summary(layout)
        numeric_cols = ["Penalización vertical (celdas)", "Penalización vertical (m)", "f mínimo", "f medio", "f máximo"]
        floor_display = floor_summary.copy()
        for col in numeric_cols:
            floor_display[col] = floor_display[col].apply(lambda x: _fmt_num(float(x), 2))
        st.dataframe(floor_display, hide_index=True, use_container_width=True)
        st.caption("La tabla muestra cómo la penalización vertical hace más caras las plantas superiores.")

        strategy = st.radio(
            "Zonificación a visualizar",
            ["ABC global 3D", "ABC por planta"],
            horizontal=True,
            help="ABC global ordena todo el edificio junto; ABC por planta reserva A/B/C dentro de cada planta.",
        )
        abc_matrix = layout.abc_global if strategy == "ABC global 3D" else layout.abc_by_floor

        _section_title("Visualización completa por planta")
        if abc_matrix.ndim == 3:
            for floor_idx in range(abc_matrix.shape[2]):
                floor_number = floor_idx + 1
                st.markdown(f"**Planta {floor_number}**")
                left, right = st.columns(2)
                left.plotly_chart(
                    _abc_heatmap(
                        abc_matrix[:, :, floor_idx],
                        f"Zonificación {strategy} - planta {floor_number}",
                        params.doors,
                    ),
                    use_container_width=True,
                )
                right.plotly_chart(
                    _f_heatmap(
                        layout.f_matrix[:, :, floor_idx],
                        f"Mapa de índice f - planta {floor_number}",
                        params.doors,
                    ),
                    use_container_width=True,
                )
        else:
            left, right = st.columns(2)
            left.plotly_chart(
                _abc_heatmap(abc_matrix, f"Zonificación {strategy} - planta única", params.doors),
                use_container_width=True,
            )
            right.plotly_chart(
                _f_heatmap(layout.f_matrix, "Mapa de índice f - planta única", params.doors),
                use_container_width=True,
            )

        summary = category_summary(abc_matrix)
        st.dataframe(summary, hide_index=True, use_container_width=True)
        st.caption("Cuenta cuántas celdas quedan en cada zona ABC por planta.")

    with tab_vs:
        st.caption(
            "Esta comparación separa dos formas de asignar ABC: por planta o global en todo el edificio."
        )
        params = _vs_controls("vs")
        layout = solve_layout(params)
        _section_title("ABC individual por planta vs ABC global 3D")
        st.markdown(
            "Compara dos reglas de asignación sobre el mismo edificio: una reparte "
            "A/B/C en cada planta y la otra ordena todo el edificio para concentrar "
            "las zonas de mayor movimiento en posiciones más favorables."
        )

        c1, c2, c3 = st.columns(3)
        c1.metric("Coste ABC por planta", _fmt_num(layout.cost_by_floor, 2))
        c2.metric("Coste ABC global 3D", _fmt_num(layout.cost_global, 2))
        c3.metric("Mejora global", f"{layout.improvement_pct:.2f}%")
        st.caption(
            "Si el coste global baja, el modelo está concentrando zonas de mayor movimiento en posiciones más favorables."
        )

        comparison_df = pd.DataFrame(
            {
                "Estrategia": ["ABC por planta", "ABC global 3D"],
                "Coste logístico diario": [layout.cost_by_floor, layout.cost_global],
            }
        )
        fig = go.Figure(
            data=go.Bar(
                x=comparison_df["Estrategia"],
                y=comparison_df["Coste logístico diario"],
                marker_color=["#d95f5f", "#38a169"],
                text=[_fmt_num(v, 2) for v in comparison_df["Coste logístico diario"]],
                textposition="outside",
            )
        )
        fig.update_layout(
            title="Comparación de coste ponderado",
            yaxis_title="Índice de coste logístico diario",
            height=390,
            margin=dict(l=10, r=10, t=45, b=10),
        )
        st.plotly_chart(fig, use_container_width=True)

        floor_display = floor_cost_summary(layout)
        for col in ["Penalización vertical (celdas)", "Penalización vertical (m)", "f mínimo", "f medio", "f máximo"]:
            floor_display[col] = floor_display[col].apply(lambda x: _fmt_num(float(x), 2))
        st.dataframe(floor_display, hide_index=True, use_container_width=True)

        st.markdown(
            "La lectura correcta es comparar los dos costes agregados. La tabla "
            "por planta explica de dónde sale la mejora: el ABC global suele "
            "concentrar la zona A en posiciones más cercanas a puertas y plantas "
            "inferiores, reduciendo recorridos internos."
        )

    with tab_sensitivity:
        st.caption(
            "Explora cómo cambia la mejora ABC al variar inventario y movimientos de la zona A."
        )
        params = _vs_controls("sensitivity")
        _section_title("Barrido paramétrico")
        c1, c2, c3, c4 = st.columns(4)
        pct_a_min = c1.slider("A mín. inventario (%)", 1.0, 50.0, 5.0, 1.0) / 100.0
        pct_a_max = c2.slider("A máx. inventario (%)", 1.0, 60.0, 30.0, 1.0) / 100.0
        move_a_min = c3.slider("A mín. movimientos (%)", 1.0, 99.0, 70.0, 1.0) / 100.0
        move_a_max = c4.slider("A máx. movimientos (%)", 1.0, 99.0, 85.0, 1.0) / 100.0
        c1, c2 = st.columns(2)
        pct_steps = c1.number_input("Puntos de inventario A", 2, 25, 6, 1)
        move_steps = c2.number_input("Puntos de movimientos A", 2, 25, 4, 1)

        pct_values = np.linspace(min(pct_a_min, pct_a_max), max(pct_a_min, pct_a_max), pct_steps)
        move_values = np.linspace(min(move_a_min, move_a_max), max(move_a_min, move_a_max), move_steps)
        sweep = sweep_abc_layout(params, pct_values, move_values)
        best_by_floor = sweep.loc[sweep["coste_por_planta"].idxmin()]
        best_global = sweep.loc[sweep["coste_global"].idxmin()]
        best_improvement = sweep.loc[sweep["mejora_pct"].idxmax()]

        c1, c2, c3 = st.columns(3)
        c1.metric("Menor coste por planta", _fmt_num(best_by_floor["coste_por_planta"], 2), f"A={best_by_floor['pct_A']:.0%}, mov A={best_by_floor['mov_A']:.0%}")
        c2.metric("Menor coste global", _fmt_num(best_global["coste_global"], 2), f"A={best_global['pct_A']:.0%}, mov A={best_global['mov_A']:.0%}")
        c3.metric("Mayor mejora", f"{best_improvement['mejora_pct']:.2f}%", f"A={best_improvement['pct_A']:.0%}, mov A={best_improvement['mov_A']:.0%}")

        display = sweep.copy()
        for col in ["pct_A", "pct_B", "pct_C", "mov_A", "mov_B", "mov_C"]:
            display[col] = display[col].apply(lambda x: f"{x:.1%}")
        st.dataframe(display.sort_values("coste_global"), hide_index=True, use_container_width=True)
        st.caption("Ordena los escenarios para detectar qué combinación reduce más el coste global.")

        pivot = sweep.pivot_table(index="pct_A", columns="mov_A", values="mejora_pct")
        fig = go.Figure(
            data=go.Heatmap(
                z=pivot.values,
                x=[f"{x:.0%}" for x in pivot.columns],
                y=[f"{y:.0%}" for y in pivot.index],
                colorscale="Viridis",
                colorbar=dict(title="Mejora %"),
            )
        )
        fig.update_layout(
            title="Mejora del ABC global frente al ABC por planta",
            xaxis_title="Movimientos A",
            yaxis_title="Inventario A",
            height=420,
        )
        st.plotly_chart(fig, use_container_width=True)


def _current_cost_controls() -> CurrentCostParams:
    with st.expander("Costes actuales y volúmenes", expanded=True):
        st.caption(
            "Permite modificar el as-is del caso para sensibilidad; en la vista normal estos datos se muestran solo como referencia."
        )
        c1, c2, c3 = st.columns(3)
        personal_svq1 = c1.number_input(
            "Personal SVQ1 (M€/año)",
            0.0,
            100.0,
            20.7,
            0.1,
            help="Coste anual de personal de SVQ1 usado como base del caso.",
        ) * 1e6
        personal_dqa4 = c1.number_input(
            "Personal DQA4 (M€/año)",
            0.0,
            100.0,
            9.1,
            0.1,
            help="Coste anual de personal de DQA4 usado como base del caso.",
        ) * 1e6
        energy_svq1 = c2.number_input(
            "Energía SVQ1 (M€/año)",
            0.0,
            100.0,
            6.2,
            0.1,
            help="Coste anual de energía y combustible asignado a SVQ1.",
        ) * 1e6
        energy_dqa4 = c2.number_input(
            "Energía DQA4 (M€/año)",
            0.0,
            100.0,
            4.7,
            0.1,
            help="Coste anual de energía y combustible asignado a DQA4.",
        ) * 1e6
        facilities_svq1 = c3.number_input(
            "Instalaciones SVQ1 (M€/año)",
            0.0,
            100.0,
            2.4,
            0.1,
            help="Coste anual de instalaciones de SVQ1.",
        ) * 1e6
        facilities_dqa4 = c3.number_input(
            "Instalaciones DQA4 (M€/año)",
            0.0,
            100.0,
            1.5,
            0.1,
            help="Coste anual de instalaciones de DQA4.",
        ) * 1e6

        c1, c2, c3 = st.columns(3)
        other_svq1 = c1.number_input(
            "Otros SVQ1 (M€/año)",
            0.0,
            100.0,
            7.0,
            0.1,
            help="Otros gastos operativos anuales de SVQ1.",
        ) * 1e6
        other_dqa4 = c1.number_input(
            "Otros DQA4 (M€/año)",
            0.0,
            100.0,
            2.8,
            0.1,
            help="Otros gastos operativos anuales de DQA4.",
        ) * 1e6
        transfer_cost = c2.number_input(
            "Coste transferencias (M€/año)",
            0.0,
            50.0,
            1.99,
            0.01,
            help="Coste anual de mover paquetes entre SVQ1 y DQA4.",
        ) * 1e6
        transfer_daily = c2.number_input(
            "Paquetes transferidos/día",
            0,
            200_000,
            26_100,
            100,
            help="Volumen diario que viaja desde SVQ1 hasta DQA4.",
        )
        transfer_distance = c3.number_input(
            "Distancia SVQ1-DQA4 (km)",
            0.0,
            200.0,
            25.0,
            1.0,
            help="Distancia usada para contextualizar la transferencia entre centros.",
        )
        days = c3.number_input(
            "Días/año",
            1,
            366,
            365,
            1,
            help="Días anuales considerados para calcular el coste por paquete transferido.",
        )
    return CurrentCostParams(
        personal_svq1=personal_svq1,
        personal_dqa4=personal_dqa4,
        energy_svq1=energy_svq1,
        energy_dqa4=energy_dqa4,
        facilities_svq1=facilities_svq1,
        facilities_dqa4=facilities_dqa4,
        other_svq1=other_svq1,
        other_dqa4=other_dqa4,
        transfer_annual_cost=transfer_cost,
        transfer_daily_packages=transfer_daily,
        transfer_distance_km=transfer_distance,
        days_per_year=days,
    )


def _investment_controls(prefix: str) -> tuple[list[InvestmentOption], AdditionalCostParams, FinanceParams]:
    with st.expander("Opciones de inversión", expanded=True):
        st.caption(
            "Edita CAPEX, ahorros y robots de cada alternativa para pruebas de sensibilidad."
        )
        options: list[InvestmentOption] = []
        for default in DEFAULT_OPTIONS:
            st.markdown(f"**{default.name}**")
            c1, c2, c3, c4 = st.columns(4)
            opt_key = f"{prefix}_{default.name}"
            capex = c1.number_input(
                f"CAPEX base {default.name} (M€)",
                0.0,
                200.0,
                default.capex_base / 1e6,
                0.1,
                key=f"{opt_key}_capex",
                help="Inversión inicial de la alternativa antes de costes de transición.",
            ) * 1e6
            infra = c2.number_input(
                f"Infra {default.name} (M€)",
                0.0,
                200.0,
                default.capex_infra / 1e6,
                0.1,
                key=f"{opt_key}_infra",
                help="Parte informativa asociada a expansión física e infraestructura.",
            ) * 1e6
            tech = c3.number_input(
                f"Tech {default.name} (M€)",
                0.0,
                200.0,
                default.capex_tech / 1e6,
                0.1,
                key=f"{opt_key}_tech",
                help="Parte informativa asociada a tecnología y robótica.",
            ) * 1e6
            it = c4.number_input(
                f"IT {default.name} (M€)",
                0.0,
                200.0,
                default.capex_it / 1e6,
                0.1,
                key=f"{opt_key}_it",
                help="Parte informativa asociada a integración de sistemas.",
            ) * 1e6
            c1, c2 = st.columns(2)
            savings = c1.number_input(
                f"Ahorro bruto {default.name} (M€/año)",
                0.0,
                100.0,
                default.gross_savings / 1e6,
                0.1,
                key=f"{opt_key}_savings",
                help="Ahorro anual antes de descontar nuevos costes recurrentes.",
            ) * 1e6
            robots = c2.number_input(
                f"Robots {default.name}",
                0,
                5_000,
                int(default.robots_total or 0),
                10,
                key=f"{opt_key}_robots",
                help="Robots totales asociados a la alternativa cuando el dato existe.",
            )
            options.append(
                InvestmentOption(
                    name=default.name,
                    capex_base=capex,
                    capex_infra=infra,
                    capex_tech=tech,
                    capex_it=it,
                    gross_savings=savings,
                    robots_total=robots or None,
                )
            )

    with st.expander("Costes adicionales y horizonte", expanded=True):
        st.caption(
            "Define qué costes de transición y parámetros financieros entran en el resultado."
        )
        c1, c2, c3 = st.columns(3)
        training = c1.number_input(
            "Formación (M€ CAPEX)",
            0.0,
            50.0,
            1.56,
            0.01,
            key=f"{prefix}_training",
            help="Coste único de formación incluido como transición.",
        ) * 1e6
        phasing = c2.number_input(
            "Implementación por fases (M€ CAPEX)",
            0.0,
            50.0,
            2.20,
            0.01,
            key=f"{prefix}_phasing",
            help="Coste de mitigación por hacer la transición progresiva.",
        ) * 1e6
        backup = c3.number_input(
            "Sistemas respaldo (M€ CAPEX)",
            0.0,
            50.0,
            1.80,
            0.01,
            key=f"{prefix}_backup",
            help="Coste de mitigación para continuidad tecnológica y operativa.",
        ) * 1e6
        c1, c2, c3 = st.columns(3)
        incentives = c1.number_input(
            "Incentivos empleados (M€)",
            0.0,
            50.0,
            0.68,
            0.01,
            key=f"{prefix}_incentives",
            help="Coste total de incentivos, repartido entre bono inicial y permanencia.",
        ) * 1e6
        incentive_capex_share = c2.slider(
            "% incentivos como CAPEX",
            0.0,
            100.0,
            50.0,
            5.0,
            key=f"{prefix}_incentive_share",
            help="Porcentaje de incentivos tratado como coste único de transición.",
        ) / 100.0
        insurance = c3.number_input(
            "Seguros especiales (M€/año)",
            0.0,
            50.0,
            0.45,
            0.01,
            key=f"{prefix}_insurance",
            help="Coste recurrente anual de coberturas especiales de riesgo.",
        ) * 1e6

        c1, c2, c3 = st.columns(3)
        support = c1.selectbox(
            "Apoyo empleados DQA4",
            ["Subsidio transporte público", "Transporte corporativo", "Compensación única", "Sin apoyo"],
            key=f"{prefix}_support",
            help="Política de apoyo para los empleados de DQA4 afectados por el traslado.",
        )
        include_regulation = c2.checkbox(
            "Tratar regulación 2025 como incremental",
            value=False,
            key=f"{prefix}_include_reg",
            help="Añade la regulación laboral 2025 como coste anual incremental del proyecto.",
        )
        regulation = c3.number_input(
            "Regulación 2025 (M€/año)",
            0.0,
            50.0,
            3.25,
            0.01,
            key=f"{prefix}_regulation",
            help="Coste anual asociado a la regulación laboral si se trata como incremental.",
        )
        regulation *= 1e6

        c1, c2, c3 = st.columns(3)
        discount_rate = c1.slider(
            "Tasa descuento (%)",
            0.0,
            25.0,
            7.0,
            0.25,
            key=f"{prefix}_discount",
            help="Tasa usada para actualizar los flujos de caja del VAN.",
        ) / 100.0
        horizon = c2.number_input(
            "Horizonte (años)",
            1,
            30,
            10,
            1,
            key=f"{prefix}_horizon",
            help="Número de años incluidos en el cálculo financiero.",
        )
        pess_capex = c3.slider(
            "Pesimista: CAPEX x",
            1.0,
            2.0,
            1.30,
            0.05,
            key=f"{prefix}_pess_capex",
            help="Multiplicador aplicado al CAPEX total en el escenario pesimista.",
        )
        pess_savings = c3.slider(
            "Pesimista: ahorro x",
            0.1,
            1.0,
            0.75,
            0.05,
            key=f"{prefix}_pess_savings",
            help="Multiplicador aplicado al ahorro neto anual en el escenario pesimista.",
        )

    additional = AdditionalCostParams(
        training_capex=training,
        mitigation_phasing_capex=phasing,
        mitigation_backup_capex=backup,
        incentive_total=incentives,
        incentive_capex_share=incentive_capex_share,
        insurance_opex=insurance,
        transport_support=support,
        include_labor_regulation_as_incremental=include_regulation,
        labor_regulation_opex=regulation,
    )
    finance = FinanceParams(
        discount_rate=discount_rate,
        horizon_years=horizon,
        pessimistic_capex_multiplier=pess_capex,
        pessimistic_savings_multiplier=pess_savings,
    )
    return options, additional, finance


def _vehicle_controls() -> VehicleCostParams:
    with st.expander("Costes de flota", expanded=False):
        st.caption(
            "Edita cantidades y costes unitarios para sensibilidad económica. "
            "Este bloque calcula coste anual de flota; no es el solver de rutas."
        )
        c1, c2, c3 = st.columns(3)
        vans_a = c1.number_input(
            "Furgonetas sin km ni dietas",
            0,
            1_000,
            26,
            1,
            help="Número de furgonetas propias sin kilometraje ni dietas.",
        )
        vans_b = c2.number_input(
            "Furgonetas sin km con dietas",
            0,
            1_000,
            19,
            1,
            help="Número de furgonetas propias sin kilometraje pero con dietas.",
        )
        vans_c = c3.number_input(
            "Furgonetas con km y dietas",
            0,
            1_000,
            75,
            1,
            help="Número de furgonetas propias con kilometraje y dietas.",
        )
        c1, c2, c3 = st.columns(3)
        subcontracted = c1.number_input(
            "Furgonetas subcontratadas",
            0,
            1_000,
            51,
            1,
            help="Número de furgonetas contratadas a terceros.",
        )
        trailer_a = c2.number_input(
            "Trailers con km y dietas",
            0,
            100,
            1,
            1,
            help="Número de trailers con kilometraje y dietas.",
        )
        trailer_b = c3.number_input(
            "Trailers sin dietas",
            0,
            100,
            6,
            1,
            help="Número de trailers sin dietas.",
        )

        c1, c2, c3 = st.columns(3)
        unit_a = c1.number_input(
            "€/año furgo sin km/dietas",
            0.0,
            500_000.0,
            48_370.93,
            100.0,
            help="Coste anual unitario de furgoneta sin kilometraje ni dietas.",
        )
        unit_b = c2.number_input(
            "€/año furgo con dietas",
            0.0,
            500_000.0,
            54_739.73,
            100.0,
            help="Coste anual unitario de furgoneta con dietas.",
        )
        unit_c = c3.number_input(
            "€/año furgo km+dietas",
            0.0,
            500_000.0,
            61_012.93,
            100.0,
            help="Coste anual unitario de furgoneta con kilometraje y dietas.",
        )
        c1, c2, c3 = st.columns(3)
        unit_sub = c1.number_input(
            "€/año subcontratada",
            0.0,
            500_000.0,
            45_000.0,
            100.0,
            help="Coste anual unitario de cada furgoneta subcontratada.",
        )
        unit_trailer_a = c2.number_input(
            "€/año trailer km+dietas",
            0.0,
            1_000_000.0,
            147_422.32,
            100.0,
            help="Coste anual unitario de trailer con kilometraje y dietas.",
        )
        unit_trailer_b = c3.number_input(
            "€/año trailer sin dietas",
            0.0,
            1_000_000.0,
            141_053.52,
            100.0,
            help="Coste anual unitario de trailer sin dietas.",
        )
        baseline = st.number_input(
            "Escenario sin unificar: total rutas (M€)",
            0.0,
            100.0,
            10.04038638,
            0.01,
            help="Coste anual de rutas usado como referencia para calcular el diferencial.",
        )

    return VehicleCostParams(
        own_vans_no_km_no_diet_count=vans_a,
        own_vans_no_km_with_diet_count=vans_b,
        own_vans_with_km_diet_count=vans_c,
        subcontracted_vans_count=subcontracted,
        trailer_with_km_diet_count=trailer_a,
        trailer_without_diet_count=trailer_b,
        unit_van_no_km_no_diet=unit_a,
        unit_van_no_km_with_diet=unit_b,
        unit_van_with_km_diet=unit_c,
        unit_subcontracted_van=unit_sub,
        unit_trailer_with_km_diet=unit_trailer_a,
        unit_trailer_without_diet=unit_trailer_b,
        baseline_without_unification_millions=baseline,
    )


def _render_current_cost_snapshot(params: CurrentCostParams, show_chart: bool = True) -> None:
    current = current_cost_frame(params)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Coste actual total", _fmt_money(total_current_cost(params)))
    c2.metric("Transferencias", _fmt_money(params.transfer_annual_cost))
    c3.metric("Coste/paquete transferido", f"{transfer_unit_cost(params):.4f} €")
    c4.metric("Distancia transferencia", f"{params.transfer_distance_km:.1f} km")
    st.dataframe(_money_df(current, ["SVQ1", "DQA4", "Total"]), hide_index=True, use_container_width=True)
    st.caption(
        "Estos importes describen la situación actual del caso y sirven como línea base para comparar alternativas."
    )
    if show_chart:
        st.plotly_chart(
            _bar_chart(current, "Concepto", ["SVQ1", "DQA4"], "Desglose anual de costes actuales"),
            use_container_width=True,
        )


def _render_operational_economics_bridge(
    pipeline_result,
    center_option: str,
    current_costs: CurrentCostParams | None = None,
    vehicle_cost_params: VehicleCostParams | None = None,
    dqa4_attributable_share: float = DEFAULT_DQA4_ATTRIBUTABLE_SHARE,
) -> None:
    """Muestra el puente entre las rutas calculadas y la lectura economica."""
    if pipeline_result is None:
        st.info(
            "Calcula primero las rutas para ver cómo las métricas operativas alimentan "
            "esta lectura económica complementaria."
        )
        return

    current_costs = current_costs or CurrentCostParams()
    vehicle_cost_params = vehicle_cost_params or VehicleCostParams()
    bridge_result = estimate_operational_cost_bridge(
        pipeline_result=pipeline_result,
        current_costs=current_costs,
        vehicle_cost_params=vehicle_cost_params,
        center_option=center_option,
        dqa4_attributable_share=dqa4_attributable_share,
    )
    bridge = bridge_result.bridge
    summary = bridge.operational_summary

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Alternativa", summary.center_option)
    c2.metric("Depot usado", summary.depot_name)
    c3.metric("Rutas totales", _fmt_int(summary.total_routes))
    c4.metric("Paquetes", _fmt_int(summary.total_packages))

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Distancia rutas", f"{_fmt_num(summary.total_distance_km, 0)} km")
    c2.metric("Tiempo rutas", f"{_fmt_num(summary.total_time_min, 0)} min")
    c3.metric("Flota VRP", f"{summary.diesel_count} D / {summary.electric_count} E")
    c4.metric("Dedicadas", f"{summary.dedicated_routes} rutas")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Transferencia reducible", _fmt_money(bridge.transfer_cost_removed_or_reduced))
    c2.metric("DQA4 parcial", _fmt_money(bridge.dqa4_liberable_cost_estimate))
    c3.metric("Coste flota anual", _fmt_money(bridge.route_cost_estimate))
    c4.metric("Ahorro operativo ajustado", _fmt_money(bridge_result.adjusted_operational_saving))

    st.caption(
        "El ajuste operativo suma transferencia reducible y la parte atribuible/liberable de DQA4 "
        "solo cuando la alternativa lo permite, y descuenta el diferencial de flota cuando aplica. "
        "Es una orientación operativa, no sustituye el análisis financiero completo."
    )
    st.markdown(bridge_result.interpretation)

    display_warnings = _filter_display_warnings(
        bridge.warnings,
        center_option,
    )
    if (
        center_option == OPERATIONAL_OPTION_INTERMEDIATE
        and _is_virtual_depot_name(summary.depot_name)
    ):
        st.info(AUTO_NEW_LOCATION_VIRTUAL_WARNING)
    if display_warnings:
        st.warning(" ".join(display_warnings))

    detail_rows = [
        ("Coste actual base", bridge_result.baseline_current_cost),
        ("Coste DQA4 base", dqa4_current_cost(current_costs)),
        ("Ahorro transferencia estimado", bridge_result.estimated_transfer_saving),
        ("Ahorro DQA4 parcial estimado", bridge_result.estimated_dqa4_partial_saving),
        ("Diferencial anual de flota", bridge_result.estimated_route_cost_delta),
        ("Ahorro operativo ajustado", bridge_result.adjusted_operational_saving),
    ]
    detail_df = pd.DataFrame(detail_rows, columns=["Concepto", "Importe"])
    st.dataframe(
        _money_df(detail_df, ["Importe"]),
        hide_index=True,
        use_container_width=True,
    )

    with st.expander("Notas del puente operativo-económico", expanded=False):
        st.markdown("\n".join(f"- {note}" for note in bridge.notes))


def _render_economic_results_table(results: pd.DataFrame) -> None:
    display = results.copy()
    for col in [
        "CAPEX base",
        "CAPEX transición",
        "CAPEX total",
        "Ahorro bruto anual",
        "OPEX nuevo anual",
        "Ahorro neto anual",
        "VAN",
        "VAN pesimista",
    ]:
        display[col] = display[col].apply(_fmt_money)
    for col in ["TIR", "VAN/CAPEX"]:
        display[col] = display[col].apply(_fmt_pct)
    for col in ["Payback neto", "Payback pesimista"]:
        display[col] = display[col].apply(_fmt_years)
    st.dataframe(display, hide_index=True, use_container_width=True)
    st.caption(
        "Compara inversión, costes recurrentes, recuperación y valor financiero actualizado por alternativa."
    )


def _render_labor_summary_metrics(labor_result) -> None:
    labor_summary = labor_result.summary
    st.caption(
        "Resume empleados afectados, desplazamiento adicional, costes únicos y anuales, "
        "y riesgo laboral estimado antes y después de apoyos."
    )
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Empleados afectados", _fmt_int(labor_summary.affected_employees))
    c2.metric("Desplazamiento extra", f"{labor_summary.additional_commute_km_daily:.1f} km/día")
    c3.metric("Coste único laboral", _fmt_money(labor_summary.oneoff_cost))
    c4.metric("Coste anual laboral", _fmt_money(labor_summary.annual_recurring_cost))
    c1, c2, c3 = st.columns(3)
    c1.metric("Riesgo laboral esperado", _fmt_money(labor_summary.expected_risk_cost))
    c2.metric("Riesgo laboral residual", _fmt_money(labor_summary.residual_risk_cost))
    c3.metric("Aceptabilidad", labor_summary.acceptability)
    st.caption(
        "Una opción barata puede mantener más riesgo laboral si no compensa el desplazamiento "
        "o la adaptación de los empleados."
    )


def _render_labor_detail_tables(labor_result) -> None:
    st.caption("Costes únicos y anuales incluidos según la política laboral elegida.")
    st.dataframe(
        _money_df(labor_cost_frame(labor_result.cost_lines), ["Importe"]),
        hide_index=True,
        use_container_width=True,
    )
    labor_risks = labor_risk_frame(labor_result.risk_results)
    st.caption(
        "El riesgo residual aplica las mitigaciones seleccionadas a la probabilidad base; "
        "el valor esperado se interpreta como coste medio estimado."
    )
    st.dataframe(
        _pct_df(
            _money_df(
                labor_risks,
                ["Coste si ocurre", "Valor esperado", "Valor esperado residual"],
            ),
            ["Probabilidad", "Probabilidad residual", "Reducción probabilidad"],
        ),
        hide_index=True,
        use_container_width=True,
    )


def _render_metric_explanations() -> None:
    _section_title("Cómo leer las métricas")
    st.caption("Glosario mínimo para interpretar la decisión sin entrar en la hoja completa.")
    st.markdown(
        "- **CAPEX**: inversión inicial para hacer el cambio.\n"
        "- **CAPEX de transición**: formación, mitigaciones y apoyos tratados como coste único.\n"
        "- **OPEX**: costes anuales recurrentes que aparecen con la alternativa.\n"
        "- **Ahorro bruto**: ahorro anual antes de restar nuevos costes.\n"
        "- **Ahorro neto**: ahorro bruto menos nuevos costes anuales.\n"
        "- **Payback**: años necesarios para recuperar la inversión.\n"
        "- **VAN**: valor económico actualizado del proyecto en el horizonte elegido.\n"
        "- **TIR**: rentabilidad aproximada del proyecto.\n"
        "- **Pesimista**: prueba una inversión más cara y ahorros menores."
    )


def _render_economics_normal_view(
    pipeline_result=None,
    center_option: str = OPERATIONAL_OPTION_CURRENT,
) -> None:
    params = CurrentCostParams()
    finance = FinanceParams()
    st.caption(
        "Vista normal: pocos controles, datos base protegidos y resultados principales para decidir."
    )

    _section_title("Datos base del caso")
    st.caption(
        "Muestra los costes y transferencias documentados como punto de partida; en esta vista no son editables."
    )
    _render_current_cost_snapshot(params)

    _section_title("Conexión logística-economía")
    st.caption(
        "Traduce las rutas calculadas en una lectura económica simple. La estructura actual "
        "mantiene DQA4 como centro de reparto; SVQ1 ampliado prueba qué pasaría si SVQ1 "
        "absorbiera ese flujo de última milla."
    )
    _render_operational_economics_bridge(
        pipeline_result=pipeline_result,
        center_option=center_option,
        current_costs=params,
        vehicle_cost_params=VehicleCostParams(),
    )

    _section_title("Decisiones principales")
    st.caption(
        "Aquí solo se cambian palancas de decisión: inversión, apoyo laboral y mitigaciones principales."
    )
    c1, c2, c3 = st.columns(3)
    option_name = c1.selectbox(
        "Opción de inversión",
        [option.name for option in DEFAULT_OPTIONS],
        index=1,
        help="Elige el nivel de inversión que se evaluará con los supuestos base.",
    )
    transport_support = c2.selectbox(
        "Apoyo empleados DQA4",
        ["Sin apoyo", "Subsidio transporte público", "Transporte corporativo", "Compensación única"],
        index=1,
        help="Selecciona la medida de apoyo para empleados DQA4 afectados por el traslado.",
    )
    financial_scenario = c3.radio(
        "Escenario financiero",
        ["Base", "Pesimista"],
        horizontal=True,
        help="Base usa los flujos centrales; pesimista usa inversión más cara y ahorros menores.",
    )

    c1, c2, c3 = st.columns(3)
    include_phasing = c1.checkbox(
        "Implementación por fases",
        value=True,
        help="Incluye el coste de mitigación por desplegar el cambio progresivamente.",
    )
    include_backup = c2.checkbox(
        "Sistemas de respaldo",
        value=True,
        help="Incluye el coste de mitigación para reducir riesgo tecnológico y operativo.",
    )
    include_incentives = c3.checkbox(
        "Incentivos empleados",
        value=True,
        help="Incluye incentivos laborales como coste de transición y permanencia.",
    )
    c1, c2 = st.columns(2)
    include_insurance = c1.checkbox(
        "Seguros especiales",
        value=True,
        help="Incluye el coste anual de seguros especiales como mitigación financiera.",
    )
    include_regulation = c2.checkbox(
        "Regulación laboral 2025 incremental",
        value=False,
        help="Añade la regulación 2025 como coste anual incremental del proyecto.",
    )
    st.caption(
        "Los importes detallados permanecen en los defaults documentados; usa la vista avanzada para sensibilidad."
    )

    additional = AdditionalCostParams(
        transport_support=transport_support,
        include_mitigation_phasing=include_phasing,
        include_mitigation_backup=include_backup,
        include_incentives=include_incentives,
        include_insurance=include_insurance,
        include_labor_regulation_as_incremental=include_regulation,
    )
    selected_option = next(option for option in DEFAULT_OPTIONS if option.name == option_name)
    result = compute_economic_result(selected_option, additional, finance)
    labor_result = labor_policy_result_from_additional(additional)

    _section_title("Resultados de la opción seleccionada")
    st.caption(
        "Calcula la inversión, los nuevos costes anuales y la recuperación usando el modelo económico existente."
    )
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("CAPEX total", _fmt_money(result.capex_total))
    c2.metric("CAPEX transición", _fmt_money(result.capex_transition))
    c3.metric("OPEX nuevo anual", _fmt_money(result.opex_new_annual))
    c4.metric("Ahorro bruto anual", _fmt_money(result.gross_savings_annual))
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Ahorro neto anual", _fmt_money(result.net_savings_annual))
    c2.metric("Payback neto", _fmt_years(result.payback_net))
    c3.metric("VAN", _fmt_money(result.van))
    c4.metric("TIR", _fmt_pct(result.tir))
    st.caption(
        "Un mayor VAN (valor económico actualizado) indica mejor resultado financiero bajo estos supuestos, "
        "pero no sustituye el análisis operativo y de riesgos."
    )

    if financial_scenario == "Pesimista":
        _section_title("Resultado pesimista")
        st.caption(
            "Aplica inversión más alta y ahorro neto menor para ver si la alternativa resiste un escenario adverso."
        )
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("CAPEX total pesimista", _fmt_money(result.pessimistic.capex_total))
        c2.metric("Ahorro neto pesimista", _fmt_money(result.pessimistic.net_savings_annual))
        c3.metric("Payback pesimista", _fmt_years(result.pessimistic.payback))
        c4.metric("VAN pesimista", _fmt_money(result.pessimistic.van))

    _section_title("Resumen laboral")
    st.caption(
        "Resume el impacto sobre empleados DQA4, separando coste directo y riesgo laboral residual."
    )
    _render_labor_summary_metrics(labor_result)
    with st.expander("Detalle laboral", expanded=False):
        st.caption("Desglosa costes laborales y riesgos residuales derivados de las decisiones elegidas.")
        _render_labor_detail_tables(labor_result)

    _render_metric_explanations()


def _render_economics_advanced_view(
    pipeline_result=None,
    center_option: str = OPERATIONAL_OPTION_CURRENT,
) -> None:
    st.caption(
        "Vista avanzada: parámetros editables para sensibilidad. Úsala para probar supuestos, no como lectura principal."
    )
    tab_bridge, tab_current, tab_investment, tab_fleet, tab_risk = st.tabs(
        ["Puente operativo", "Costes actuales", "Inversión y VAN", "Flota", "Riesgos"]
    )

    with tab_bridge:
        _section_title("Conexión logística-economía")
        st.caption(
            "Permite probar qué parte de DQA4 se considera atribuible al flujo SVQ1 → DQA4 "
            "cuando SVQ1 ampliado absorbe ese flujo. En estructura actual, DQA4 sigue siendo "
            "el centro de reparto y no se reconoce ahorro por transferencia."
        )
        dqa4_share = st.slider(
            "Porcentaje DQA4 atribuible/liberable",
            0.0,
            0.99,
            DEFAULT_DQA4_ATTRIBUTABLE_SHARE,
            0.01,
            format="%.2f",
            help=(
                "Parte conservadora del coste DQA4 que se considera atribuible al "
                "flujo SVQ1-DQA4. No representa cierre completo de DQA4."
            ),
        )
        _render_operational_economics_bridge(
            pipeline_result=pipeline_result,
            center_option=center_option,
            current_costs=CurrentCostParams(),
            vehicle_cost_params=VehicleCostParams(),
            dqa4_attributable_share=dqa4_share,
        )

    with tab_current:
        _section_title("Costes actuales")
        st.caption(
            "Permite recalcular la situación actual modificando costes base, transferencias y volúmenes."
        )
        params = _current_cost_controls()
        _render_current_cost_snapshot(params)

    with tab_investment:
        _section_title("Inversión y VAN")
        st.caption(
            "Compara las alternativas editando CAPEX, costes de transición, OPEX incremental y parámetros financieros."
        )
        options, additional, finance = _investment_controls("investment")
        structured_results = compute_economic_results(options, additional, finance)
        results = economic_results_frame(structured_results)
        recommended = recommend_option(results)
        extra_capex, extra_opex, extra_frame = additional_capex_opex(additional)

        _section_title("Resultados financieros")
        st.caption(
            "Resume recomendación, inversión de transición, costes anuales nuevos y valor económico actualizado "
            "con los parámetros editados."
        )
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Opción recomendada", recommended)
        c2.metric("CAPEX transición", _fmt_money(extra_capex))
        c3.metric("OPEX nuevo", _fmt_money(extra_opex))
        best_result = next(result for result in structured_results if result.option_name == recommended)
        c4.metric("VAN recomendado", _fmt_money(best_result.van))

        _render_economic_results_table(results)

        st.dataframe(_money_df(extra_frame, ["Importe"]), hide_index=True, use_container_width=True)
        st.caption("La tabla separa costes únicos de transición y costes anuales que reducen el ahorro neto.")

        labor_result = labor_policy_result_from_additional(additional)
        with st.expander("Resumen laboral", expanded=False):
            st.caption("Resume el efecto laboral de los costes adicionales y del apoyo elegido.")
            _render_labor_summary_metrics(labor_result)
            _render_labor_detail_tables(labor_result)

        chart_df = results[["Opción", "CAPEX total", "VAN", "VAN pesimista"]]
        st.plotly_chart(
            _bar_chart(chart_df, "Opción", ["CAPEX total", "VAN", "VAN pesimista"], "CAPEX y VAN por opción"),
            use_container_width=True,
        )

    with tab_fleet:
        _section_title("Flota")
        st.caption(
            "Calcula el coste económico anual de flota con cantidades y costes unitarios. "
            "No modifica las rutas calculadas."
        )
        params = _vehicle_controls()
        df = vehicle_cost_frame(params)
        totals = vehicle_totals(params)
        _section_title("Costes anuales de rutas")
        st.caption(
            "Agrupa furgonetas propias, furgonetas subcontratadas y trailers, y compara contra el escenario sin unificar."
        )
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Furgonetas", _fmt_money(totals["vans"]))
        c2.metric("Trailers", _fmt_money(totals["trailers"]))
        c3.metric("Total rutas", _fmt_money(totals["total"]))
        c4.metric("Diferencial", _fmt_money(totals["difference"]))
        st.dataframe(
            _money_df(df, ["Coste unitario anual", "Coste anual"]),
            hide_index=True,
            use_container_width=True,
        )
        st.caption("Los costes unitarios proceden de supuestos internos del proyecto y sirven para sensibilidad económica.")
        st.plotly_chart(
            _bar_chart(df, "Bloque", ["Coste anual"], "Costes de flota por bloque"),
            use_container_width=True,
        )

    with tab_risk:
        _section_title("Riesgos")
        st.caption(
            "Cuantifica exposición al riesgo como probabilidad por impacto. No es una predicción exacta; "
            "sirve para comparar exposición."
        )
        with st.expander("¿Cómo leer este bloque?", expanded=False):
            st.markdown(
                "- **Coste medio estimado** = probabilidad x impacto económico.\n"
                "- **Riesgo residual** es el riesgo que queda después de mitigaciones cuando el modelo lo calcula.\n"
                "- **Tormenta perfecta** agrupa un escenario extremo combinado.\n"
                "- Los riesgos ayudan a comparar alternativas, no sustituyen el juicio del equipo."
            )
        options, additional, finance = _investment_controls("risk")
        results = analyze_options(options, additional, finance)
        selected_name = st.selectbox(
            "Opción para riesgo de construcción",
            [o.name for o in options],
            index=1,
            help="Alternativa cuyo CAPEX base se usa para estimar el sobrecoste de construcción.",
        )
        selected_option = next(o for o in options if o.name == selected_name)

        st.markdown("**Riesgos cuantificados**")
        st.caption("Edita nombre, probabilidad e impacto de cada riesgo incluido en el coste medio estimado.")
        risks: list[Risk] = []
        for idx, default in enumerate(DEFAULT_RISKS):
            c1, c2, c3 = st.columns(3)
            name = c1.text_input(
                f"Riesgo {idx + 1}",
                default.name,
                key=f"risk_name_{idx}",
                help="Nombre descriptivo del riesgo evaluado.",
            )
            prob = c2.slider(
                f"Probabilidad {idx + 1} (%)",
                0.0,
                100.0,
                default.probability * 100.0,
                1.0,
                key=f"risk_prob_{idx}",
                help="Probabilidad estimada de que ocurra este riesgo.",
            ) / 100.0
            cost = c3.number_input(
                f"Coste {idx + 1} (M€)",
                0.0,
                100.0,
                default.cost_if_occurs / 1e6,
                0.1,
                key=f"risk_cost_{idx}",
                help="Impacto económico si el riesgo ocurre.",
            ) * 1e6
            risks.append(Risk(name, prob, cost))

        include_construction = st.checkbox(
            "Añadir sobrecoste construcción como 30% del CAPEX base",
            value=True,
            help="Incluye un riesgo adicional de sobrecoste calculado sobre el CAPEX base seleccionado.",
        )
        if include_construction:
            risks.append(Risk("Sobrecostes construcción (+30%)", 0.35, selected_option.capex_base * 0.30))
        storm_prob = st.slider(
            "Probabilidad tormenta perfecta (%)",
            0.0,
            25.0,
            3.0,
            0.5,
            help="Probabilidad del escenario extremo combinado descrito en el enunciado.",
        ) / 100.0
        storm_cost = st.number_input(
            "Coste tormenta perfecta (M€)",
            0.0,
            100.0,
            15.2,
            0.1,
            help="Impacto económico del escenario extremo combinado.",
        ) * 1e6
        st.caption(
            "La tormenta perfecta combina fallos críticos, conflictos y sobrecostes; se muestra como prueba de estrés."
        )
        risks.append(Risk("Tormenta perfecta", storm_prob, storm_cost))

        rf = risk_frame(risks, selected_option)
        c1, c2 = st.columns(2)
        c1.metric("Coste medio estimado total", _fmt_money(rf["Valor esperado"].sum()))
        recommended = recommend_option(results)
        c2.metric("Opción financiera recomendada", recommended)
        st.dataframe(
            _pct_df(_money_df(rf, ["Coste si ocurre", "Valor esperado"]), ["Probabilidad"]),
            hide_index=True,
            use_container_width=True,
        )
        st.caption("La suma del coste medio estimado resume exposición económica, no una pérdida segura.")


def _closest_option_index(options: dict[str, float], value: float) -> int:
    labels = list(options.keys())
    return min(range(len(labels)), key=lambda idx: abs(options[labels[idx]] - value))


def _guided_dataset_signature(dataset) -> tuple:
    return (
        tuple(dataset.names),
        tuple(int(value) for value in np.asarray(dataset.poblacion).tolist()),
        int(dataset.depot_index),
    )


def _guided_pipeline_signature(pipeline_config) -> tuple:
    return (
        float(pipeline_config.market_penetration),
        float(pipeline_config.max_workday_hours),
        float(pipeline_config.service_time_per_package_min),
        float(pipeline_config.inter_package_time_min),
        float(pipeline_config.seasonality_multiplier),
        (
            None
            if pipeline_config.target_daily_volume is None
            else float(pipeline_config.target_daily_volume)
        ),
        repr(pipeline_config.fleet),
        repr(pipeline_config.trailer),
        repr(pipeline_config.schedule),
        str(pipeline_config.solver_strategy),
        int(pipeline_config.solver_time_limit_seconds),
    )


def _guided_route_signature(
    scenarios: tuple[ScenarioConfig, ...],
    dataset,
    pipeline_config,
    route_params: dict | None,
) -> tuple:
    params_signature = ()
    if route_params:
        params_signature = tuple(
            sorted((key, str(value)) for key, value in route_params.items())
        )
    scenario_signature = tuple(
        (
            scenario.name,
            scenario.center_option,
            scenario.investment_option_name,
            scenario.transport_support,
            scenario.include_phasing,
            scenario.include_backup,
            scenario.start_month,
        )
        for scenario in scenarios
    )
    return (
        "guided_memory",
        scenario_signature,
        _guided_dataset_signature(dataset),
        _guided_pipeline_signature(pipeline_config),
        params_signature,
    )


def _compute_guided_scenario_runs(
    dataset,
    pipeline_config,
    route_params: dict | None,
) -> list[dict[str, object]]:
    scenarios = build_preset_scenario_configs(SCENARIO_PRESET_BASIC)
    runs: list[dict[str, object]] = []

    for scenario in scenarios:
        notes: tuple[str, ...] = ()
        pipeline_result = None
        error: str | None = None
        try:
            dataset_for_run, notes = resolve_scenario_depot(dataset, scenario)
            pipeline_result = run_pipeline(dataset_for_run, pipeline_config)
            scenario_result = build_scenario_result(
                scenario,
                pipeline_result=pipeline_result,
                route_params=route_params,
            )
        except Exception as exc:
            error = str(exc)
            scenario_result = build_scenario_result(
                scenario,
                pipeline_result=None,
                route_params=route_params,
            )
        runs.append(
            {
                "scenario": scenario,
                "result": scenario_result,
                "pipeline_result": pipeline_result,
                "notes": notes,
                "error": error,
            }
        )

    return runs


def _get_guided_scenario_runs(
    dataset,
    pipeline_config,
    route_params: dict | None,
) -> list[dict[str, object]]:
    scenarios = build_preset_scenario_configs(SCENARIO_PRESET_BASIC)
    signature = _guided_route_signature(scenarios, dataset, pipeline_config, route_params)
    if (
        st.session_state.get("guided_memory_signature") == signature
        and "guided_memory_runs" in st.session_state
    ):
        return st.session_state["guided_memory_runs"]

    with st.spinner("Calculando comparacion operativa A/B/C..."):
        runs = _compute_guided_scenario_runs(
            dataset,
            pipeline_config,
            route_params,
        )
    st.session_state["guided_memory_runs"] = runs
    st.session_state["guided_memory_signature"] = signature
    return runs


def _guided_result_for_center(
    runs: list[dict[str, object]],
    center_option: str,
):
    for run in runs:
        result = run["result"]
        if result.config.center_option == center_option:
            return result
    return None


def _guided_summary_for_center(
    runs: list[dict[str, object]],
    center_option: str,
):
    result = _guided_result_for_center(runs, center_option)
    if result is None or result.operational_economic_result is None:
        return None
    return result.operational_economic_result.bridge.operational_summary


def _guided_minutes(value: float | None) -> str:
    if value is None:
        return "-"
    return f"{_fmt_num(float(value), 0)} min"


def _guided_source_label(source: str | None) -> str:
    if not source:
        return "proxy"
    normalized = str(source).casefold()
    if "od" in normalized or "matriz" in normalized:
        return "OD real"
    if "haversine" in normalized:
        return "Haversine"
    if "no disponible" in normalized:
        return "no disponible"
    return "proxy"


def _guided_candidate_label(candidate_name: str) -> str:
    if candidate_name == SECONDARY_HUB_NAME:
        return "DQA4"
    if candidate_name == DEPOT_NAME:
        return "SVQ1"
    if "continuo" in candidate_name.casefold():
        return "Optimo continuo / Weber"
    if "intermedio" in candidate_name.casefold() or "punto medio" in candidate_name.casefold():
        return "Centro intermedio"
    return candidate_name


def _render_guided_demand_block(dataset, pipeline_config) -> None:
    _section_title("1. Demanda")
    st.markdown("**Pregunta:** ¿donde estan los paquetes?")
    st.caption(
        "La demanda se estima con poblacion como proxy, con calibracion opcional "
        "de volumen y multiplicador estacional."
    )

    demand_config = pipeline_config.to_demand_config()
    packages = compute_packages(dataset.poblacion, demand_config, dataset.depot_index)
    population_mask = np.asarray(dataset.poblacion) > 0
    total_population = int(np.asarray(dataset.poblacion)[population_mask].sum())
    demand_nodes = int(population_mask.sum())

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Nodos con demanda", _fmt_int(demand_nodes))
    c2.metric("Poblacion considerada", _fmt_int(total_population))
    c3.metric("Paquetes estimados", _fmt_int(int(packages.sum())))
    c4.metric("Multiplicador estacional", f"x{pipeline_config.seasonality_multiplier:.2f}")
    c5.metric(
        "Volumen objetivo",
        _fmt_int(float(pipeline_config.target_daily_volume))
        if pipeline_config.target_daily_volume is not None
        else "No calibrado",
    )

    rows = []
    for name, population, package_count in zip(dataset.names, dataset.poblacion, packages):
        if int(package_count) <= 0:
            continue
        rows.append(
            {
                "Municipio": name,
                "Poblacion": int(population),
                "Paquetes estimados": int(package_count),
            }
        )
    top_demand = pd.DataFrame(rows)
    if top_demand.empty:
        st.warning("No hay nodos con demanda estimada para mostrar.")
    else:
        top_demand = top_demand.sort_values(
            "Paquetes estimados",
            ascending=False,
        ).head(8)
        st.dataframe(top_demand, hide_index=True, use_container_width=True)
    st.info(
        "No se usa demanda real de Amazon; se usa poblacion como proxy academico."
    )


def _render_guided_location_block(dataset) -> None:
    _section_title("2. Localizacion")
    st.markdown("**Pregunta:** ¿que ubicacion esta mejor situada respecto a la demanda?")
    st.caption(
        "La localizacion mide accesibilidad espacial. El coste geometrico no son euros "
        "ni equivale a los kilometros finales de una ruta."
    )

    solver = LocationSolver(dataset)
    method_result = solver.solve(LocationMethod.MIN_TOTAL_DISTANCE)
    candidates = solver.build_default_candidates(method_result)
    comparison = solver.evaluate_candidates(candidates)

    rows = []
    for evaluation in comparison.evaluations:
        candidate = evaluation.candidate
        rows.append(
            {
                "Candidato": _guided_candidate_label(candidate.name),
                "Detalle": candidate.name,
                "Distancia media ponderada": f"{_fmt_num(evaluation.weighted_mean_distance_km, 2)} km",
                "Tiempo medio ponderado": (
                    f"{_fmt_num(evaluation.weighted_mean_time_min, 1)} min"
                    if evaluation.weighted_mean_time_min is not None
                    else "-"
                ),
                "Fuente": (
                    f"{_guided_source_label(evaluation.distance_source)} / "
                    f"{_guided_source_label(evaluation.time_source)}"
                ),
            }
        )

    order = {
        "DQA4": 0,
        "SVQ1": 1,
        "Optimo continuo / Weber": 2,
        "Centro intermedio": 3,
    }
    frame = pd.DataFrame(rows)
    if frame.empty:
        st.warning("No se pudieron construir candidatos de localizacion.")
    else:
        frame["_order"] = frame["Candidato"].map(lambda value: order.get(value, 99))
        frame = frame.sort_values(["_order", "Candidato"]).drop(columns=["_order"])
        st.dataframe(frame, hide_index=True, use_container_width=True)
    st.info(
        "La localizacion no decide la fusion; solo mide accesibilidad espacial."
    )


def _render_guided_routes_block(runs: list[dict[str, object]]) -> None:
    _section_title("3. Rutas")
    st.markdown(
        "**Pregunta:** ¿cuanto empeora o mejora la operacion de reparto segun el centro de salida?"
    )
    st.caption(
        "Se comparan como maximo tres alternativas: estructura actual con DQA4, "
        "SVQ1 ampliado y nuevo centro/intermedio como contraste academico."
    )

    rows = []
    for run in runs:
        result = run["result"]
        summary = (
            result.operational_economic_result.bridge.operational_summary
            if result.operational_economic_result is not None
            else None
        )
        pipeline_result = run["pipeline_result"]
        unserved = (
            len(pipeline_result.vrp.unassigned_nodes)
            if pipeline_result is not None
            else None
        )
        vehicle_count = (
            summary.diesel_count + summary.electric_count + summary.dedicated_routes
            if summary is not None
            else None
        )
        rows.append(
            {
                "Escenario": result.config.name,
                "Centro de salida": summary.depot_name if summary is not None else "-",
                "Rutas totales": summary.total_routes if summary is not None else None,
                "km/dia": summary.total_distance_km if summary is not None else None,
                "Tiempo total": summary.total_time_min if summary is not None else None,
                "Vehiculos usados": vehicle_count,
                "Paquetes": summary.total_packages if summary is not None else None,
                "Nodos no servidos": unserved,
            }
        )

    display = pd.DataFrame(rows)
    if display.empty:
        st.warning("No hay resultados de rutas para comparar.")
    else:
        for col in ("Rutas totales", "Vehiculos usados", "Paquetes", "Nodos no servidos"):
            display[col] = display[col].map(_fmt_optional_int)
        display["km/dia"] = display["km/dia"].map(
            lambda value: "-" if pd.isna(value) else f"{_fmt_num(float(value), 0)} km"
        )
        display["Tiempo total"] = display["Tiempo total"].map(
            lambda value: "-" if pd.isna(value) else _guided_minutes(float(value))
        )
        st.dataframe(display, hide_index=True, use_container_width=True)

    for run in runs:
        if run["error"]:
            st.warning(f"{run['scenario'].name}: no se pudieron calcular rutas ({run['error']}).")
        for note in run["notes"]:
            if note == AUTO_NEW_LOCATION_VIRTUAL_WARNING:
                st.warning(note)
            else:
                st.caption(note)

    st.info(
        "Si SVQ1 aumenta km o tiempo, eso es una penalizacion operativa de ultima milla."
    )


def _render_guided_economics_block(runs: list[dict[str, object]]) -> None:
    _section_title("4. Analisis economico")
    st.markdown(
        "**Pregunta:** ¿compensan los ahorros estructurales la penalizacion operativa?"
    )
    st.caption(
        "La tabla mantiene una lectura sencilla: la estructura actual es la referencia "
        "y las demas alternativas se leen con los supuestos economicos existentes."
    )

    rows = []
    for run in runs:
        result = run["result"]
        bridge = result.operational_economic_result
        is_current = result.config.center_option == OPERATIONAL_OPTION_CURRENT
        is_intermediate = result.config.center_option == OPERATIONAL_OPTION_INTERMEDIATE
        proxy_note = ""
        if is_intermediate:
            summary = (
                bridge.bridge.operational_summary
                if bridge is not None
                else None
            )
            if summary is None or _is_virtual_depot_name(summary.depot_name):
                proxy_note = "Academico/proxy"
            else:
                proxy_note = "Contraste academico"

        if is_current:
            rows.append(
                {
                    "Escenario": result.config.name,
                    "Lectura": "Referencia",
                    "Inversion": 0.0,
                    "Ahorro transferencia": 0.0,
                    "Ahorro DQA4 parcial": 0.0,
                    "Sobrecoste rutas": 0.0,
                    "Ahorro neto anual": 0.0,
                    "Payback": "Referencia",
                    "VAN": 0.0,
                }
            )
            continue

        rows.append(
            {
                "Escenario": result.config.name,
                "Lectura": proxy_note or "Evaluacion economica",
                "Inversion": result.economic_result.capex_total,
                "Ahorro transferencia": (
                    bridge.estimated_transfer_saving if bridge is not None else None
                ),
                "Ahorro DQA4 parcial": (
                    bridge.estimated_dqa4_partial_saving if bridge is not None else None
                ),
                "Sobrecoste rutas": (
                    bridge.estimated_route_cost_delta if bridge is not None else None
                ),
                "Ahorro neto anual": result.economic_result.net_savings_annual,
                "Payback": _fmt_years(result.economic_result.payback_net),
                "VAN": result.economic_result.van,
            }
        )

    display = pd.DataFrame(rows)
    if display.empty:
        st.warning("No hay resultados economicos para mostrar.")
        return

    money_cols = [
        "Inversion",
        "Ahorro transferencia",
        "Ahorro DQA4 parcial",
        "Sobrecoste rutas",
        "Ahorro neto anual",
        "VAN",
    ]
    for col in money_cols:
        display[col] = display[col].map(
            lambda value: "-" if pd.isna(value) else _fmt_money(float(value))
        )
    st.dataframe(display, hide_index=True, use_container_width=True)
    st.info(
        "El escenario actual es la base. SVQ1 solo es defendible si el ahorro "
        "estructural compensa el sobrecoste operativo de reparto."
    )


def _render_guided_conclusion_block(runs: list[dict[str, object]]) -> None:
    _section_title("5. Conclusion")
    current = _guided_summary_for_center(runs, OPERATIONAL_OPTION_CURRENT)
    svq1 = _guided_summary_for_center(runs, OPERATIONAL_OPTION_SVQ1_EXPANDED)
    svq1_result = _guided_result_for_center(runs, OPERATIONAL_OPTION_SVQ1_EXPANDED)
    intermediate = _guided_summary_for_center(runs, OPERATIONAL_OPTION_INTERMEDIATE)

    if current is not None and svq1 is not None:
        delta_km = svq1.total_distance_km - current.total_distance_km
        delta_min = svq1.total_time_min - current.total_time_min
        if delta_km > 0 or delta_min > 0:
            operational_text = (
                "DQA4 queda mejor situado operativamente para ultima milla: "
                f"SVQ1 suma {_fmt_num(delta_km, 0)} km/dia y "
                f"{_fmt_num(delta_min, 0)} min/dia frente a la referencia."
            )
        else:
            operational_text = (
                "SVQ1 no empeora la referencia operativa con estos parametros; "
                "la comparacion debe revisarse junto con los supuestos de demanda."
            )
    else:
        operational_text = (
            "No hay comparacion operativa completa; revisa el calculo de rutas antes de concluir."
        )

    if svq1_result is not None:
        van = svq1_result.economic_result.van
        if van > 0:
            economic_text = (
                "SVQ1 tiene lectura economica positiva en el modelo estructurado, "
                f"con VAN {_fmt_money(van)} bajo los supuestos actuales."
            )
        else:
            economic_text = (
                "SVQ1 no compensa economicamente bajo los supuestos actuales "
                f"(VAN {_fmt_money(van)})."
            )
    else:
        economic_text = "No hay resultado economico SVQ1 suficiente para comparar."

    viability_text = (
        "La viabilidad exige que los ahorros por transferencia y actividad atribuible "
        "a DQA4 superen la penalizacion de rutas, sin leer el nuevo centro como "
        "recomendacion real directa."
    )
    if intermediate is not None:
        viability_text += " El nuevo centro queda como contraste academico/proxy."

    conclusion = pd.DataFrame(
        [
            {"Lectura": "Resultado operativo", "Frase": operational_text},
            {"Lectura": "Resultado economico", "Frase": economic_text},
            {"Lectura": "Condiciones de viabilidad", "Frase": viability_text},
        ]
    )
    st.dataframe(conclusion, hide_index=True, use_container_width=True)
    st.caption(
        "La conclusion es condicionada: la fusion no se justifica por mejorar rutas, "
        "sino si los ahorros estructurales compensan el empeoramiento operativo."
    )


def render_guided_flow_section(
    dataset,
    pipeline_config,
    route_params: dict | None = None,
) -> None:
    """Renderiza una memoria interactiva sencilla y academica."""

    st.markdown(
        "Esta vista sigue la logica de la memoria del proyecto: demanda, "
        "localizacion, rutas, traduccion economica y conclusion condicionada."
    )
    st.caption(
        "No es un simulador profesional ni un forecast de Amazon. Es una cadena "
        "academica para explicar una decision logistica con proxies documentados."
    )

    runs = _get_guided_scenario_runs(dataset, pipeline_config, route_params)
    _render_guided_demand_block(dataset, pipeline_config)
    _render_guided_location_block(dataset)
    _render_guided_routes_block(runs)
    _render_guided_economics_block(runs)
    _render_guided_conclusion_block(runs)


def render_scenario_tree_lab_section(
    dataset,
    pipeline_config,
    route_params: dict | None = None,
) -> None:
    """Renderiza el laboratorio avanzado basado en comparacion de escenarios."""

    st.markdown(
        "Esta vista compara alternativas completas usando rutas, economía, "
        "cronograma, riesgos y medidas laborales."
    )
    st.caption(
        "El objetivo es preparar una lectura final defendible: define escenarios, "
        "calcula rutas por centro, integra modelos existentes y compara resultados. "
        "No emite una recomendación automática definitiva."
    )

    _section_title("Paso 1. Definir árbol de escenarios")
    build_mode = st.radio(
        "Modo de construcción",
        ["Construcción manual", "Preset rápido"],
        horizontal=True,
        key="scenario_tree_build_mode",
    )

    if build_mode == "Preset rápido":
        if st.session_state.get("scenario_tree_preset") not in SCENARIO_PRESETS:
            st.session_state.pop("scenario_tree_preset", None)
        preset_name = st.selectbox(
            "Preset",
            SCENARIO_PRESETS,
            index=SCENARIO_PRESETS.index(SCENARIO_PRESET_BASIC),
            key="scenario_tree_preset",
        )
        scenarios = build_preset_scenario_configs(preset_name)
        tree_result = ScenarioTreeResult(
            scenarios=scenarios,
            total_combinations=len(scenarios),
            warnings=(),
            limit_exceeded=False,
        )
        st.caption("El preset es un punto de partida; puedes cambiar a construcción manual para abrir ejes.")
    else:
        tree_config = _render_scenario_tree_controls()
        tree_result = build_scenario_configs_from_tree(tree_config)
        scenarios = tree_result.scenarios

    st.metric("Escenarios generados", tree_result.total_combinations)
    for warning in tree_result.warnings:
        st.warning(warning)

    _section_title("Paso 2. Revisar escenarios generados")
    if scenarios:
        scenario_rows = _scenario_config_rows(scenarios)
        st.dataframe(pd.DataFrame(scenario_rows), hide_index=True, use_container_width=True)
        excluded_names = st.multiselect(
            "Excluir escenarios concretos",
            options=[scenario.name for scenario in scenarios],
            default=[],
            key="scenario_tree_exclusions",
            help="Útil para quitar combinaciones poco interesantes antes de calcular.",
        )
        scenarios = tuple(
            scenario for scenario in scenarios if scenario.name not in set(excluded_names)
        )
        st.caption(f"Escenarios seleccionados para cálculo: {len(scenarios)}")
    else:
        excluded_names = []
        st.info("No hay escenarios generados para revisar.")

    signature = _comparison_signature(
        build_mode,
        scenarios,
        excluded_names,
        route_params,
    )
    stored_signature = st.session_state.get("comparison_signature")
    _section_title("Paso 3. Calcular escenarios")
    run_col, info_col = st.columns([1, 3])
    run_button = run_col.button(
        "Calcular escenarios",
        type="primary",
        use_container_width=True,
        disabled=tree_result.limit_exceeded or not scenarios,
    )
    info_col.caption(
        "Usa la configuración de rutas compartida y mantiene las restricciones actuales "
        "de jornada y autonomía eléctrica."
    )

    comparison = st.session_state.get("comparison_results")
    if run_button:
        comparison_config = ScenarioComparisonConfig(scenarios=scenarios)
        with st.spinner("Calculando escenarios completos..."):
            comparison = build_scenario_comparison(
                dataset,
                pipeline_config,
                comparison_config=comparison_config,
                route_params=route_params,
            )
        st.session_state["comparison_results"] = comparison
        st.session_state["comparison_signature"] = signature
    elif comparison is not None and stored_signature != signature:
        comparison = None
        st.info("La configuración cambió. Pulsa Calcular escenarios para actualizar la comparación.")

    if comparison is None:
        if tree_result.limit_exceeded:
            st.info("Reduce el árbol antes de calcular escenarios.")
        elif not scenarios:
            st.info("Genera o selecciona al menos un escenario antes de calcular.")
        else:
            st.info("Pulsa Calcular escenarios para generar la tabla comparativa y el análisis por alternativa.")
        return

    _section_title("Paso 4. Comparar resultados")
    _section_title("Tabla comparativa")
    st.dataframe(
        _format_comparison_frame(comparison.comparison_frame),
        hide_index=True,
        use_container_width=True,
    )

    _section_title("Interpretación preliminar")
    st.info(comparison.interpretation)

    if comparison.warnings:
        with st.expander("Warnings de la comparación", expanded=True):
            for warning in comparison.warnings:
                st.warning(warning)

    result_by_name = {result.config.name: result for result in comparison.results}
    names = list(result_by_name.keys())
    if st.session_state.get("active_scenario_name") not in names:
        st.session_state["active_scenario_name"] = names[0]
    selected_name = st.selectbox(
        "Escenario activo para detalle",
        names,
        index=_active_scenario_index(names),
        key="active_scenario_name",
        help="Guarda el escenario elegido para que futuras vistas puedan reutilizarlo.",
    )
    active_result = result_by_name[selected_name]
    st.session_state["active_scenario_result"] = active_result

    _section_title("Lectura del escenario activo")
    _render_guided_scenario_summary(active_result)

    _section_title("Análisis por escenario")
    for result in comparison.results:
        with st.expander(result.config.name, expanded=result.config.name == selected_name):
            _render_guided_scenario_summary(result)


def _format_comparison_frame(frame: pd.DataFrame) -> pd.DataFrame:
    display = frame.copy()
    money_cols = [
        "CAPEX total",
        "Ahorro neto anual",
        "Ahorro operativo ajustado",
        "Coste medio de riesgos",
        "VAN",
    ]
    for col in money_cols:
        if col in display:
            display[col] = display[col].map(_fmt_optional_money)
    for col in ("Rutas totales", "Vehículos VRP", "Alertas altas de cronograma"):
        if col in display:
            display[col] = display[col].map(_fmt_optional_int)
    if "Distancia total" in display:
        display["Distancia total"] = display["Distancia total"].map(
            lambda value: "-" if pd.isna(value) else f"{_fmt_num(float(value), 0)} km"
        )
    if "Tiempo total" in display:
        display["Tiempo total"] = display["Tiempo total"].map(
            lambda value: "-" if pd.isna(value) else f"{_fmt_num(float(value), 0)} min"
        )
    if "Payback" in display:
        display["Payback"] = display["Payback"].map(
            lambda value: "-" if pd.isna(value) else _fmt_years(float(value))
        )
    return display


def _render_scenario_tree_controls() -> ScenarioTreeConfig:
    center_options = (
        OPERATIONAL_OPTION_CURRENT,
        OPERATIONAL_OPTION_SVQ1_EXPANDED,
        OPERATIONAL_OPTION_INTERMEDIATE,
    )
    investment_names = tuple(option.name for option in DEFAULT_OPTIONS)
    support_options = (
        "Sin apoyo",
        "Subsidio transporte público",
        "Transporte corporativo",
        "Compensación única",
    )
    transition_options = (TRANSITION_DIRECT, TRANSITION_PHASED)
    backup_labels = {"Sí": True, "No": False}

    centers = tuple(
        st.multiselect(
            "Centros a incluir",
            center_options,
            default=(OPERATIONAL_OPTION_CURRENT, OPERATIONAL_OPTION_SVQ1_EXPANDED),
            key="scenario_tree_centers",
        )
    )

    c1, c2 = st.columns(2)
    use_investment_axis = c1.checkbox(
        "Activar eje de inversión",
        value=True,
        key="scenario_tree_use_investment",
    )
    if use_investment_axis:
        investment_options = tuple(
            c2.multiselect(
                "Opciones de inversión",
                investment_names,
                default=("Estándar",),
                key="scenario_tree_investments",
            )
        )
    else:
        investment_options = (
            c2.selectbox(
                "Inversión base",
                investment_names,
                index=investment_names.index("Estándar"),
                key="scenario_tree_investment_base",
            ),
        )

    c1, c2 = st.columns(2)
    use_support_axis = c1.checkbox(
        "Activar eje de apoyo laboral",
        value=False,
        key="scenario_tree_use_support",
    )
    if use_support_axis:
        transport_supports = tuple(
            c2.multiselect(
                "Políticas laborales",
                support_options,
                default=("Subsidio transporte público",),
                key="scenario_tree_supports",
            )
        )
    else:
        transport_supports = (
            c2.selectbox(
                "Apoyo laboral base",
                support_options,
                index=support_options.index("Subsidio transporte público"),
                key="scenario_tree_support_base",
            ),
        )

    c1, c2 = st.columns(2)
    use_transition_axis = c1.checkbox(
        "Activar eje de transición",
        value=False,
        key="scenario_tree_use_transition",
    )
    if use_transition_axis:
        transition_modes = tuple(
            c2.multiselect(
                "Modos de transición",
                transition_options,
                default=(TRANSITION_PHASED,),
                key="scenario_tree_transitions",
            )
        )
    else:
        transition_modes = (
            c2.selectbox(
                "Transición base",
                transition_options,
                index=transition_options.index(TRANSITION_PHASED),
                key="scenario_tree_transition_base",
            ),
        )

    c1, c2 = st.columns(2)
    use_backup_axis = c1.checkbox(
        "Activar eje de respaldo",
        value=False,
        key="scenario_tree_use_backup",
    )
    if use_backup_axis:
        backup_options = tuple(
            backup_labels[label]
            for label in c2.multiselect(
                "Sistemas de respaldo",
                tuple(backup_labels.keys()),
                default=("Sí",),
                key="scenario_tree_backups",
            )
        )
    else:
        backup_options = (
            backup_labels[
                c2.selectbox(
                    "Respaldo base",
                    tuple(backup_labels.keys()),
                    index=0,
                    key="scenario_tree_backup_base",
                )
            ],
        )

    c1, c2 = st.columns(2)
    use_month_axis = c1.checkbox(
        "Activar eje de mes de inicio",
        value=False,
        key="scenario_tree_use_month",
    )
    month_labels = tuple(TREE_START_MONTHS.keys())
    if use_month_axis:
        start_months = tuple(
            TREE_START_MONTHS[label]
            for label in c2.multiselect(
                "Meses de inicio",
                month_labels,
                default=("Enero",),
                key="scenario_tree_months",
            )
        )
    else:
        start_months = (
            TREE_START_MONTHS[
                c2.selectbox(
                    "Mes de inicio base",
                    month_labels,
                    index=0,
                    key="scenario_tree_month_base",
                )
            ],
        )

    max_scenarios = st.number_input(
        "Máximo de combinaciones",
        min_value=1,
        max_value=100,
        value=DEFAULT_MAX_TREE_SCENARIOS,
        step=1,
        key="scenario_tree_max_scenarios",
    )

    return ScenarioTreeConfig(
        centers=centers,
        investment_options=investment_options,
        transport_supports=transport_supports,
        transition_modes=transition_modes,
        backup_options=backup_options,
        start_months=start_months,
        max_scenarios=int(max_scenarios),
    )


def _scenario_config_rows(scenarios: tuple[ScenarioConfig, ...]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for scenario in scenarios:
        rows.append(
            {
                "Escenario": scenario.name,
                "Centro": scenario.center_option,
                "Inversión": scenario.investment_option_name,
                "Apoyo laboral": scenario.transport_support,
                "Transición": TRANSITION_PHASED if scenario.include_phasing else TRANSITION_DIRECT,
                "Respaldo": _yes_no(scenario.include_backup),
                "Formación": _yes_no(scenario.include_training),
                "Incentivos": _yes_no(scenario.include_incentives),
                "Mes inicio": MONTH_NAMES[scenario.start_month],
            }
        )
    return rows


def _render_guided_scenario_summary(result) -> None:
    summary = (
        result.operational_economic_result.bridge.operational_summary
        if result.operational_economic_result is not None
        else None
    )
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Viabilidad", preliminary_viability(result))
    c2.metric("Centro de reparto", summary.depot_name if summary is not None else "Sin rutas")
    c3.metric("Rutas totales", _fmt_int(summary.total_routes) if summary is not None else "-")
    c4.metric(
        "Vehículos VRP",
        _fmt_int(summary.diesel_count + summary.electric_count) if summary is not None else "-",
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("CAPEX total", _fmt_money(result.capex_total))
    c2.metric("Ahorro neto anual", _fmt_money(result.net_savings_annual))
    c3.metric("Ahorro operativo", _fmt_money(result.adjusted_operational_saving))
    c4.metric("Coste medio riesgos", _fmt_money(result.total_expected_risk_cost))

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Aceptabilidad laboral", result.labor_result.summary.acceptability)
    c2.metric("Alertas cronograma", result.timeline_result.high_severity_warning_count)
    c3.metric("Payback", _fmt_years(result.economic_result.payback_net))
    c4.metric("VAN", _fmt_money(result.economic_result.van))

    st.info(result.interpretation)
    if result.warnings:
        for warning in result.warnings:
            st.warning(warning)


def _comparison_signature(
    build_mode: str,
    scenarios: tuple[ScenarioConfig, ...],
    excluded_names,
    route_params: dict | None,
) -> tuple:
    params_signature = ()
    if route_params:
        params_signature = tuple(
            sorted((key, str(value)) for key, value in route_params.items())
        )
    scenario_signature = tuple(
        (
            scenario.name,
            scenario.center_option,
            scenario.investment_option_name,
            scenario.transport_support,
            scenario.include_phasing,
            scenario.include_backup,
            scenario.start_month,
        )
        for scenario in scenarios
    )
    return build_mode, scenario_signature, tuple(excluded_names), params_signature


def _active_scenario_index(names: list[str]) -> int:
    active = st.session_state.get("active_scenario_name")
    if active in names:
        return names.index(active)
    return 0


def _fmt_optional_money(value) -> str:
    return "-" if pd.isna(value) else _fmt_money(float(value))


def _fmt_optional_int(value) -> str:
    return "-" if pd.isna(value) else _fmt_int(float(value))


def _scenario_decisions_frame(config: ScenarioConfig) -> pd.DataFrame:
    return pd.DataFrame(
        [
            ("Nombre", config.name),
            ("Centro / alternativa", config.center_option),
            ("Inversión", config.investment_option_name),
            ("Apoyo laboral", config.transport_support),
            ("Mes de inicio", MONTH_NAMES[config.start_month]),
            ("Implementación por fases", _yes_no(config.include_phasing)),
            ("Sistemas de respaldo", _yes_no(config.include_backup)),
            ("Formación", _yes_no(config.include_training)),
            ("Incentivos", _yes_no(config.include_incentives)),
            ("Seguros especiales", _yes_no(config.include_insurance)),
            ("Regulación laboral incremental", _yes_no(config.include_labor_regulation)),
            ("DQA4 atribuible/liberable", f"{config.dqa4_attributable_share:.0%}"),
        ],
        columns=["Decisión", "Valor"],
    )


def render_scenario_section(
    pipeline_result=None,
    center_option: str = OPERATIONAL_OPTION_CURRENT,
    route_params: dict | None = None,
) -> None:
    """Renderiza una lectura integrada simple de ScenarioConfig/ScenarioResult."""
    st.markdown(
        "Esta pestaña agrupa decisiones y resultados ya existentes en un escenario actual. "
        "No compara escenarios, no hace ranking y no emite una recomendación automática."
    )
    st.caption(
        "La capa de escenario reutiliza economía, puente operativo, submodelo laboral, "
        "cronograma y riesgos sin recalcular rutas internamente."
    )

    _section_title("Decisiones del escenario")
    c1, c2, c3 = st.columns(3)
    scenario_name = c1.text_input(
        "Nombre del escenario",
        value="Escenario actual",
        key="scenario_name",
    )
    option_name = c2.selectbox(
        "Opción de inversión",
        [option.name for option in DEFAULT_OPTIONS],
        index=1,
        key="scenario_investment_option",
    )
    transport_support = c3.selectbox(
        "Apoyo laboral",
        ["Sin apoyo", "Subsidio transporte público", "Transporte corporativo", "Compensación única"],
        index=1,
        key="scenario_transport_support",
    )

    c1, c2, c3 = st.columns(3)
    start_month = c1.selectbox(
        "Mes de inicio",
        options=list(MONTH_NAMES.keys()),
        index=0,
        format_func=lambda value: MONTH_NAMES[value],
        key="scenario_start_month",
    )
    include_phasing = c2.checkbox(
        "Implementación por fases",
        value=True,
        key="scenario_include_phasing",
    )
    include_backup = c3.checkbox(
        "Sistemas de respaldo",
        value=True,
        key="scenario_include_backup",
    )

    c1, c2, c3, c4 = st.columns(4)
    include_training = c1.checkbox("Formación", value=True, key="scenario_include_training")
    include_incentives = c2.checkbox("Incentivos", value=True, key="scenario_include_incentives")
    include_insurance = c3.checkbox("Seguros especiales", value=True, key="scenario_include_insurance")
    include_regulation = c4.checkbox(
        "Regulación laboral incremental",
        value=False,
        key="scenario_include_regulation",
    )

    config = ScenarioConfig(
        name=scenario_name,
        center_option=center_option,
        investment_option_name=option_name,
        transport_support=transport_support,
        include_phasing=include_phasing,
        include_backup=include_backup,
        include_training=include_training,
        include_incentives=include_incentives,
        include_insurance=include_insurance,
        include_labor_regulation=include_regulation,
        start_month=int(start_month),
    )

    try:
        result = build_scenario_result(
            config,
            pipeline_result=pipeline_result,
            route_params=route_params,
        )
    except Exception as exc:
        st.error(f"No se pudo construir el escenario: {exc}")
        return

    st.dataframe(_scenario_decisions_frame(config), hide_index=True, use_container_width=True)

    _section_title("Resumen integrado")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("CAPEX total", _fmt_money(result.capex_total))
    c2.metric("Ahorro neto anual", _fmt_money(result.net_savings_annual))
    c3.metric("Ahorro operativo ajustado", _fmt_money(result.adjusted_operational_saving))
    c4.metric("Coste medio riesgos", _fmt_money(result.total_expected_risk_cost))

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Aceptabilidad laboral", result.labor_result.summary.acceptability)
    c2.metric("Alertas altas cronograma", result.timeline_result.high_severity_warning_count)
    c3.metric("Rutas usadas", _fmt_int(result.risk_assessment.inputs.total_routes))
    c4.metric("Vehículos VRP", _fmt_int(result.risk_assessment.inputs.vehicle_count))

    _section_title("Interpretación")
    st.info(result.interpretation)

    high_warnings = [
        warning.message
        for warning in result.timeline_result.warnings
        if warning.severity == "alta"
    ]
    if high_warnings:
        with st.expander("Alertas altas del cronograma", expanded=True):
            for warning in high_warnings:
                st.warning(_friendly_timeline_warning(warning))

    display_warnings = _filter_display_warnings(
        result.warnings,
        center_option,
    )
    if display_warnings:
        with st.expander("Warnings del escenario", expanded=True):
            for warning in display_warnings:
                st.warning(warning)
    else:
        st.success("No hay warnings adicionales del escenario con las entradas actuales.")


def render_risk_section(
    pipeline_result=None,
    center_option: str = OPERATIONAL_OPTION_CURRENT,
    route_params: dict | None = None,
) -> None:
    """Renderiza riesgos dependientes de decisiones sin crear escenarios globales."""
    st.markdown(
        "Esta pestaña traduce decisiones actuales en una lectura sencilla de riesgo residual. "
        "No es una simulación ni un escenario global; sirve para ver cómo cambian los riesgos "
        "al tocar centro, rutas, inversión, personas, calendario y mitigaciones."
    )
    st.caption(
        "La fórmula usada es simple: riesgo base x modificadores de probabilidad x "
        "modificadores de impacto = riesgo residual."
    )

    if pipeline_result is None:
        st.info(
            "Calcula primero las rutas para que el riesgo operativo use rutas, distancia, "
            "tiempo, vehículos, dedicadas y trailers reales. Mientras tanto se usa una "
            "lectura conservadora sin ahorro operativo ajustado."
        )

    _section_title("Decisiones principales")
    c1, c2, c3 = st.columns(3)
    option_name = c1.selectbox(
        "Opción de inversión",
        [option.name for option in DEFAULT_OPTIONS],
        index=1,
        key="risk_investment_option",
        help="La inversión básica sube riesgo tecnológico; la premium reduce tecnología pero sube riesgo financiero.",
    )
    transport_support = c2.selectbox(
        "Apoyo laboral",
        ["Sin apoyo", "Subsidio transporte público", "Transporte corporativo", "Compensación única"],
        index=1,
        key="risk_transport_support",
        help="El apoyo laboral reduce riesgo laboral y legal/sindical.",
    )
    seasonality_options = {
        "Base": 1.00,
        "Enero-marzo": 0.85,
        "Julio-septiembre": 1.08,
        "Octubre-diciembre": 1.25,
    }
    route_seasonality = (
        float(route_params.get("seasonality_multiplier", 1.0))
        if route_params is not None
        else 1.0
    )
    seasonality_label = c3.selectbox(
        "Temporada de demanda",
        list(seasonality_options.keys()),
        index=_closest_option_index(seasonality_options, route_seasonality),
        key="risk_seasonality",
        help="La temporada alta aumenta sobre todo el riesgo operativo.",
    )

    c1, c2, c3, c4 = st.columns(4)
    include_phasing = c1.checkbox(
        "Implementación por fases",
        value=True,
        key="risk_include_phasing",
        help="Reduce riesgo operativo, cronograma y legal/sindical.",
    )
    include_backup = c2.checkbox(
        "Sistemas de respaldo",
        value=True,
        key="risk_include_backup",
        help="Reduce riesgo tecnológico y continuidad operativa.",
    )
    include_training = c3.checkbox(
        "Formación",
        value=True,
        key="risk_include_training",
        help="Reduce riesgo laboral y legal/sindical.",
    )
    include_incentives = c4.checkbox(
        "Incentivos",
        value=True,
        key="risk_include_incentives",
        help="Reduce riesgo laboral al mejorar la aceptación del cambio.",
    )

    c1, c2 = st.columns([1, 3])
    start_month = c1.selectbox(
        "Mes de inicio",
        options=list(MONTH_NAMES.keys()),
        index=0,
        format_func=lambda value: MONTH_NAMES[value],
        key="risk_start_month",
        help="El cronograma sube si hitos críticos caen en octubre-diciembre.",
    )
    timeline = build_timeline(int(start_month))
    c2.info(timeline.summary)

    additional = AdditionalCostParams(
        transport_support=transport_support,
        include_mitigation_phasing=include_phasing,
        include_mitigation_backup=include_backup,
        include_training=include_training,
        include_incentives=include_incentives,
    )
    selected_option = next(option for option in DEFAULT_OPTIONS if option.name == option_name)
    economic_result = compute_economic_result(selected_option, additional, FinanceParams())
    labor_result = labor_policy_result_from_additional(additional)

    bridge_result = None
    bridge_warnings: tuple[str, ...] = ()
    if pipeline_result is not None:
        try:
            bridge_result = estimate_operational_cost_bridge(
                pipeline_result=pipeline_result,
                current_costs=CurrentCostParams(),
                vehicle_cost_params=VehicleCostParams(),
                center_option=center_option,
            )
            bridge_warnings = bridge_result.bridge.warnings
        except Exception as exc:
            st.warning(f"No se pudo enlazar rutas con economía para riesgos: {exc}")

    summary = bridge_result.bridge.operational_summary if bridge_result is not None else None
    adjusted_operational_saving = (
        bridge_result.adjusted_operational_saving
        if bridge_result is not None
        else 0.0
    )
    intermediate_approximate = False
    if center_option == OPERATIONAL_OPTION_INTERMEDIATE:
        if pipeline_result is None:
            intermediate_approximate = True
        else:
            depot_name = pipeline_result.dataset.names[pipeline_result.dataset.depot_index]
            intermediate_approximate = _is_virtual_depot_name(depot_name)

    if intermediate_approximate:
        st.warning(
            "El centro intermedio se evalúa como aproximación cuando usa el depot "
            "virtual calculado automáticamente."
        )
    display_bridge_warnings = _filter_display_warnings(
        bridge_warnings,
        center_option,
    )
    if display_bridge_warnings:
        st.warning(" ".join(display_bridge_warnings))

    critical_peak_milestones = sum(
        1 for milestone in timeline.milestones if milestone.in_critical_peak
    )
    inputs = RiskDecisionInputs(
        center_option=center_option,
        investment_option=option_name,
        transport_support=transport_support,
        labor_acceptability=labor_result.summary.acceptability,
        total_routes=summary.total_routes if summary is not None else 0,
        dedicated_routes=summary.dedicated_routes if summary is not None else 0,
        trailer_routes=summary.trailer_routes if summary is not None else 0,
        vehicle_count=(
            summary.diesel_count + summary.electric_count
            if summary is not None
            else 0
        ),
        total_distance_km=summary.total_distance_km if summary is not None else 0.0,
        total_time_min=summary.total_time_min if summary is not None else 0.0,
        seasonality_multiplier=seasonality_options[seasonality_label],
        adjusted_operational_saving=adjusted_operational_saving,
        include_phasing=include_phasing,
        include_backup_systems=include_backup,
        include_training=include_training,
        include_incentives=include_incentives,
        start_month=int(start_month),
        critical_peak_milestone_count=critical_peak_milestones,
        high_severity_timeline_warnings=timeline.high_severity_warning_count,
        intermediate_center_is_approximate=intermediate_approximate,
    )
    assessment = assess_risks(inputs)

    _section_title("Resumen usado por riesgos")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Centro evaluado", center_option)
    c2.metric("Rutas totales", _fmt_int(inputs.total_routes))
    c3.metric("Rutas dedicadas", _fmt_int(inputs.dedicated_routes))
    c4.metric("Trailers", _fmt_int(inputs.trailer_routes))
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Distancia total", f"{_fmt_num(inputs.total_distance_km, 0)} km")
    c2.metric("Tiempo total", f"{_fmt_num(inputs.total_time_min, 0)} min")
    c3.metric("Vehículos VRP", _fmt_int(inputs.vehicle_count))
    c4.metric("Ahorro operativo ajustado", _fmt_money(inputs.adjusted_operational_saving))

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("CAPEX total", _fmt_money(economic_result.capex_total))
    c2.metric("Ahorro neto anual", _fmt_money(economic_result.net_savings_annual))
    c3.metric("Aceptabilidad laboral", labor_result.summary.acceptability)
    c4.metric("Alertas altas cronograma", timeline.high_severity_warning_count)

    _section_title("Tabla de riesgos")
    risk_df = risk_results_frame(assessment.risks)
    display = _pct_df(
        _money_df(
            risk_df,
            [
                "Impacto base si ocurre",
                "Impacto si ocurre",
                "Coste medio base",
                "Coste medio estimado",
            ],
        ),
        ["Probabilidad base", "Probabilidad tras decisiones"],
    )
    st.dataframe(display, hide_index=True, use_container_width=True)

    c1, c2, c3 = st.columns(3)
    c1.metric("Coste medio base total", _fmt_money(assessment.total_base_expected_cost))
    c2.metric("Coste medio total", _fmt_money(assessment.total_residual_expected_cost))
    delta = assessment.total_residual_expected_cost - assessment.total_base_expected_cost
    c3.metric("Cambio por decisiones", _fmt_money(delta))
    st.caption(
        "El coste medio total suma los costes medios estimados residuales. No es una pérdida segura; "
        "es una lectura comparable de exposición."
    )


def render_economics_section(
    pipeline_result=None,
    center_option: str = OPERATIONAL_OPTION_CURRENT,
) -> None:
    """Renderiza la herramienta económica paramétrica."""
    st.markdown(
        "Esta pestaña evalúa si los ahorros atribuibles al flujo SVQ1 → DQA4 compensan la inversión "
        "inicial y los nuevos costes recurrentes."
    )
    st.caption(
        "Los datos base vienen del enunciado y supuestos del proyecto. La vista normal muestra "
        "decisiones principales y la avanzada prueba sensibilidad."
    )
    st.info(
        "La estructura actual mantiene DQA4 como centro de reparto. SVQ1 ampliado prueba "
        "qué pasaría si SVQ1 absorbiera ese flujo. Los ahorros de DQA4 no deben "
        "interpretarse como cierre completo de DQA4."
    )
    mode = st.radio(
        "Modo de análisis",
        ["Vista normal", "Vista avanzada"],
        horizontal=True,
        help="Vista normal protege los datos base y muestra decisiones clave; vista avanzada expone parámetros editables.",
    )
    if mode == "Vista normal":
        _render_economics_normal_view(pipeline_result, center_option)
    else:
        _render_economics_advanced_view(pipeline_result, center_option)
