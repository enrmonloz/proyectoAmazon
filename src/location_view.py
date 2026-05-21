"""Visualización interactiva de resultados de localización.

Este módulo proporciona funciones para visualizar en mapas (Folium) y gráficos
(Plotly) los resultados de localización de centros de reparto.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

import folium
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st


from .location_solver import (
    CandidateComparisonResult,
    CandidateType,
    LocationResult,
    LocationSolver,
)


def build_location_map(
    dataset,
    result: LocationResult,
    show_distance_rings: bool = False,
    include_hubs: bool = True,
) -> folium.Map:
    """Construye un mapa Folium con la localización óptima y los municipios.

    Parámetros:
        dataset: Dataset con coordenadas y población de municipios.
        result: LocationResult con la ubicación óptima.
        show_distance_rings: si True, dibuja anillos de distancia concéntricos.
        include_hubs: si True, marca los centros logísticos (SVQ1, DQA4).

    Retorna:
        Mapa Folium listo para renderizar.
    """
    # Centro geográfico del mapa
    center_lat = np.mean(dataset.latitudes)
    center_lon = np.mean(dataset.longitudes)

    # Crear mapa centrado
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=9,
        tiles="OpenStreetMap",
    )

    # Identificar centros logísticos y municipios de demanda
    is_hub = dataset.poblacion == 0
    is_demand = dataset.poblacion > 0

    # 1. Dibujar municipios de demanda como burbujas (tamaño proporcional a población)
    demand_indices = np.where(is_demand)[0]
    poblacion_norm = dataset.poblacion[demand_indices] / dataset.poblacion[demand_indices].max()
    for idx_pos, i in enumerate(demand_indices):
        radius = max(10, float(poblacion_norm[idx_pos]) * 30)
        folium.CircleMarker(
            location=[dataset.latitudes[i], dataset.longitudes[i]],
            radius=radius,
            popup=f"{dataset.names[i]}<br>Población: {int(dataset.poblacion[i]):,}",
            tooltip=dataset.names[i],
            color="#5B9BD5",
            fill=True,
            fillColor="#5B9BD5",
            fillOpacity=0.6,
            weight=1,
        ).add_to(m)

    # 2. Dibujar centros logísticos (si include_hubs=True)
    if include_hubs:
        for i in np.where(is_hub)[0]:
            icon_color = "#EDB120" if dataset.names[i] == "DQA4" else "#FF0000"
            folium.Marker(
                location=[dataset.latitudes[i], dataset.longitudes[i]],
                popup=f"{dataset.names[i]} (Centro Logístico)",
                tooltip=dataset.names[i],
                icon=folium.Icon(color=icon_color, icon="warehouse", prefix="fa"),
            ).add_to(m)

    # 3. Dibujar ubicación óptima
    folium.Marker(
        location=[result.latitude, result.longitude],
        popup=(
            f"<b>Referencia calculada ({result.method.value.replace('_', ' ').title()})</b><br>"
            f"Municipio más cercano: {result.nearest_municipality}<br>"
            f"Distancia: {result.distance_to_nearest_km:.2f} km<br>"
            f"Distancia total ponderada: {result.weighted_distance:,.1f}<br>"
            f"Distancia máxima ponderada: {result.max_weighted_distance:,.1f}"
        ),
        tooltip="Referencia calculada",
        icon=folium.Icon(color="green", icon="star", prefix="fa"),
    ).add_to(m)

    # 4. Dibujar anillos de distancia (opcional)
    if show_distance_rings:
        distances_km = [50, 100, 150]
        colors = ["#90EE90", "#FFD700", "#FF6347"]
        for dist_km, color in zip(distances_km, colors):
            folium.Circle(
                location=[result.latitude, result.longitude],
                radius=dist_km * 1000,  # Convertir a metros
                popup=f"{dist_km} km",
                color=color,
                fill=False,
                weight=1,
                opacity=0.5,
            ).add_to(m)

    return m


def build_comparison_map(
    dataset,
    solutions: dict,  # dict de LocationResult por método
) -> folium.Map:
    """Construye un mapa con múltiples soluciones superpuestas (una por cada método).

    Parámetros:
        dataset: Dataset con coordenadas.
        solutions: Diccionario {método: LocationResult}.

    Retorna:
        Mapa Folium con todas las soluciones marcadas.
    """
    center_lat = np.mean(dataset.latitudes)
    center_lon = np.mean(dataset.longitudes)

    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=9,
        tiles="OpenStreetMap",
    )

    # Colores para cada método
    colors = {
        "gravity_center": "blue",
        "min_total_distance": "purple",
        "minimax": "red",
        "geographic_center": "gray",
        "k_median": "orange",
    }

    # Dibujar cada solución
    for method_name, result in solutions.items():
        color = colors.get(method_name, "gray")
        folium.Marker(
            location=[result.latitude, result.longitude],
            popup=(
                f"<b>{method_name.replace('_', ' ').title()}</b><br>"
                f"Municipio: {result.nearest_municipality}<br>"
                f"Dist. total: {result.weighted_distance:,.1f}"
            ),
            tooltip=method_name,
            icon=folium.Icon(color=color, icon="map-pin", prefix="fa"),
        ).add_to(m)

    # Dibujar municipios de demanda
    is_demand = dataset.poblacion > 0
    demand_indices = np.where(is_demand)[0]
    poblacion_norm = dataset.poblacion[demand_indices] / dataset.poblacion[demand_indices].max()
    for idx_pos, i in enumerate(demand_indices):
        radius = max(5, float(poblacion_norm[idx_pos]) * 20)
        folium.CircleMarker(
            location=[dataset.latitudes[i], dataset.longitudes[i]],
            radius=radius,
            color="#5B9BD5",
            fill=True,
            fillColor="#5B9BD5",
            fillOpacity=0.4,
            weight=0.5,
        ).add_to(m)

    return m


def _candidate_type_label(candidate_type: CandidateType) -> str:
    labels = {
        CandidateType.EXISTING_HUB: "Candidato existente",
        CandidateType.OPERATIONAL_REFERENCE: "Referencia operativa",
        CandidateType.MATHEMATICAL_REFERENCE: "Referencia matemática",
        CandidateType.HEURISTIC_INTERMEDIATE: "Intermedio aproximado",
    }
    return labels.get(candidate_type, str(candidate_type))


def _friendly_source_label(source: str) -> str:
    mapping = {
        "matriz OD de distancia": "tabla de distancias entre puntos",
        "matriz OD de tiempo": "tabla de tiempos entre puntos",
        "aproximacion Haversine": "distancia geografica aproximada",
        "geométrica euclídea común": "distancia geometrica euclidea comun",
        "tiempo no disponible": "tiempo no disponible",
    }
    return mapping.get(source, source)


def _candidate_display_name(candidate: LocationCandidate) -> str:
    name = candidate.name
    if candidate.candidate_type == CandidateType.MATHEMATICAL_REFERENCE:
        name = name.replace("Optimo continuo", "Referencia matemática")
    if candidate.candidate_type == CandidateType.HEURISTIC_INTERMEDIATE:
        name = name.replace("Intermedio heuristico", "Intermedio aproximado")
    return name


def build_candidate_comparison_map(
    dataset,
    comparison: CandidateComparisonResult,
) -> folium.Map:
    """Construye un mapa con los candidatos discretos y referencias."""
    center_lat = np.mean(dataset.latitudes)
    center_lon = np.mean(dataset.longitudes)

    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=9,
        tiles="OpenStreetMap",
    )

    is_demand = dataset.poblacion > 0
    demand_indices = np.where(is_demand)[0]
    poblacion_norm = dataset.poblacion[demand_indices] / dataset.poblacion[demand_indices].max()
    for idx_pos, i in enumerate(demand_indices):
        radius = max(4, float(poblacion_norm[idx_pos]) * 18)
        folium.CircleMarker(
            location=[dataset.latitudes[i], dataset.longitudes[i]],
            radius=radius,
            color="#5B9BD5",
            fill=True,
            fillColor="#5B9BD5",
            fillOpacity=0.35,
            weight=0.5,
            tooltip=dataset.names[i],
        ).add_to(m)

    colors = {
        CandidateType.EXISTING_HUB: "red",
        CandidateType.OPERATIONAL_REFERENCE: "orange",
        CandidateType.MATHEMATICAL_REFERENCE: "green",
        CandidateType.HEURISTIC_INTERMEDIATE: "purple",
    }
    icons = {
        CandidateType.EXISTING_HUB: "warehouse",
        CandidateType.OPERATIONAL_REFERENCE: "flag",
        CandidateType.MATHEMATICAL_REFERENCE: "star",
        CandidateType.HEURISTIC_INTERMEDIATE: "map-marker",
    }

    for evaluation in comparison.evaluations:
        candidate = evaluation.candidate
        display_name = _candidate_display_name(candidate)
        time_text = (
            f"{evaluation.weighted_mean_time_min:.1f} min"
            if evaluation.weighted_mean_time_min is not None
            else "No disponible"
        )
        popup = (
            f"<b>{display_name}</b><br>"
            f"Tipo: {_candidate_type_label(candidate.candidate_type)}<br>"
            f"Distancia media ponderada: {evaluation.weighted_mean_distance_km:.2f} km<br>"
            f"Distancia maxima: {evaluation.max_distance_km:.2f} km<br>"
            f"Tiempo medio: {time_text}<br>"
            f"Distancia: {_friendly_source_label(evaluation.distance_source)}<br>"
            f"Tiempo: {_friendly_source_label(evaluation.time_source)}"
        )
        folium.Marker(
            location=[candidate.latitude, candidate.longitude],
            popup=popup,
            tooltip=display_name,
            icon=folium.Icon(
                color=colors.get(candidate.candidate_type, "gray"),
                icon=icons.get(candidate.candidate_type, "map-marker"),
                prefix="fa",
            ),
        ).add_to(m)

    return m


def create_distance_heatmap(
    dataset,
    result: LocationResult,
) -> go.Figure:
    """Crea un gráfico de distancia por municipio desde la ubicación óptima.

    Parámetros:
        dataset: Dataset con municipios.
        result: LocationResult con la ubicación óptima.

    Retorna:
        Figura Plotly con gráfico de barras.
    """
    distances = np.sqrt(
        (result.longitude - dataset.longitudes) ** 2
        + (result.latitude - dataset.latitudes) ** 2
    )

    # Haversine más preciso
    R = 6371
    lat1 = np.radians(result.latitude)
    lon1 = np.radians(result.longitude)
    lat2 = np.radians(dataset.latitudes)
    lon2 = np.radians(dataset.longitudes)
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    c = 2 * np.arcsin(np.sqrt(a))
    distances_km = R * c

    # Filtrar solo municipios con demanda
    is_demand = dataset.poblacion > 0
    names_demand = [dataset.names[i] for i in range(len(dataset.names)) if is_demand[i]]
    distances_demand = [distances_km[i] for i in range(len(distances_km)) if is_demand[i]]

    # Ordenar por distancia
    sorted_indices = np.argsort(distances_demand)
    sorted_names = [names_demand[i] for i in sorted_indices]
    sorted_distances = [distances_demand[i] for i in sorted_indices]

    fig = go.Figure(
        data=[
            go.Bar(
                y=sorted_names[:30],  # Top 30 municipios más lejanos
                x=sorted_distances[:30],
                orientation="h",
                marker=dict(color=sorted_distances[:30], colorscale="Reds"),
            )
        ]
    )
    fig.update_layout(
        title=f"Distancia desde referencia calculada ({result.method.value})",
        xaxis_title="Distancia (km)",
        yaxis_title="Municipio",
        height=500,
        showlegend=False,
    )

    return fig


def create_population_coverage_chart(
    dataset,
    result: LocationResult,
    distance_thresholds: Optional[List[float]] = None,
) -> go.Figure:
    """Crea un gráfico de cobertura de población por rangos de distancia.

    Parámetros:
        dataset: Dataset con población.
        result: LocationResult con ubicación óptima.
        distance_thresholds: Lista de distancias (km) para evaluar cobertura.
                            Por defecto: [25, 50, 75, 100, 150, 200].

    Retorna:
        Figura Plotly con gráfico de área.
    """
    if distance_thresholds is None:
        distance_thresholds = [25, 50, 75, 100, 150, 200]

    # Calcular distancias Haversine
    R = 6371
    lat1 = np.radians(result.latitude)
    lon1 = np.radians(result.longitude)
    lat2 = np.radians(dataset.latitudes)
    lon2 = np.radians(dataset.longitudes)
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    c = 2 * np.arcsin(np.sqrt(a))
    distances_km = R * c

    # Calcular población dentro de cada radio
    is_demand = dataset.poblacion > 0
    coverage = []
    coverage_pct = []

    total_population = dataset.poblacion[is_demand].sum()

    for dist in distance_thresholds:
        covered = (distances_km[is_demand] <= dist).sum()
        covered_pop = dataset.poblacion[is_demand][distances_km[is_demand] <= dist].sum()
        coverage.append(covered_pop)
        coverage_pct.append(100 * covered_pop / total_population)

    fig = go.Figure(
        data=[
            go.Scatter(
                x=[str(d) for d in distance_thresholds],
                y=coverage_pct,
                fill="tozeroy",
                mode="lines+markers",
                line=dict(color="#5B9BD5", width=2),
                marker=dict(size=8),
            )
        ]
    )
    fig.update_layout(
        title="Cobertura de población por distancia",
        xaxis_title="Distancia máxima (km)",
        yaxis_title="Población cubierta (%)",
        yaxis_range=[0, 105],
        height=400,
        showlegend=False,
    )

    return fig


def _format_integrated_comparison_frame(frame: pd.DataFrame) -> pd.DataFrame:
    display = frame.copy()
    for col in ["Latitud", "Longitud"]:
        if col in display.columns:
            display[col] = display[col].apply(lambda v: f"{float(v):.4f}")
    for col in ["Distancia media (km)", "Distancia total (km)", "Distancia maxima (km)"]:
        if col in display.columns:
            display[col] = display[col].apply(lambda v: f"{float(v):.2f}")
    if "Delta vs mejor (%)" in display.columns:
        display["Delta vs mejor (%)"] = display["Delta vs mejor (%)"].apply(
            lambda v: f"{float(v):.1f}%"
        )
    return display


def render_integrated_comparison_view(dataset, solver: LocationSolver) -> None:
    """Renderiza la comparacion integrada de tecnicas y candidatos."""
    st.markdown("### Comparación integrada de localización")
    st.caption(
        "Todas las tecnicas y candidatos se comparan con distancia euclidea comun en km. "
        "La matriz OD queda reservada para el analisis de rutas."
    )

    frame = solver.build_full_location_comparison()
    if frame.empty:
        st.warning("No se pudo construir la comparación integrada de localización.")
        return

    best = frame.iloc[0]
    c1, c2, c3 = st.columns(3)
    c1.metric("Mejor accesibilidad", best["Nombre"])
    c2.metric("Distancia media", f"{best['Distancia media (km)']:.2f} km")
    c3.metric("Distancia maxima", f"{best['Distancia maxima (km)']:.2f} km")

    st.dataframe(
        _format_integrated_comparison_frame(frame),
        hide_index=True,
        use_container_width=True,
    )
    st.caption(
        "La tabla integra referencias matematicas y candidatos reales en la misma escala. "
        "\"Uso en rutas\" indica si hay OD existente, si requiere una tabla externa o si es proxy academico."
    )


def render_location_results(dataset, result: LocationResult) -> None:
    """Renderiza un panel completo de resultados de localización en Streamlit.

    Parámetros:
        dataset: Dataset con municipios.
        result: LocationResult con la solución calculada.
    """
    st.markdown("### Resultados de Localización")
    st.caption(
        "Esta vista calcula una referencia matemática con población como peso. "
        "No representa una parcela real ni decide por sí sola la ubicación final."
    )

    # Métricas clave
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Latitud", f"{result.latitude:.4f}")
    col2.metric("Longitud", f"{result.longitude:.4f}")
    col3.metric("Municipio más cercano", result.nearest_municipality)
    col4.metric("Distancia (km)", f"{result.distance_to_nearest_km:.2f}")

    col1b, col2b = st.columns(2)
    col1b.metric("Distancia total ponderada", f"{result.weighted_distance:,.0f}")
    col2b.metric("Distancia máxima ponderada", f"{result.max_weighted_distance:,.0f}")
    st.caption(
        "La distancia ponderada da más peso a municipios con más población. "
        "El municipio más cercano sirve para aterrizar el resultado continuo."
    )
    with st.expander("¿Cómo interpretar estos resultados?", expanded=False):
        st.markdown(
            "- La referencia continua es útil para orientación, no como decisión inmobiliaria.\n"
            "- La distancia total ponderada resume el esfuerzo agregado hacia la demanda.\n"
            "- La distancia máxima ayuda a ver el peor caso aproximado.\n"
            "- La decisión final debe cruzarse con economía, riesgos, personas y calendario."
        )

    # Mapa principal
    st.markdown("### Visualización Geográfica")
    st.caption(
        "El mapa ubica municipios, centros existentes y la solución calculada. "
        "La visualización es orientativa."
    )
    m = build_location_map(dataset, result, show_distance_rings=True)
    from streamlit_folium import st_folium

    st_folium(m, height=500, use_container_width=True)

    # Gráficos adicionales
    col_left, col_right = st.columns(2)

    with col_left:
        st.markdown("### Cobertura de Población")
        st.caption("Muestra qué proporción de población queda dentro de cada radio de distancia.")
        fig_coverage = create_population_coverage_chart(dataset, result)
        st.plotly_chart(fig_coverage, use_container_width=True)

    with col_right:
        st.markdown("### Distancias a Municipios")
        st.caption("Ordena municipios por distancia aproximada desde la ubicación calculada.")
        fig_distances = create_distance_heatmap(dataset, result)
        st.plotly_chart(fig_distances, use_container_width=True)


def render_comparison_view(dataset, solver: LocationSolver) -> None:
    """Renderiza un panel comparativo de todas las técnicas de localización.

    Parámetros:
        dataset: Dataset con municipios.
        solver: LocationSolver inicializado.
    """
    st.markdown("### Comparación de Técnicas de Localización")
    st.caption(
        "Compara métodos matemáticos sobre los mismos datos de población y coordenadas. "
        "Sirve para ver sensibilidad, no para elegir un candidato real por sí sola."
    )
    with st.expander("Supuestos de comparación", expanded=False):
        st.markdown(
            "- Todos los métodos usan nodos de demanda ponderados por población.\n"
            "- Las soluciones continuas son referencias matemáticas.\n"
            "- Si una solución no coincide con un nodo real, debe revisarse como concepto, no como parcela."
        )

    # Tabla comparativa
    st.markdown("#### Tabla Comparativa")
    comparison_df = solver.compare_solutions()
    st.dataframe(comparison_df, use_container_width=True, hide_index=True)
    st.caption("Mira si varios métodos convergen a zonas parecidas o si el resultado depende mucho de la técnica.")

    # Mapa con todas las soluciones
    st.markdown("#### Referencias calculadas por método")
    solutions = solver.get_all_solutions()
    m_comparison = build_comparison_map(dataset, solutions)
    from streamlit_folium import st_folium

    st_folium(m_comparison, height=500, use_container_width=True)

    # Tabla detallada de desempeño
    st.markdown("#### Análisis de Desempeño")
    perf_rows = []
    for method_name, result in solutions.items():
        perf_rows.append(
            {
                "Método": method_name.replace("_", " ").title(),
                "Lat": f"{result.latitude:.4f}",
                "Lon": f"{result.longitude:.4f}",
                "Dist. Total": f"{result.weighted_distance:,.0f}",
                "Dist. Máx": f"{result.max_weighted_distance:,.0f}",
                "Municipio": result.nearest_municipality,
                "Km al municipio": f"{result.distance_to_nearest_km:.2f}",
            }
        )
    st.dataframe(pd.DataFrame(perf_rows), use_container_width=True, hide_index=True)
    st.caption("La tabla ayuda a auditar coordenadas, municipio cercano y métricas de cada técnica.")


def render_candidate_comparison_view(
    dataset,
    solver: LocationSolver,
    method_result: LocationResult,
) -> None:
    """Renderiza la comparacion discreta de candidatos de ubicacion."""
    st.markdown("### Comparación de Candidatos")
    st.caption(
        "SVQ1 se evalúa como ubicación existente, DQA4 como referencia operativa "
        "actual, una referencia matemática y un punto intermedio como alternativa conceptual. "
        "La comparación usa distancia euclidea comun; los tiempos se reservan para rutas."
    )
    with st.expander("¿Qué significa cada candidato?", expanded=False):
        st.markdown(
            "- **SVQ1**: centro existente y candidato natural de expansión.\n"
            "- **DQA4**: referencia operativa actual de última milla, no recomendación final automática.\n"
            "- **Referencia matemática**: punto calculado por el método elegido.\n"
            "- **Intermedio**: alternativa conceptual para equilibrar distancias entre centros."
        )

    candidates = solver.build_default_candidates(method_result)
    comparison = solver.evaluate_candidates(candidates)

    col1, col2 = st.columns(2)
    if comparison.best_by_distance is not None:
        best_name = _candidate_display_name(comparison.best_by_distance.candidate)
        col1.metric(
            "Mejor distancia media",
            best_name,
            f"{comparison.best_by_distance.weighted_mean_distance_km:.2f} km",
        )
    if comparison.best_by_time is not None:
        best_time_name = _candidate_display_name(comparison.best_by_time.candidate)
        col2.metric(
            "Mejor tiempo medio",
            best_time_name,
            f"{comparison.best_by_time.weighted_mean_time_min:.1f} min",
        )
    else:
        col2.metric("Mejor tiempo medio", "No disponible")

    rows = []
    for evaluation in comparison.evaluations:
        candidate = evaluation.candidate
        display_name = _candidate_display_name(candidate)
        rows.append(
            {
                "Candidato": display_name,
                "Tipo": _candidate_type_label(candidate.candidate_type),
                "Punto de referencia": (
                    dataset.names[candidate.node_index]
                    if candidate.node_index is not None
                    else "Referencia matemática"
                ),
                "Distancia media ponderada (km)": round(evaluation.weighted_mean_distance_km, 2),
                "Distancia total ponderada": round(evaluation.weighted_total_distance_km, 1),
                "Distancia máxima (km)": round(evaluation.max_distance_km, 2),
                "Tiempo medio ponderado (min)": (
                    round(evaluation.weighted_mean_time_min, 1)
                    if evaluation.weighted_mean_time_min is not None
                    else None
                ),
                "Tiempo máximo (min)": (
                    round(evaluation.max_time_min, 1)
                    if evaluation.max_time_min is not None
                    else None
                ),
                "Fuente distancia": _friendly_source_label(evaluation.distance_source),
                "Fuente tiempo": _friendly_source_label(evaluation.time_source),
                "Notas": evaluation.notes or candidate.description or "",
            }
        )

    table = pd.DataFrame(rows).sort_values("Distancia media ponderada (km)")
    st.dataframe(table, use_container_width=True, hide_index=True)
    st.caption(
        "La distancia media ponderada resume el recorrido típico ponderado por población. "
        "La distancia total ponderada refleja el esfuerzo agregado de toda la demanda."
    )

    st.info(comparison.warning)
    st.caption("La comparación ayuda a ver qué candidato queda más cerca de la demanda en promedio.")
    with st.expander("Limitaciones de estas métricas", expanded=False):
        st.markdown(
            "- La comparación usa distancia euclidea para homogeneizar tecnicas y candidatos.\n"
            "- Los tiempos no se calculan aquí; se obtienen en la fase de rutas.\n"
            "- La localización debe combinarse con economía, riesgos, personas y cronograma."
        )

    st.markdown("#### Mapa de Candidatos")
    st.caption("El mapa compara referencias y candidatos sobre la misma demanda territorial.")
    m_candidates = build_candidate_comparison_map(dataset, comparison)
    from streamlit_folium import st_folium

    st_folium(m_candidates, height=500, use_container_width=True)
