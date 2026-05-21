"""Solver de localización de centros de reparto.

Este módulo implementa diferentes técnicas de optimización para localizar
centros de distribución basándose en la población y coordenadas de los municipios.

Técnicas implementadas:
1. Centro de Gravedad Ponderado: Media simple ponderada por población.
2. Minimización de Distancia Total: Minimiza sum(población * distancia) → ubicación óptima según demanda.
3. Minimax: Minimiza la máxima distancia ponderada a cubrir → minimiza el servicio al peor cliente.
4. k-Mediana: Agrupa municipios y selecciona medianas ponderadas.
5. Análisis de múltiples centros: Evalúa ubicaciones alternativas.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
from scipy.optimize import minimize

from .data_loader import DEPOT_NAME, SECONDARY_HUB_NAME


class LocationMethod(str, Enum):
    """Estrategias de localización disponibles."""

    GRAVITY_CENTER = "gravity_center"
    MIN_TOTAL_DISTANCE = "min_total_distance"
    MINIMAX = "minimax"
    K_MEDIAN = "k_median"
    GEOGRAPHIC_CENTER = "geographic_center"


class CandidateType(str, Enum):
    """Tipos de candidato para la comparacion discreta de ubicaciones."""

    EXISTING_HUB = "existing_hub"
    OPERATIONAL_REFERENCE = "operational_reference"
    MATHEMATICAL_REFERENCE = "mathematical_reference"
    HEURISTIC_INTERMEDIATE = "heuristic_intermediate"


class LocationEvaluationMode(str, Enum):
    """Modo de evaluacion de candidatos de localizacion."""

    GEOMETRIC_EUCLIDEAN = "geometric_euclidean"
    OD_MATRIX = "od_matrix"


@dataclass
class LocationResult:
    """Resultado de un cálculo de localización.

    Atributos:
        method: técnica utilizada.
        longitude: coordenada X óptima.
        latitude: coordenada Y óptima.
        weighted_distance: métrica de coste total (significado depende del método).
        max_weighted_distance: distancia máxima ponderada a cualquier nodo.
        nearest_municipality: municipio más cercano a la ubicación óptima.
        distance_to_nearest_km: distancia en km al municipio más cercano.
        objective_value: valor de la función objetivo en la solución.
    """

    method: LocationMethod
    longitude: float
    latitude: float
    weighted_distance: float
    max_weighted_distance: float
    nearest_municipality: Optional[str] = None
    distance_to_nearest_km: Optional[float] = None
    objective_value: Optional[float] = None


@dataclass(frozen=True)
class LocationCandidate:
    """Alternativa concreta o referencia de ubicacion para evaluar."""

    name: str
    candidate_type: CandidateType
    latitude: float
    longitude: float
    node_index: Optional[int] = None
    description: Optional[str] = None


@dataclass(frozen=True)
class CandidateEvaluation:
    """Metricas logisticas calculadas para un candidato de localizacion."""

    candidate: LocationCandidate
    weighted_mean_distance_km: float
    weighted_total_distance_km: float
    max_distance_km: float
    weighted_mean_time_min: Optional[float]
    max_time_min: Optional[float]
    distance_source: str
    time_source: str
    notes: str = ""


@dataclass(frozen=True)
class CandidateComparisonResult:
    """Resultado agregado de la comparacion discreta de candidatos."""

    evaluations: List[CandidateEvaluation]
    best_by_distance: Optional[CandidateEvaluation]
    best_by_time: Optional[CandidateEvaluation]
    notes: str
    warning: str = (
        "La comparacion resume distancia geometrica; no representa "
        "por si sola una decision final de ubicacion."
    )


@dataclass(frozen=True)
class AutoLocationSelection:
    """Seleccion automatica para el escenario de nueva ubicacion."""

    selected: CandidateEvaluation
    comparison: CandidateComparisonResult
    method_results: tuple[LocationResult, ...]

    @property
    def candidate(self) -> LocationCandidate:
        return self.selected.candidate


DISTANCE_SOURCE_OD = "matriz OD de distancia"
DISTANCE_SOURCE_HAVERSINE = "aproximacion Haversine"
DISTANCE_SOURCE_GEOMETRIC = "geométrica euclídea común"
TIME_SOURCE_OD = "matriz OD de tiempo"
TIME_SOURCE_UNAVAILABLE = "tiempo no disponible"


def _node_count(dataset) -> int:
    return int(getattr(dataset, "n_nodes", len(dataset.names)))


def _find_node_index(dataset, name: str) -> Optional[int]:
    normalized = name.strip().casefold()
    for idx, node_name in enumerate(dataset.names):
        if str(node_name).strip().casefold() == normalized:
            return idx
    return None


def _haversine_distances_from_point(
    longitude: float,
    latitude: float,
    longitudes: Sequence[float],
    latitudes: Sequence[float],
) -> np.ndarray:
    """Calcula distancias Haversine en km desde un punto a varios nodos."""
    earth_radius_km = 6371.0
    lat1_rad = np.radians(latitude)
    lon1_rad = np.radians(longitude)
    lat2_rad = np.radians(latitudes)
    lon2_rad = np.radians(longitudes)

    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1_rad) * np.cos(lat2_rad) * np.sin(dlon / 2) ** 2
    c = 2 * np.arcsin(np.sqrt(a))
    return earth_radius_km * c


def latlon_to_local_km(
    longitude: float,
    latitude: float,
    *,
    reference_latitude: float,
    reference_longitude: float,
) -> Tuple[float, float]:
    """Convierte lat/lon a coordenadas locales en km usando una proyeccion simple."""
    km_per_degree = 111.32
    ref_lat = float(reference_latitude)
    ref_lon = float(reference_longitude)
    lat_rad = np.radians(ref_lat)
    x_km = (float(longitude) - ref_lon) * km_per_degree * float(np.cos(lat_rad))
    y_km = (float(latitude) - ref_lat) * km_per_degree
    return x_km, y_km


def euclidean_distances_from_point_km(
    longitude: float,
    latitude: float,
    longitudes: Sequence[float],
    latitudes: Sequence[float],
    *,
    reference_latitude: float,
    reference_longitude: float,
) -> np.ndarray:
    """Calcula distancias euclideas en km desde un punto a varios nodos."""
    x0, y0 = latlon_to_local_km(
        longitude,
        latitude,
        reference_latitude=reference_latitude,
        reference_longitude=reference_longitude,
    )
    km_per_degree = 111.32
    ref_lat = float(reference_latitude)
    ref_lon = float(reference_longitude)
    lat_rad = np.radians(ref_lat)
    longs = np.asarray(longitudes, dtype=float)
    lats = np.asarray(latitudes, dtype=float)
    xs = (longs - ref_lon) * km_per_degree * float(np.cos(lat_rad))
    ys = (lats - ref_lat) * km_per_degree
    dx = xs - float(x0)
    dy = ys - float(y0)
    return np.sqrt(dx**2 + dy**2)


def _nearest_node_to_point(
    dataset,
    longitude: float,
    latitude: float,
    candidate_indices: Optional[np.ndarray] = None,
) -> Optional[int]:
    if candidate_indices is None:
        candidate_indices = np.arange(_node_count(dataset))
    if len(candidate_indices) == 0:
        return None

    distances = _haversine_distances_from_point(
        longitude,
        latitude,
        np.asarray(dataset.longitudes)[candidate_indices],
        np.asarray(dataset.latitudes)[candidate_indices],
    )
    return int(candidate_indices[int(np.argmin(distances))])


def _matrix_available(dataset, attr_name: str) -> bool:
    matrix = getattr(dataset, attr_name, None)
    if matrix is None:
        return False
    matrix = np.asarray(matrix)
    n_nodes = _node_count(dataset)
    return matrix.ndim == 2 and matrix.shape[0] >= n_nodes and matrix.shape[1] >= n_nodes


def _demand_indices(dataset) -> np.ndarray:
    poblacion = np.asarray(dataset.poblacion)
    return np.where(poblacion > 0)[0]


def _prepare_evaluation_weights(
    dataset,
    demand_indices: np.ndarray,
    weights: Optional[Sequence[float]],
) -> np.ndarray:
    if weights is None:
        prepared = np.asarray(dataset.poblacion, dtype=float)[demand_indices]
    else:
        raw = np.asarray(weights, dtype=float)
        if raw.ndim != 1:
            raise ValueError("Los pesos deben ser un vector de una dimension")
        if len(raw) == _node_count(dataset):
            prepared = raw[demand_indices]
        elif len(raw) == len(demand_indices):
            prepared = raw
        else:
            raise ValueError(
                "Los pesos deben tener longitud compatible con el dataset: "
                f"{_node_count(dataset)} nodos o {len(demand_indices)} nodos de demanda"
            )

    if not np.all(np.isfinite(prepared)):
        raise ValueError("Los pesos deben ser valores finitos")
    if np.any(prepared < 0):
        raise ValueError("Los pesos deben ser no negativos")
    if float(np.sum(prepared)) <= 0:
        raise ValueError("La suma de pesos de los nodos de demanda debe ser positiva")
    return prepared.astype(float)


def build_default_candidates(dataset, method_result: LocationResult) -> List[LocationCandidate]:
    """Construye los candidatos base para comparar ubicaciones defendibles.

    Incluye SVQ1 como candidato existente, DQA4 como referencia operativa, el
    optimo continuo del metodo elegido como referencia matematica y un proxy
    intermedio discreto basado en los datos disponibles.
    """
    candidates: List[LocationCandidate] = []

    svq1_index = getattr(dataset, "depot_index", None)
    if svq1_index is None or dataset.names[svq1_index] != DEPOT_NAME:
        svq1_index = _find_node_index(dataset, DEPOT_NAME)
    dqa4_index = _find_node_index(dataset, SECONDARY_HUB_NAME)

    if svq1_index is not None:
        candidates.append(
            LocationCandidate(
                name=DEPOT_NAME,
                candidate_type=CandidateType.EXISTING_HUB,
                latitude=float(dataset.latitudes[svq1_index]),
                longitude=float(dataset.longitudes[svq1_index]),
                node_index=int(svq1_index),
                description="Centro logistico existente y candidato principal de expansion.",
            )
        )

    if dqa4_index is not None:
        candidates.append(
            LocationCandidate(
                name=SECONDARY_HUB_NAME,
                candidate_type=CandidateType.OPERATIONAL_REFERENCE,
                latitude=float(dataset.latitudes[dqa4_index]),
                longitude=float(dataset.longitudes[dqa4_index]),
                node_index=int(dqa4_index),
                description="Referencia operativa actual de ultima milla, no recomendacion final.",
            )
        )

    candidates.append(
        LocationCandidate(
            name=f"Optimo continuo ({method_result.method.value})",
            candidate_type=CandidateType.MATHEMATICAL_REFERENCE,
            latitude=float(method_result.latitude),
            longitude=float(method_result.longitude),
            node_index=None,
            description="Referencia matematica continua; no representa una parcela real.",
        )
    )

    demand_nodes = _demand_indices(dataset)
    if svq1_index is not None and dqa4_index is not None:
        mid_lat = (float(dataset.latitudes[svq1_index]) + float(dataset.latitudes[dqa4_index])) / 2
        mid_lon = (float(dataset.longitudes[svq1_index]) + float(dataset.longitudes[dqa4_index])) / 2
        intermediate_idx = None
        intermediate_description = (
            f"Punto medio geometrico {DEPOT_NAME}-{SECONDARY_HUB_NAME} (contraste academico)."
        )
    else:
        intermediate_idx = _nearest_node_to_point(
            dataset,
            float(method_result.longitude),
            float(method_result.latitude),
            demand_nodes,
        )
        intermediate_description = "Municipio con demanda mas cercano al optimo continuo."

    if intermediate_idx is not None:
        candidates.append(
            LocationCandidate(
                name=f"Intermedio heuristico ({dataset.names[intermediate_idx]})",
                candidate_type=CandidateType.HEURISTIC_INTERMEDIATE,
                latitude=float(dataset.latitudes[intermediate_idx]),
                longitude=float(dataset.longitudes[intermediate_idx]),
                node_index=int(intermediate_idx),
                description=intermediate_description,
            )
        )
    elif svq1_index is not None and dqa4_index is not None:
        candidates.append(
            LocationCandidate(
                name=f"Punto medio {DEPOT_NAME}-{SECONDARY_HUB_NAME}",
                candidate_type=CandidateType.HEURISTIC_INTERMEDIATE,
                latitude=mid_lat,
                longitude=mid_lon,
                node_index=None,
                description=intermediate_description,
            )
        )

    return candidates


def evaluate_candidates(
    dataset,
    candidates: Sequence[LocationCandidate],
    weights: Optional[Sequence[float]] = None,
    mode: LocationEvaluationMode = LocationEvaluationMode.GEOMETRIC_EUCLIDEAN,
) -> CandidateComparisonResult:
    """Evalua candidatos discretos con metricas homogeneas de distancia/tiempo."""
    demand_nodes = _demand_indices(dataset)
    if len(demand_nodes) == 0:
        raise ValueError("No hay nodos de demanda con poblacion positiva")

    prepared_weights = _prepare_evaluation_weights(dataset, demand_nodes, weights)
    total_weight = float(np.sum(prepared_weights))
    n_nodes = _node_count(dataset)
    distance_matrix_available = _matrix_available(dataset, "distance_matrix")
    time_matrix_available = _matrix_available(dataset, "time_matrix")
    if isinstance(mode, str):
        mode = LocationEvaluationMode(mode)
    reference_latitude = float(np.mean(np.asarray(dataset.latitudes, dtype=float)))
    reference_longitude = float(np.mean(np.asarray(dataset.longitudes, dtype=float)))

    evaluations: List[CandidateEvaluation] = []
    for candidate in candidates:
        notes: List[str] = []
        node_index = candidate.node_index
        if node_index is not None:
            node_index = int(node_index)
            if node_index < 0 or node_index >= n_nodes:
                raise ValueError(
                    f"node_index fuera de rango para candidato '{candidate.name}': {node_index}"
                )

        if mode == LocationEvaluationMode.GEOMETRIC_EUCLIDEAN:
            distances = euclidean_distances_from_point_km(
                candidate.longitude,
                candidate.latitude,
                np.asarray(dataset.longitudes)[demand_nodes],
                np.asarray(dataset.latitudes)[demand_nodes],
                reference_latitude=reference_latitude,
                reference_longitude=reference_longitude,
            )
            distance_source = DISTANCE_SOURCE_GEOMETRIC
            notes.append("Modo geometrico: distancia euclidea comun.")
        else:
            if node_index is not None and distance_matrix_available:
                distances = np.asarray(dataset.distance_matrix[node_index, demand_nodes], dtype=float)
                distance_source = DISTANCE_SOURCE_OD
            else:
                distances = euclidean_distances_from_point_km(
                    candidate.longitude,
                    candidate.latitude,
                    np.asarray(dataset.longitudes)[demand_nodes],
                    np.asarray(dataset.latitudes)[demand_nodes],
                    reference_latitude=reference_latitude,
                    reference_longitude=reference_longitude,
                )
                distance_source = DISTANCE_SOURCE_GEOMETRIC
                if node_index is None:
                    notes.append("Proxy geometrico: candidato sin node_index.")
                else:
                    notes.append("Proxy geometrico: matriz OD no disponible.")

        weighted_total_distance = float(np.sum(prepared_weights * distances))
        weighted_mean_distance = weighted_total_distance / total_weight
        max_distance = float(np.max(distances))

        if mode == LocationEvaluationMode.OD_MATRIX and node_index is not None and time_matrix_available:
            times = np.asarray(dataset.time_matrix[node_index, demand_nodes], dtype=float)
            weighted_mean_time = float(np.sum(prepared_weights * times) / total_weight)
            max_time = float(np.max(times))
            time_source = TIME_SOURCE_OD
        else:
            weighted_mean_time = None
            max_time = None
            time_source = TIME_SOURCE_UNAVAILABLE
            if mode == LocationEvaluationMode.OD_MATRIX:
                if node_index is None:
                    notes.append("Tiempo no disponible para candidatos sin node_index.")
                else:
                    notes.append("Matriz OD de tiempo no disponible.")
            else:
                notes.append("Modo geometrico: tiempo no calculado.")

        evaluations.append(
            CandidateEvaluation(
                candidate=candidate,
                weighted_mean_distance_km=weighted_mean_distance,
                weighted_total_distance_km=weighted_total_distance,
                max_distance_km=max_distance,
                weighted_mean_time_min=weighted_mean_time,
                max_time_min=max_time,
                distance_source=distance_source,
                time_source=time_source,
                notes=" ".join(notes),
            )
        )

    best_by_distance = min(
        evaluations,
        key=lambda item: item.weighted_mean_distance_km,
        default=None,
    )
    time_evaluations = [
        item for item in evaluations if item.weighted_mean_time_min is not None
    ]
    best_by_time = min(
        time_evaluations,
        key=lambda item: item.weighted_mean_time_min,
        default=None,
    )
    if mode == LocationEvaluationMode.GEOMETRIC_EUCLIDEAN:
        notes = (
            "Comparacion geometrica euclidea comun; se usa solo distancia como criterio "
            "homogeneo."
        )
    else:
        notes = (
            "Modo OD: se usan matrices OD cuando hay node_index; los continuos "
            "se mantienen como proxy geometrico."
        )
    return CandidateComparisonResult(
        evaluations=evaluations,
        best_by_distance=best_by_distance,
        best_by_time=best_by_time,
        notes=notes,
    )


def build_auto_location_candidates(
    dataset,
    method_results: Sequence[LocationResult],
) -> List[LocationCandidate]:
    """Construye candidatos rapidos para la nueva ubicacion automatica."""
    candidates: List[LocationCandidate] = []

    for result in method_results:
        candidates.append(
            LocationCandidate(
                name=f"Optimo continuo ({result.method.value})",
                candidate_type=CandidateType.MATHEMATICAL_REFERENCE,
                latitude=float(result.latitude),
                longitude=float(result.longitude),
                node_index=None,
                description="Referencia continua generada por metodo de localizacion.",
            )
        )

    svq1_index = _find_node_index(dataset, DEPOT_NAME)
    dqa4_index = _find_node_index(dataset, SECONDARY_HUB_NAME)

    if svq1_index is not None:
        candidates.append(
            LocationCandidate(
                name=DEPOT_NAME,
                candidate_type=CandidateType.EXISTING_HUB,
                latitude=float(dataset.latitudes[svq1_index]),
                longitude=float(dataset.longitudes[svq1_index]),
                node_index=int(svq1_index),
                description="Centro logistico existente incluido en la comparacion automatica.",
            )
        )

    if dqa4_index is not None:
        candidates.append(
            LocationCandidate(
                name=SECONDARY_HUB_NAME,
                candidate_type=CandidateType.OPERATIONAL_REFERENCE,
                latitude=float(dataset.latitudes[dqa4_index]),
                longitude=float(dataset.longitudes[dqa4_index]),
                node_index=int(dqa4_index),
                description="Referencia operativa actual incluida en la comparacion automatica.",
            )
        )

    if svq1_index is not None and dqa4_index is not None:
        candidates.append(
            LocationCandidate(
                name=f"Punto medio {DEPOT_NAME}-{SECONDARY_HUB_NAME}",
                candidate_type=CandidateType.HEURISTIC_INTERMEDIATE,
                latitude=(
                    float(dataset.latitudes[svq1_index])
                    + float(dataset.latitudes[dqa4_index])
                ) / 2,
                longitude=(
                    float(dataset.longitudes[svq1_index])
                    + float(dataset.longitudes[dqa4_index])
                ) / 2,
                node_index=None,
                description="Punto geometrico medio entre los dos centros del caso.",
            )
        )

    return candidates


def _candidate_type_label(candidate_type: CandidateType) -> str:
    mapping = {
        CandidateType.EXISTING_HUB: "Centro existente",
        CandidateType.OPERATIONAL_REFERENCE: "Referencia operativa",
        CandidateType.MATHEMATICAL_REFERENCE: "Referencia matematica",
        CandidateType.HEURISTIC_INTERMEDIATE: "Intermedio heuristico",
    }
    return mapping.get(candidate_type, str(candidate_type))


def _route_usage_for_candidate(candidate: LocationCandidate) -> str:
    if candidate.candidate_type in (CandidateType.EXISTING_HUB, CandidateType.OPERATIONAL_REFERENCE):
        return "OD existente"
    if candidate.candidate_type == CandidateType.HEURISTIC_INTERMEDIATE:
        return "requiere Excel"
    return "proxy academico"


def _route_usage_for_method() -> str:
    return "proxy academico"


def _geometric_metrics_for_point(
    *,
    longitude: float,
    latitude: float,
    demand_longitudes: np.ndarray,
    demand_latitudes: np.ndarray,
    weights: np.ndarray,
    reference_latitude: float,
    reference_longitude: float,
) -> tuple[float, float, float]:
    distances = euclidean_distances_from_point_km(
        longitude,
        latitude,
        demand_longitudes,
        demand_latitudes,
        reference_latitude=reference_latitude,
        reference_longitude=reference_longitude,
    )
    weighted_total = float(np.sum(weights * distances))
    weighted_mean = weighted_total / float(np.sum(weights))
    max_distance = float(np.max(distances))
    return weighted_mean, weighted_total, max_distance


def build_full_location_comparison(
    dataset,
    weights: Optional[Sequence[float]] = None,
) -> pd.DataFrame:
    """Construye una tabla integrada con tecnicas y candidatos en la misma escala."""
    demand_nodes = _demand_indices(dataset)
    if len(demand_nodes) == 0:
        raise ValueError("No hay nodos de demanda con poblacion positiva")

    prepared_weights = _prepare_evaluation_weights(dataset, demand_nodes, weights)
    demand_longitudes = np.asarray(dataset.longitudes, dtype=float)[demand_nodes]
    demand_latitudes = np.asarray(dataset.latitudes, dtype=float)[demand_nodes]
    reference_latitude = float(np.mean(np.asarray(dataset.latitudes, dtype=float)))
    reference_longitude = float(np.mean(np.asarray(dataset.longitudes, dtype=float)))

    rows: list[dict[str, object]] = []

    solver = LocationSolver(dataset)
    for method in LocationMethod:
        result = solver.solve(method)
        mean_dist, total_dist, max_dist = _geometric_metrics_for_point(
            longitude=float(result.longitude),
            latitude=float(result.latitude),
            demand_longitudes=demand_longitudes,
            demand_latitudes=demand_latitudes,
            weights=prepared_weights,
            reference_latitude=reference_latitude,
            reference_longitude=reference_longitude,
        )
        rows.append(
            {
                "Nombre": f"Optimo continuo ({method.value})",
                "Clase": "Tecnica continua",
                "Tipo": method.value.replace("_", " ").title(),
                "Latitud": float(result.latitude),
                "Longitud": float(result.longitude),
                "Distancia media (km)": mean_dist,
                "Distancia total (km)": total_dist,
                "Distancia maxima (km)": max_dist,
                "Fuente": DISTANCE_SOURCE_GEOMETRIC,
                "Uso en rutas": _route_usage_for_method(),
            }
        )

    candidates: list[LocationCandidate] = []
    svq1_index = _find_node_index(dataset, DEPOT_NAME)
    dqa4_index = _find_node_index(dataset, SECONDARY_HUB_NAME)

    if svq1_index is not None:
        candidates.append(
            LocationCandidate(
                name=DEPOT_NAME,
                candidate_type=CandidateType.EXISTING_HUB,
                latitude=float(dataset.latitudes[svq1_index]),
                longitude=float(dataset.longitudes[svq1_index]),
                node_index=int(svq1_index),
                description="Centro logistico existente.",
            )
        )

    if dqa4_index is not None:
        candidates.append(
            LocationCandidate(
                name=SECONDARY_HUB_NAME,
                candidate_type=CandidateType.OPERATIONAL_REFERENCE,
                latitude=float(dataset.latitudes[dqa4_index]),
                longitude=float(dataset.longitudes[dqa4_index]),
                node_index=int(dqa4_index),
                description="Referencia operativa actual.",
            )
        )

    if svq1_index is not None and dqa4_index is not None:
        mid_lat = (float(dataset.latitudes[svq1_index]) + float(dataset.latitudes[dqa4_index])) / 2
        mid_lon = (float(dataset.longitudes[svq1_index]) + float(dataset.longitudes[dqa4_index])) / 2
        candidates.append(
            LocationCandidate(
                name=f"Punto medio {DEPOT_NAME}-{SECONDARY_HUB_NAME}",
                candidate_type=CandidateType.HEURISTIC_INTERMEDIATE,
                latitude=mid_lat,
                longitude=mid_lon,
                node_index=None,
                description="Contraste academico: punto medio geometrico.",
            )
        )

    for candidate in candidates:
        mean_dist, total_dist, max_dist = _geometric_metrics_for_point(
            longitude=float(candidate.longitude),
            latitude=float(candidate.latitude),
            demand_longitudes=demand_longitudes,
            demand_latitudes=demand_latitudes,
            weights=prepared_weights,
            reference_latitude=reference_latitude,
            reference_longitude=reference_longitude,
        )
        rows.append(
            {
                "Nombre": candidate.name,
                "Clase": "Candidato",
                "Tipo": _candidate_type_label(candidate.candidate_type),
                "Latitud": float(candidate.latitude),
                "Longitud": float(candidate.longitude),
                "Distancia media (km)": mean_dist,
                "Distancia total (km)": total_dist,
                "Distancia maxima (km)": max_dist,
                "Fuente": DISTANCE_SOURCE_GEOMETRIC,
                "Uso en rutas": _route_usage_for_candidate(candidate),
            }
        )

    frame = pd.DataFrame(rows)
    if frame.empty:
        return frame

    best_value = float(frame["Distancia media (km)"].min())
    if best_value > 0:
        frame["Delta vs mejor (%)"] = (
            frame["Distancia media (km)"] - best_value
        ) / best_value * 100.0
    else:
        frame["Delta vs mejor (%)"] = 0.0

    columns = [
        "Nombre",
        "Clase",
        "Tipo",
        "Latitud",
        "Longitud",
        "Distancia media (km)",
        "Distancia total (km)",
        "Distancia maxima (km)",
        "Delta vs mejor (%)",
        "Fuente",
        "Uso en rutas",
    ]
    return frame[columns].sort_values("Distancia media (km)").reset_index(drop=True)


def select_auto_new_location(
    dataset,
    weights: Optional[Sequence[float]] = None,
) -> AutoLocationSelection:
    """Elige la nueva ubicacion por distancia media ponderada minima."""
    solver = LocationSolver(dataset)
    method_results = tuple(solver.solve(method) for method in LocationMethod)
    candidates = build_auto_location_candidates(dataset, method_results)
    comparison = evaluate_candidates(dataset, candidates, weights=weights)
    selected = min(
        comparison.evaluations,
        key=lambda item: (
            item.weighted_mean_distance_km,
            item.max_distance_km,
            item.candidate.name,
        ),
    )
    return AutoLocationSelection(
        selected=selected,
        comparison=comparison,
        method_results=method_results,
    )


class LocationSolver:
    """Solver de localización de centros de distribución."""

    def __init__(self, dataset):
        """
        Inicializa el solver con datos de municipios.

        Parámetros:
            dataset: objeto Dataset con nombres, coordenadas, población y matriz de distancias.
        """
        self.dataset = dataset
        self.names = dataset.names
        self.latitudes = dataset.latitudes
        self.longitudes = dataset.longitudes
        self.poblacion = dataset.poblacion
        self.distance_matrix = dataset.distance_matrix

        # Excluir centros logísticos (población=0) del cálculo de demanda
        self.demand_mask = self.poblacion > 0
        self.demand_indices = np.where(self.demand_mask)[0]

    def solve(self, method: LocationMethod = LocationMethod.MIN_TOTAL_DISTANCE) -> LocationResult:
        """Resuelve el problema de localización usando la técnica especificada.

        Parámetros:
            method: técnica de localización a utilizar.

        Retorna:
            LocationResult con la ubicación óptima y métricas asociadas.
        """
        if method == LocationMethod.GRAVITY_CENTER:
            return self._solve_gravity_center()
        elif method == LocationMethod.MIN_TOTAL_DISTANCE:
            return self._solve_min_total_distance()
        elif method == LocationMethod.MINIMAX:
            return self._solve_minimax()
        elif method == LocationMethod.GEOGRAPHIC_CENTER:
            return self._solve_geographic_center()
        elif method == LocationMethod.K_MEDIAN:
            return self._solve_k_median()
        else:
            raise ValueError(f"Método desconocido: {method}")

    def _solve_gravity_center(self) -> LocationResult:
        """Centro de gravedad ponderado por población."""
        demand_nodes = self.demand_indices
        weights = self.poblacion[demand_nodes]
        lats = self.latitudes[demand_nodes]
        lons = self.longitudes[demand_nodes]

        lat_optimal = np.sum(weights * lats) / np.sum(weights)
        lon_optimal = np.sum(weights * lons) / np.sum(weights)

        # Calcular métricas
        distances = self._calculate_distances_from_point(lon_optimal, lat_optimal)
        weighted_dist = np.sum(weights * distances[demand_nodes])
        max_weighted_dist = np.max(weights * distances[demand_nodes])

        nearest_idx = self._find_nearest_municipality(lon_optimal, lat_optimal)

        return LocationResult(
            method=LocationMethod.GRAVITY_CENTER,
            longitude=lon_optimal,
            latitude=lat_optimal,
            weighted_distance=weighted_dist,
            max_weighted_distance=max_weighted_dist,
            nearest_municipality=self.names[nearest_idx],
            distance_to_nearest_km=distances[nearest_idx],
            objective_value=weighted_dist,
        )

    def _solve_min_total_distance(self) -> LocationResult:
        """Minimiza la suma ponderada de distancias: sum(población * distancia)."""
        demand_nodes = self.demand_indices
        weights = self.poblacion[demand_nodes]
        lats = self.latitudes[demand_nodes]
        lons = self.longitudes[demand_nodes]

        # Punto inicial: centro de gravedad
        x0 = np.array([
            np.sum(weights * lons) / np.sum(weights),
            np.sum(weights * lats) / np.sum(weights),
        ])

        # Función objetivo
        def objective(xy):
            distances = np.sqrt((xy[0] - lons) ** 2 + (xy[1] - lats) ** 2)
            return np.sum(weights * distances)

        # Usar scipy.optimize.minimize (más robusto que fminunc en MATLAB)
        result = minimize(objective, x0, method="Nelder-Mead", options={"maxiter": 10000})
        lon_optimal, lat_optimal = result.x

        # Calcular métricas finales
        distances = self._calculate_distances_from_point(lon_optimal, lat_optimal)
        weighted_dist = np.sum(weights * distances[demand_nodes])
        max_weighted_dist = np.max(weights * distances[demand_nodes])
        nearest_idx = self._find_nearest_municipality(lon_optimal, lat_optimal)

        return LocationResult(
            method=LocationMethod.MIN_TOTAL_DISTANCE,
            longitude=lon_optimal,
            latitude=lat_optimal,
            weighted_distance=weighted_dist,
            max_weighted_distance=max_weighted_dist,
            nearest_municipality=self.names[nearest_idx],
            distance_to_nearest_km=distances[nearest_idx],
            objective_value=result.fun,
        )

    def _solve_minimax(self) -> LocationResult:
        """Minimax: Minimiza la máxima distancia ponderada.

        Objetivo: Minimizar el servicio al cliente peor servido (equidad).
        """
        demand_nodes = self.demand_indices
        weights = self.poblacion[demand_nodes]
        lats = self.latitudes[demand_nodes]
        lons = self.longitudes[demand_nodes]

        # Punto inicial
        x0 = np.array([
            np.sum(weights * lons) / np.sum(weights),
            np.sum(weights * lats) / np.sum(weights),
        ])

        # Función objetivo: vector de distancias ponderadas
        def objective_vector(xy):
            distances = np.sqrt((xy[0] - lons) ** 2 + (xy[1] - lats) ** 2)
            return weights * distances

        # Minimizar el máximo valor (minimax)
        def objective_max(xy):
            return np.max(objective_vector(xy))

        result = minimize(objective_max, x0, method="Nelder-Mead", options={"maxiter": 10000})
        lon_optimal, lat_optimal = result.x

        # Calcular métricas
        distances = self._calculate_distances_from_point(lon_optimal, lat_optimal)
        weighted_dist = np.sum(weights * distances[demand_nodes])
        max_weighted_dist = np.max(weights * distances[demand_nodes])
        nearest_idx = self._find_nearest_municipality(lon_optimal, lat_optimal)

        return LocationResult(
            method=LocationMethod.MINIMAX,
            longitude=lon_optimal,
            latitude=lat_optimal,
            weighted_distance=weighted_dist,
            max_weighted_distance=max_weighted_dist,
            nearest_municipality=self.names[nearest_idx],
            distance_to_nearest_km=distances[nearest_idx],
            objective_value=result.fun,
        )

    def _solve_geographic_center(self) -> LocationResult:
        """Centro geográfico simple (sin ponderación por población)."""
        demand_nodes = self.demand_indices
        weights = self.poblacion[demand_nodes]
        lats = self.latitudes[demand_nodes]
        lons = self.longitudes[demand_nodes]

        # Centro geográfico simple
        lat_optimal = np.mean(lats)
        lon_optimal = np.mean(lons)

        # Calcular métricas
        distances = self._calculate_distances_from_point(lon_optimal, lat_optimal)
        weighted_dist = np.sum(weights * distances[demand_nodes])
        max_weighted_dist = np.max(weights * distances[demand_nodes])
        nearest_idx = self._find_nearest_municipality(lon_optimal, lat_optimal)

        return LocationResult(
            method=LocationMethod.GEOGRAPHIC_CENTER,
            longitude=lon_optimal,
            latitude=lat_optimal,
            weighted_distance=weighted_dist,
            max_weighted_distance=max_weighted_dist,
            nearest_municipality=self.names[nearest_idx],
            distance_to_nearest_km=distances[nearest_idx],
            objective_value=weighted_dist,
        )

    def _solve_k_median(self, k: int = 1) -> LocationResult:
        """k-mediana: encuentra k ubicaciones óptimas (para k=1, es la mediana ponderada).

        Para k=1, es equivalente a encontrar la "mediana" que minimiza distancias.
        Aquí usamos k-means para agrupar y luego la mediana de cada grupo.
        """
        if k == 1:
            # Para k=1, usar min_total_distance
            return self._solve_min_total_distance()

        # Para k > 1, usar clustering simple k-means
        demand_nodes = self.demand_indices
        lats = self.latitudes[demand_nodes]
        lons = self.longitudes[demand_nodes]
        weights = self.poblacion[demand_nodes]

        # Datos de entrada para clustering
        X = np.column_stack([lons, lats])

        # K-means simple iterativo
        from sklearn.cluster import KMeans

        try:
            kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
            labels = kmeans.fit_predict(X)

            # Encontrar la mediana ponderada de cada cluster
            centroids = []
            for i in range(k):
                cluster_mask = labels == i
                cluster_lons = lons[cluster_mask]
                cluster_lats = lats[cluster_mask]
                cluster_weights = weights[cluster_mask]

                # Mediana ponderada (usamos media como aproximación)
                lon_median = np.average(cluster_lons, weights=cluster_weights)
                lat_median = np.average(cluster_lats, weights=cluster_weights)
                centroids.append((lon_median, lat_median))

            # Para k > 1, retornar el centroide del cluster más grande
            largest_cluster = np.argmax(np.bincount(labels))
            lon_optimal, lat_optimal = centroids[largest_cluster]

        except ImportError:
            # Fallback si sklearn no está disponible
            return self._solve_min_total_distance()

        # Calcular métricas
        distances = self._calculate_distances_from_point(lon_optimal, lat_optimal)
        weighted_dist = np.sum(weights * distances[demand_nodes])
        max_weighted_dist = np.max(weights * distances[demand_nodes])
        nearest_idx = self._find_nearest_municipality(lon_optimal, lat_optimal)

        return LocationResult(
            method=LocationMethod.K_MEDIAN,
            longitude=lon_optimal,
            latitude=lat_optimal,
            weighted_distance=weighted_dist,
            max_weighted_distance=max_weighted_dist,
            nearest_municipality=self.names[nearest_idx],
            distance_to_nearest_km=distances[nearest_idx],
            objective_value=weighted_dist,
        )

    def _calculate_distances_from_point(
        self, longitude: float, latitude: float
    ) -> np.ndarray:
        """Calcula distancia en km (Haversine) entre un punto y todos los nodos."""
        return _haversine_distances_from_point(
            longitude,
            latitude,
            self.longitudes,
            self.latitudes,
        )

    def _find_nearest_municipality(
        self, longitude: float, latitude: float
    ) -> int:
        """Encuentra el municipio más cercano a una ubicación."""
        distances = self._calculate_distances_from_point(longitude, latitude)
        return np.argmin(distances)

    def get_all_solutions(self) -> dict:
        """Ejecuta todos los métodos y retorna un diccionario con los resultados."""
        solutions = {}
        for method in LocationMethod:
            solutions[method.value] = self.solve(method)
        return solutions

    def compare_solutions(self) -> pd.DataFrame:
        """Compara todas las soluciones en un DataFrame.

        Retorna:
            DataFrame con un fila por método, columnas con métricas clave.
        """
        solutions = self.get_all_solutions()

        rows = []
        for method_name, result in solutions.items():
            rows.append(
                {
                    "Método": method_name.replace("_", " ").title(),
                    "Latitud": result.latitude,
                    "Longitud": result.longitude,
                    "Dist. Total Ponderada": f"{result.weighted_distance:,.1f}",
                    "Dist. Máxima Pond.": f"{result.max_weighted_distance:,.1f}",
                    "Municipio Más Cercano": result.nearest_municipality,
                    "Distancia al Municipio (km)": f"{result.distance_to_nearest_km:.2f}",
                }
            )

        return pd.DataFrame(rows)

    def build_default_candidates(
        self,
        method_result: LocationResult,
    ) -> List[LocationCandidate]:
        """Construye los candidatos base usando el dataset del solver."""
        return build_default_candidates(self.dataset, method_result)

    def evaluate_candidates(
        self,
        candidates: Sequence[LocationCandidate],
        weights: Optional[Sequence[float]] = None,
        mode: LocationEvaluationMode = LocationEvaluationMode.GEOMETRIC_EUCLIDEAN,
    ) -> CandidateComparisonResult:
        """Evalua candidatos usando el dataset del solver."""
        return evaluate_candidates(self.dataset, candidates, weights=weights, mode=mode)

    def build_full_location_comparison(
        self,
        weights: Optional[Sequence[float]] = None,
    ) -> pd.DataFrame:
        """Construye la tabla integrada de tecnicas y candidatos."""
        return build_full_location_comparison(self.dataset, weights=weights)

    def select_auto_new_location(
        self,
        weights: Optional[Sequence[float]] = None,
    ) -> AutoLocationSelection:
        """Elige automaticamente la nueva ubicacion usando el dataset del solver."""
        return select_auto_new_location(self.dataset, weights=weights)
