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

from .economics_model import (
    DEFAULT_OPTIONS,
    DEFAULT_RISKS,
    AdditionalCostParams,
    CurrentCostParams,
    FinanceParams,
    InvestmentOption,
    Risk,
    VehicleCostParams,
    additional_capex_opex,
    analyze_options,
    compute_economic_results,
    current_cost_frame,
    economic_results_frame,
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
    with st.expander("Parámetros de dimensionamiento", expanded=True):
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
    with st.expander("Parámetros del método f", expanded=True):
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
    with st.expander("Parámetros de comparación ABC (`Almacen_vs.m`)", expanded=True):
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
        "Modelos Python equivalentes a `Almacen_dimension.m`, `Almacen_1floor.m`, "
        "`Almacen_3floor.m`, `Almacen_vs.m` y `Almacen_resultado_variable_3.m`."
    )
    tab_dimension, tab_layout, tab_vs, tab_sensitivity = st.tabs(
        ["Dimensionamiento", "Layout ABC", "Comparación ABC", "Sensibilidad ABC"]
    )

    with tab_dimension:
        params = _dimension_controls()
        result = compute_dimension(params)
        _section_title("Resultado de capacidad")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Capacidad total", _fmt_int(result.total_capacity))
        c2.metric("Capacidad/planta", _fmt_int(result.capacity_per_floor))
        c3.metric("Estanterías/planta", _fmt_int(result.shelves_per_floor))
        c4.metric("Huecos/estantería", _fmt_int(result.slots_per_shelf))

        st.dataframe(result.metrics_frame(), hide_index=True, use_container_width=True)

        abc = result.abc_frame()
        abc["Paquetes"] = abc["Paquetes"].apply(_fmt_int)
        st.dataframe(abc, hide_index=True, use_container_width=True)

    with tab_layout:
        params = _layout_controls("layout")
        layout = solve_layout(params)
        _section_title("Resultado del layout")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Coste ABC global", _fmt_num(layout.cost_global, 2))
        c2.metric("Penalización/planta", f"{layout.vertical_penalty_cells:.2f} celdas")
        c3.metric("Inventario C", f"{params.pct_c:.1%}")
        c4.metric("Movimientos C", f"{params.move_c:.1%}")

        floor_summary = floor_cost_summary(layout)
        numeric_cols = ["Penalización vertical (celdas)", "Penalización vertical (m)", "f mínimo", "f medio", "f máximo"]
        floor_display = floor_summary.copy()
        for col in numeric_cols:
            floor_display[col] = floor_display[col].apply(lambda x: _fmt_num(float(x), 2))
        st.dataframe(floor_display, hide_index=True, use_container_width=True)

        strategy = st.radio(
            "Zonificación a visualizar",
            ["ABC global 3D", "ABC por planta"],
            horizontal=True,
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

    with tab_vs:
        params = _vs_controls("vs")
        layout = solve_layout(params)
        _section_title("ABC individual por planta vs ABC global 3D")
        st.markdown(
            "`Almacen_vs.m` compara dos reglas de asignación sobre el mismo "
            "edificio 3D: una fuerza el reparto A/B/C en cada planta y la otra "
            "ordena todas las posiciones del edificio por índice `f` antes de "
            "asignar las zonas."
        )

        c1, c2, c3 = st.columns(3)
        c1.metric("Coste ABC por planta", _fmt_num(layout.cost_by_floor, 2))
        c2.metric("Coste ABC global 3D", _fmt_num(layout.cost_global, 2))
        c3.metric("Mejora global", f"{layout.improvement_pct:.2f}%")

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
            "por planta explica de dónde sale la mejora: en el ABC global, la "
            "zona A se concentra en las posiciones de menor `f`, normalmente en "
            "plantas inferiores y cerca de las puertas, mientras que el método "
            "por planta reserva A/B/C dentro de cada planta aunque su coste "
            "vertical sea mayor."
        )

    with tab_sensitivity:
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
        c1, c2, c3 = st.columns(3)
        personal_svq1 = c1.number_input("Personal SVQ1 (M€/año)", 0.0, 100.0, 20.7, 0.1) * 1e6
        personal_dqa4 = c1.number_input("Personal DQA4 (M€/año)", 0.0, 100.0, 9.1, 0.1) * 1e6
        energy_svq1 = c2.number_input("Energía SVQ1 (M€/año)", 0.0, 100.0, 6.2, 0.1) * 1e6
        energy_dqa4 = c2.number_input("Energía DQA4 (M€/año)", 0.0, 100.0, 4.7, 0.1) * 1e6
        facilities_svq1 = c3.number_input("Instalaciones SVQ1 (M€/año)", 0.0, 100.0, 2.4, 0.1) * 1e6
        facilities_dqa4 = c3.number_input("Instalaciones DQA4 (M€/año)", 0.0, 100.0, 1.5, 0.1) * 1e6

        c1, c2, c3 = st.columns(3)
        other_svq1 = c1.number_input("Otros SVQ1 (M€/año)", 0.0, 100.0, 7.0, 0.1) * 1e6
        other_dqa4 = c1.number_input("Otros DQA4 (M€/año)", 0.0, 100.0, 2.8, 0.1) * 1e6
        transfer_cost = c2.number_input("Coste transferencias (M€/año)", 0.0, 50.0, 1.99, 0.01) * 1e6
        transfer_daily = c2.number_input("Paquetes transferidos/día", 0, 200_000, 26_100, 100)
        transfer_distance = c3.number_input("Distancia SVQ1-DQA4 (km)", 0.0, 200.0, 25.0, 1.0)
        days = c3.number_input("Días/año", 1, 366, 365, 1)
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
        options: list[InvestmentOption] = []
        for default in DEFAULT_OPTIONS:
            st.markdown(f"**{default.name}**")
            c1, c2, c3, c4 = st.columns(4)
            opt_key = f"{prefix}_{default.name}"
            capex = c1.number_input(f"CAPEX base {default.name} (M€)", 0.0, 200.0, default.capex_base / 1e6, 0.1, key=f"{opt_key}_capex") * 1e6
            infra = c2.number_input(f"Infra {default.name} (M€)", 0.0, 200.0, default.capex_infra / 1e6, 0.1, key=f"{opt_key}_infra") * 1e6
            tech = c3.number_input(f"Tech {default.name} (M€)", 0.0, 200.0, default.capex_tech / 1e6, 0.1, key=f"{opt_key}_tech") * 1e6
            it = c4.number_input(f"IT {default.name} (M€)", 0.0, 200.0, default.capex_it / 1e6, 0.1, key=f"{opt_key}_it") * 1e6
            c1, c2 = st.columns(2)
            savings = c1.number_input(f"Ahorro bruto {default.name} (M€/año)", 0.0, 100.0, default.gross_savings / 1e6, 0.1, key=f"{opt_key}_savings") * 1e6
            robots = c2.number_input(
                f"Robots {default.name}",
                0,
                5_000,
                int(default.robots_total or 0),
                10,
                key=f"{opt_key}_robots",
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
        c1, c2, c3 = st.columns(3)
        training = c1.number_input("Formación (M€ CAPEX)", 0.0, 50.0, 1.56, 0.01, key=f"{prefix}_training") * 1e6
        phasing = c2.number_input("Implementación por fases (M€ CAPEX)", 0.0, 50.0, 2.20, 0.01, key=f"{prefix}_phasing") * 1e6
        backup = c3.number_input("Sistemas respaldo (M€ CAPEX)", 0.0, 50.0, 1.80, 0.01, key=f"{prefix}_backup") * 1e6
        c1, c2, c3 = st.columns(3)
        incentives = c1.number_input("Incentivos empleados (M€)", 0.0, 50.0, 0.68, 0.01, key=f"{prefix}_incentives") * 1e6
        incentive_capex_share = c2.slider("% incentivos como CAPEX", 0.0, 100.0, 50.0, 5.0, key=f"{prefix}_incentive_share") / 100.0
        insurance = c3.number_input("Seguros especiales (M€/año)", 0.0, 50.0, 0.45, 0.01, key=f"{prefix}_insurance") * 1e6

        c1, c2, c3 = st.columns(3)
        support = c1.selectbox(
            "Apoyo empleados DQA4",
            ["Subsidio transporte público", "Transporte corporativo", "Compensación única", "Sin apoyo"],
            key=f"{prefix}_support",
        )
        include_regulation = c2.checkbox("Tratar regulación 2025 como incremental", value=False, key=f"{prefix}_include_reg")
        regulation = c3.number_input("Regulación 2025 (M€/año)", 0.0, 50.0, 3.25, 0.01, key=f"{prefix}_regulation") * 1e6

        c1, c2, c3 = st.columns(3)
        discount_rate = c1.slider("Tasa descuento (%)", 0.0, 25.0, 7.0, 0.25, key=f"{prefix}_discount") / 100.0
        horizon = c2.number_input("Horizonte (años)", 1, 30, 10, 1, key=f"{prefix}_horizon")
        pess_capex = c3.slider("Pesimista: CAPEX x", 1.0, 2.0, 1.30, 0.05, key=f"{prefix}_pess_capex")
        pess_savings = c3.slider("Pesimista: ahorro x", 0.1, 1.0, 0.75, 0.05, key=f"{prefix}_pess_savings")

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
    with st.expander("Costes de flota", expanded=True):
        c1, c2, c3 = st.columns(3)
        vans_a = c1.number_input("Furgonetas sin km ni dietas", 0, 1_000, 26, 1)
        vans_b = c2.number_input("Furgonetas sin km con dietas", 0, 1_000, 19, 1)
        vans_c = c3.number_input("Furgonetas con km y dietas", 0, 1_000, 75, 1)
        c1, c2, c3 = st.columns(3)
        subcontracted = c1.number_input("Furgonetas subcontratadas", 0, 1_000, 51, 1)
        trailer_a = c2.number_input("Trailers con km y dietas", 0, 100, 1, 1)
        trailer_b = c3.number_input("Trailers sin dietas", 0, 100, 6, 1)

        c1, c2, c3 = st.columns(3)
        unit_a = c1.number_input("€/año furgo sin km/dietas", 0.0, 500_000.0, 48_370.93, 100.0)
        unit_b = c2.number_input("€/año furgo con dietas", 0.0, 500_000.0, 54_739.73, 100.0)
        unit_c = c3.number_input("€/año furgo km+dietas", 0.0, 500_000.0, 61_012.93, 100.0)
        c1, c2, c3 = st.columns(3)
        unit_sub = c1.number_input("€/año subcontratada", 0.0, 500_000.0, 45_000.0, 100.0)
        unit_trailer_a = c2.number_input("€/año trailer km+dietas", 0.0, 1_000_000.0, 147_422.32, 100.0)
        unit_trailer_b = c3.number_input("€/año trailer sin dietas", 0.0, 1_000_000.0, 141_053.52, 100.0)
        baseline = st.number_input("Escenario sin unificar: total rutas (M€)", 0.0, 100.0, 10.04038638, 0.01)

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


def render_economics_section() -> None:
    """Renderiza la herramienta económica paramétrica."""
    st.markdown(
        "Modelo Python equivalente a `Economia.m`, ampliado con costes de flota "
        "parametrizables a partir del Excel de vehículos."
    )
    tab_current, tab_investment, tab_fleet, tab_risk = st.tabs(
        ["Costes actuales", "Inversión y VAN", "Flota", "Riesgos"]
    )

    with tab_current:
        params = _current_cost_controls()
        current = current_cost_frame(params)
        _section_title("As-is")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Coste actual total", _fmt_money(total_current_cost(params)))
        c2.metric("Transferencias", _fmt_money(params.transfer_annual_cost))
        c3.metric("Coste/paquete transferido", f"{transfer_unit_cost(params):.4f} €")
        c4.metric("Distancia transferencia", f"{params.transfer_distance_km:.1f} km")
        st.dataframe(_money_df(current, ["SVQ1", "DQA4", "Total"]), hide_index=True, use_container_width=True)
        st.plotly_chart(
            _bar_chart(current, "Concepto", ["SVQ1", "DQA4"], "Desglose anual de costes actuales"),
            use_container_width=True,
        )

    with tab_investment:
        options, additional, finance = _investment_controls("investment")
        structured_results = compute_economic_results(options, additional, finance)
        results = economic_results_frame(structured_results)
        recommended = recommend_option(results)
        extra_capex, extra_opex, extra_frame = additional_capex_opex(additional)

        _section_title("Resultados financieros")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Opción recomendada", recommended)
        c2.metric("CAPEX transición", _fmt_money(extra_capex))
        c3.metric("OPEX nuevo", _fmt_money(extra_opex))
        best_result = next(result for result in structured_results if result.option_name == recommended)
        c4.metric("VAN recomendado", _fmt_money(best_result.van))

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
            display[col] = display[col].apply(lambda x: "-" if pd.isna(x) else f"{x:.2%}")
        for col in ["Payback neto", "Payback pesimista"]:
            display[col] = display[col].apply(lambda x: "∞" if np.isinf(x) else f"{x:.2f} años")
        st.dataframe(display, hide_index=True, use_container_width=True)

        st.dataframe(_money_df(extra_frame, ["Importe"]), hide_index=True, use_container_width=True)

        labor_result = labor_policy_result_from_additional(additional)
        labor_summary = labor_result.summary
        with st.expander("Resumen laboral", expanded=False):
            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("Empleados DQA4 afectados", _fmt_int(labor_summary.affected_employees))
            c2.metric("Desplazamiento extra", f"{labor_summary.additional_commute_km_daily:.1f} km/día")
            c3.metric("Coste único laboral", _fmt_money(labor_summary.oneoff_cost))
            c4.metric("Coste anual laboral", _fmt_money(labor_summary.annual_recurring_cost))
            c5.metric("Aceptabilidad", labor_summary.acceptability)
            c1, c2 = st.columns(2)
            c1.metric("Riesgo laboral esperado", _fmt_money(labor_summary.expected_risk_cost))
            c2.metric("Riesgo laboral residual", _fmt_money(labor_summary.residual_risk_cost))
            st.dataframe(
                _money_df(labor_cost_frame(labor_result.cost_lines), ["Importe"]),
                hide_index=True,
                use_container_width=True,
            )
            labor_risks = labor_risk_frame(labor_result.risk_results)
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

        chart_df = results[["Opción", "CAPEX total", "VAN", "VAN pesimista"]]
        st.plotly_chart(
            _bar_chart(chart_df, "Opción", ["CAPEX total", "VAN", "VAN pesimista"], "CAPEX y VAN por opción"),
            use_container_width=True,
        )

    with tab_fleet:
        params = _vehicle_controls()
        df = vehicle_cost_frame(params)
        totals = vehicle_totals(params)
        _section_title("Costes anuales de rutas")
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
        st.plotly_chart(
            _bar_chart(df, "Bloque", ["Coste anual"], "Costes de flota por bloque"),
            use_container_width=True,
        )

    with tab_risk:
        options, additional, finance = _investment_controls("risk")
        results = analyze_options(options, additional, finance)
        selected_name = st.selectbox("Opción para riesgo de construcción", [o.name for o in options], index=1)
        selected_option = next(o for o in options if o.name == selected_name)

        st.markdown("**Riesgos cuantificados**")
        risks: list[Risk] = []
        for idx, default in enumerate(DEFAULT_RISKS):
            c1, c2, c3 = st.columns(3)
            name = c1.text_input(f"Riesgo {idx + 1}", default.name, key=f"risk_name_{idx}")
            prob = c2.slider(f"Probabilidad {idx + 1} (%)", 0.0, 100.0, default.probability * 100.0, 1.0, key=f"risk_prob_{idx}") / 100.0
            cost = c3.number_input(f"Coste {idx + 1} (M€)", 0.0, 100.0, default.cost_if_occurs / 1e6, 0.1, key=f"risk_cost_{idx}") * 1e6
            risks.append(Risk(name, prob, cost))

        include_construction = st.checkbox("Añadir sobrecoste construcción como 30% del CAPEX base", value=True)
        if include_construction:
            risks.append(Risk("Sobrecostes construcción (+30%)", 0.35, selected_option.capex_base * 0.30))
        storm_prob = st.slider("Probabilidad tormenta perfecta (%)", 0.0, 25.0, 3.0, 0.5) / 100.0
        storm_cost = st.number_input("Coste tormenta perfecta (M€)", 0.0, 100.0, 15.2, 0.1) * 1e6
        risks.append(Risk("Tormenta perfecta", storm_prob, storm_cost))

        rf = risk_frame(risks, selected_option)
        c1, c2 = st.columns(2)
        c1.metric("Valor esperado total", _fmt_money(rf["Valor esperado"].sum()))
        recommended = recommend_option(results)
        c2.metric("Opción financiera recomendada", recommended)
        st.dataframe(
            _pct_df(_money_df(rf, ["Coste si ocurre", "Valor esperado"]), ["Probabilidad"]),
            hide_index=True,
            use_container_width=True,
        )
