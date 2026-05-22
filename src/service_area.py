"""Filtro lógico de nodos agregados de demanda y diagnóstico OD."""

from __future__ import annotations

from typing import Iterable

import numpy as np

from .data_loader import Dataset


AGGREGATED_PROVINCE_NODES = ("Cádiz", "Huelva", "Málaga", "Granada", "Córdoba")
DEFAULT_ACTIVE_PROVINCE_NODES = ("Cádiz", "Huelva")
EXPECTED_ROUTABLE_CENTER_NODES = (
    "SVQ1",
    "DQA4",
    "Centro óptimo / referencia",
    "Intermedio heurístico",
)

_EXPECTED_ROUTABLE_CENTER_INDICES = {
    "SVQ1": 0,
    "DQA4": 1,
    "Centro óptimo / referencia": 2,
    "Intermedio heurístico": 3,
}

_KNOWN_OD_PAIRS = (
    ("SVQ1", "DQA4"),
    ("DQA4", "Cádiz"),
    ("DQA4", "Huelva"),
    ("SVQ1", "Cádiz"),
    ("SVQ1", "Huelva"),
)


def apply_province_node_filter(
    dataset: Dataset,
    active_province_nodes: Iterable[str],
) -> Dataset:
    """Return a dataset view with inactive aggregated provinces set to zero.

    The filter is intentionally logical: it keeps all nodes and OD matrices in
    place, and only changes the population vector used by demand, location and
    routes.
    """

    active = _normalize_active_province_nodes(active_province_nodes)
    population = np.asarray(dataset.poblacion, dtype=int).copy()

    for province_name in AGGREGATED_PROVINCE_NODES:
        if province_name not in dataset.names:
            continue
        if province_name not in active:
            population[dataset.names.index(province_name)] = 0

    return Dataset(
        names=dataset.names,
        latitudes=dataset.latitudes,
        longitudes=dataset.longitudes,
        restringe_camion=dataset.restringe_camion,
        poblacion=population,
        distance_matrix=dataset.distance_matrix,
        time_matrix=dataset.time_matrix,
        depot_index=dataset.depot_index,
    )


def validate_od_alignment_for_known_nodes(
    dataset: Dataset,
    active_province_nodes: Iterable[str] | None = None,
) -> list[str]:
    """Validate known OD alignment and return non-fatal warning messages.

    Matrix shape errors are fatal because downstream route calculations cannot
    be trusted. Missing nodes, unexpected FG indices and suspicious known OD
    values are returned as warnings so the app can keep running visibly.
    """

    _validate_matrix_shape(dataset.distance_matrix, dataset.n_nodes, "distance_matrix")
    _validate_matrix_shape(dataset.time_matrix, dataset.n_nodes, "time_matrix")

    warnings: list[str] = []

    for center_name in ("SVQ1", "DQA4"):
        if center_name not in dataset.names:
            warnings.append(f"No se encontró el centro esperado '{center_name}' en el dataset.")

    for center_name in EXPECTED_ROUTABLE_CENTER_NODES:
        expected_index = _EXPECTED_ROUTABLE_CENTER_INDICES[center_name]
        if expected_index >= dataset.n_nodes:
            warnings.append(
                f"El índice FG esperado {expected_index} para '{center_name}' queda fuera del dataset."
            )
            continue
        actual_name = dataset.names[expected_index]
        if actual_name != center_name:
            warnings.append(
                f"Índice FG inesperado: se esperaba '{center_name}' en {expected_index}, "
                f"pero aparece '{actual_name}'."
            )

    for origin_name, destination_name in _KNOWN_OD_PAIRS:
        warnings.extend(_validate_known_pair(dataset, origin_name, destination_name))

    if active_province_nodes is not None:
        active = _normalize_active_province_nodes(active_province_nodes)
        inactive = set(AGGREGATED_PROVINCE_NODES).difference(active)
        population = np.asarray(dataset.poblacion, dtype=int)

        for province_name in inactive:
            if province_name in dataset.names:
                value = int(population[dataset.names.index(province_name)])
                if value != 0:
                    warnings.append(
                        f"La provincia agregada desactivada '{province_name}' conserva población {value}."
                    )

        for province_name in active:
            if province_name in dataset.names:
                value = int(population[dataset.names.index(province_name)])
                if value <= 0:
                    warnings.append(
                        f"La provincia agregada activa '{province_name}' no conserva población positiva."
                    )

    return warnings


def _normalize_active_province_nodes(active_province_nodes: Iterable[str]) -> tuple[str, ...]:
    active = tuple(str(name).strip() for name in active_province_nodes)
    unknown = sorted(set(active).difference(AGGREGATED_PROVINCE_NODES))
    if unknown:
        valid = ", ".join(AGGREGATED_PROVINCE_NODES)
        raise ValueError(
            f"Provincias agregadas no reconocidas: {unknown}. Opciones válidas: {valid}"
        )
    return tuple(name for name in AGGREGATED_PROVINCE_NODES if name in set(active))


def _validate_matrix_shape(matrix: np.ndarray, n_nodes: int, matrix_name: str) -> None:
    values = np.asarray(matrix)
    if values.ndim != 2:
        raise ValueError(f"{matrix_name} debe ser una matriz 2D")
    if values.shape[0] != values.shape[1]:
        raise ValueError(f"{matrix_name} debe ser cuadrada; forma actual: {values.shape}")
    if values.shape != (n_nodes, n_nodes):
        raise ValueError(
            f"{matrix_name} debe tener forma ({n_nodes}, {n_nodes}); forma actual: {values.shape}"
        )


def _validate_known_pair(dataset: Dataset, origin_name: str, destination_name: str) -> list[str]:
    missing = [name for name in (origin_name, destination_name) if name not in dataset.names]
    if missing:
        return [
            f"No se pudo validar OD {origin_name} ↔ {destination_name}: faltan nodos {missing}."
        ]

    origin_index = dataset.names.index(origin_name)
    destination_index = dataset.names.index(destination_name)
    warnings: list[str] = []
    for from_index, to_index, from_name, to_name in (
        (origin_index, destination_index, origin_name, destination_name),
        (destination_index, origin_index, destination_name, origin_name),
    ):
        distance = float(dataset.distance_matrix[from_index, to_index])
        time = float(dataset.time_matrix[from_index, to_index])
        if not np.isfinite(distance) or distance <= 0:
            warnings.append(
                f"Distancia OD no positiva/finita para {from_name} -> {to_name}: {distance}"
            )
        if not np.isfinite(time) or time <= 0:
            warnings.append(
                f"Tiempo OD no positivo/finito para {from_name} -> {to_name}: {time}"
            )
    return warnings
