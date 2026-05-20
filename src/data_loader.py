"""Carga y validacion de datos para VRP por tiempo SVQ1.

Este modulo carga y valida los datos desde dos fuentes CSV sincronizadas:

- ``poblacion.csv``: lista de municipios con poblacion y coordenadas (122 nodos: SVQ1, DQA4, 120 municipios/provincias).
- ``rutasDistTiempo.csv``: matriz OD completa con distancia (km) y tiempo (min) para los 122 nodos.

Ambos archivos estan sincronizados y tienen el mismo numero de filas de datos (122 nodos,
sin contar la cabecera).

El resultado de :func:`load_dataset` es una :class:`Dataset` con todo lo que
necesita el solver: nombres, coordenadas, restricciones, poblacion y dos
matrices NxN (distancia y tiempo) ya alineadas y consistentes.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

# Nombres de los nodos especiales (deposito y centro logistico secundario).
DEPOT_NAME = "SVQ1"
SECONDARY_HUB_NAME = "DQA4"
VIRTUAL_DEPOT_NAME_PREFIX = "Nueva ubicacion automatica"


@dataclass(frozen=True)
class Dataset:
    """Estructura de datos lista para el solver.

    Atributos:
        names: nombre de cada nodo, alineado con los indices 0..N-1.
        latitudes / longitudes: coordenadas geograficas de cada nodo.
        restringe_camion: 1 si el nodo restringe acceso a camion, 0 si no.
        poblacion: habitantes por nodo.
        distance_matrix: matriz NxN en km.
        time_matrix: matriz NxN en minutos.
        depot_index: indice del deposito (SVQ1).
    """

    names: List[str]
    latitudes: np.ndarray
    longitudes: np.ndarray
    restringe_camion: np.ndarray
    poblacion: np.ndarray
    distance_matrix: np.ndarray
    time_matrix: np.ndarray
    depot_index: int

    @property
    def n_nodes(self) -> int:
        return len(self.names)


def _read_poblacion(path: Path) -> pd.DataFrame:
    """Lee poblacion.csv tolerando BOM y separador ';'."""
    if not path.exists():
        raise FileNotFoundError(f"No se encuentra el archivo de poblacion: {path}")

    df = pd.read_csv(path, sep=";", encoding="utf-8-sig")
    expected_cols = {"Municipio", "Población", "Latitud (Y)", "Longitud (X)", "Restringe camion"}
    missing = expected_cols - set(df.columns)
    if missing:
        raise ValueError(
            f"Faltan columnas en poblacion.csv: {sorted(missing)}. "
            f"Encontradas: {df.columns.tolist()}"
        )

    df = df.copy()
    df["Municipio"] = df["Municipio"].astype(str).str.strip()
    df["Población"] = pd.to_numeric(df["Población"], errors="coerce").fillna(0).astype(int)
    df["Latitud (Y)"] = pd.to_numeric(df["Latitud (Y)"], errors="coerce")
    df["Longitud (X)"] = pd.to_numeric(df["Longitud (X)"], errors="coerce")
    df["Restringe camion"] = pd.to_numeric(df["Restringe camion"], errors="coerce").fillna(0).astype(int)

    if df[["Latitud (Y)", "Longitud (X)"]].isna().any().any():
        bad = df[df[["Latitud (Y)", "Longitud (X)"]].isna().any(axis=1)]["Municipio"].tolist()
        raise ValueError(f"Coordenadas invalidas en poblacion.csv para: {bad}")

    return df.reset_index(drop=True)


def _read_routes(path: Path, n_expected: int) -> Tuple[np.ndarray, np.ndarray]:
    """Lee rutasDistTiempo.csv y devuelve (dist_matrix, time_matrix) NxN.

    El CSV tiene formato largo (origen_id, destino_id, distancia_km, tiempo_min).
    Se valida que la matriz este completa para los IDs 0..n_expected-1.
    """
    if not path.exists():
        raise FileNotFoundError(f"No se encuentra el archivo de rutas: {path}")

    df = pd.read_csv(path, encoding="utf-8-sig")
    expected_cols = {"origen_id", "destino_id", "distancia_km", "tiempo_min"}
    missing = expected_cols - set(df.columns)
    if missing:
        raise ValueError(
            f"Faltan columnas en rutasDistTiempo.csv: {sorted(missing)}. "
            f"Encontradas: {df.columns.tolist()}"
        )

    df = df.copy()
    for col in ("origen_id", "destino_id"):
        df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")
    for col in ("distancia_km", "tiempo_min"):
        df[col] = pd.to_numeric(df[col], errors="coerce")

    if df[["origen_id", "destino_id", "distancia_km", "tiempo_min"]].isna().any().any():
        raise ValueError("Hay valores no numericos o nulos en rutasDistTiempo.csv")

    if (df["distancia_km"] < 0).any() or (df["tiempo_min"] < 0).any():
        raise ValueError("Hay distancias o tiempos negativos en rutasDistTiempo.csv")

    ids = pd.unique(pd.concat([df["origen_id"], df["destino_id"]]))
    if int(ids.min()) != 0 or int(ids.max()) != n_expected - 1:
        raise ValueError(
            f"IDs fuera de rango en rutasDistTiempo.csv. Esperado 0..{n_expected - 1}, "
            f"encontrado {int(ids.min())}..{int(ids.max())}"
        )

    expected_pairs = n_expected * n_expected
    if len(df) != expected_pairs:
        raise ValueError(
            f"La matriz OD de rutasDistTiempo.csv esta incompleta. "
            f"Esperado {expected_pairs} pares, encontrado {len(df)}"
        )

    dist = np.zeros((n_expected, n_expected), dtype=float)
    tim = np.zeros((n_expected, n_expected), dtype=float)
    for o, d, km, mn in df[["origen_id", "destino_id", "distancia_km", "tiempo_min"]].itertuples(index=False):
        dist[int(o), int(d)] = float(km)
        tim[int(o), int(d)] = float(mn)

    return dist, tim


def load_dataset(
    poblacion_path: str | Path = "data/poblacion.csv",
    rutas_path: str | Path = "data/rutasDistTiempo.csv",
) -> Dataset:
    """Carga y valida todos los datos desde los CSVs sincronizados.
    
    Espera que poblacion.csv y rutasDistTiempo.csv tengan el mismo numero de
    nodos (122) en el mismo orden.
    """
    poblacion_path = Path(poblacion_path)
    rutas_path = Path(rutas_path)

    pob_df = _read_poblacion(poblacion_path)
    n_pob = len(pob_df)

    csv_dist, csv_time = _read_routes(rutas_path, n_expected=n_pob)

    # Construir vectores alineados con nombres de poblacion.csv.
    names = pob_df["Municipio"].tolist()
    latitudes = pob_df["Latitud (Y)"].to_numpy(dtype=float)
    longitudes = pob_df["Longitud (X)"].to_numpy(dtype=float)
    restringe = pob_df["Restringe camion"].to_numpy(dtype=int)
    poblacion = pob_df["Población"].to_numpy(dtype=int)

    if DEPOT_NAME not in names:
        raise ValueError(f"No se encontro el deposito '{DEPOT_NAME}' en los datos cargados")
    depot_index = names.index(DEPOT_NAME)

    return Dataset(
        names=names,
        latitudes=latitudes,
        longitudes=longitudes,
        restringe_camion=restringe,
        poblacion=poblacion,
        distance_matrix=csv_dist,
        time_matrix=csv_time,
        depot_index=depot_index,
    )


def dataset_with_depot(dataset: Dataset, depot_name_or_index: str | int) -> Dataset:
    """Devuelve una vista del dataset con otro deposito validado.

    No modifica los datos originales ni las matrices OD. Solo cambia el
    ``depot_index`` cuando el nodo existe en la matriz de distancia y tiempo.
    """
    if isinstance(depot_name_or_index, str):
        normalized = depot_name_or_index.strip().casefold()
        matches = [
            idx
            for idx, name in enumerate(dataset.names)
            if str(name).strip().casefold() == normalized
        ]
        if not matches:
            raise ValueError(f"No existe el nodo depot '{depot_name_or_index}' en el dataset")
        depot_index = matches[0]
    else:
        depot_index = int(depot_name_or_index)

    if depot_index < 0 or depot_index >= dataset.n_nodes:
        raise ValueError(f"depot_index fuera de rango: {depot_index}")

    for matrix_name in ("distance_matrix", "time_matrix"):
        matrix = getattr(dataset, matrix_name)
        if matrix.ndim != 2:
            raise ValueError(f"{matrix_name} debe ser una matriz 2D")
        if matrix.shape[0] <= depot_index or matrix.shape[1] <= depot_index:
            raise ValueError(
                f"{matrix_name} no contiene fila/columna para depot_index {depot_index}"
            )

    return Dataset(
        names=dataset.names,
        latitudes=dataset.latitudes,
        longitudes=dataset.longitudes,
        restringe_camion=dataset.restringe_camion,
        poblacion=dataset.poblacion,
        distance_matrix=dataset.distance_matrix,
        time_matrix=dataset.time_matrix,
        depot_index=depot_index,
    )


def _haversine_distances_from_point(
    longitude: float,
    latitude: float,
    longitudes: np.ndarray,
    latitudes: np.ndarray,
) -> np.ndarray:
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


def estimate_internal_minutes_per_km(dataset: Dataset) -> float:
    """Estima velocidad interna desde la matriz OD existente, sin datos externos."""
    distances = np.asarray(dataset.distance_matrix, dtype=float)
    times = np.asarray(dataset.time_matrix, dtype=float)
    if distances.shape != times.shape:
        raise ValueError("Las matrices de distancia y tiempo deben tener la misma forma")

    valid = (
        np.isfinite(distances)
        & np.isfinite(times)
        & (distances > 0)
        & (times > 0)
    )
    if not np.any(valid):
        raise ValueError("No hay pares OD positivos para estimar minutos por km")
    return float(np.median(times[valid] / distances[valid]))


def dataset_with_virtual_depot(
    dataset: Dataset,
    *,
    name: str,
    latitude: float,
    longitude: float,
    minutes_per_km: float | None = None,
) -> Dataset:
    """Devuelve un dataset con un depot virtual añadido al final.

    Las matrices OD originales se conservan. Solo se rellena la fila/columna
    del depot virtual con distancias rectas y tiempos estimados internamente.
    """
    latitude = float(latitude)
    longitude = float(longitude)
    if not np.isfinite(latitude) or not np.isfinite(longitude):
        raise ValueError("Las coordenadas del depot virtual deben ser finitas")

    ratio = (
        estimate_internal_minutes_per_km(dataset)
        if minutes_per_km is None
        else float(minutes_per_km)
    )
    if not np.isfinite(ratio) or ratio <= 0:
        raise ValueError("minutes_per_km debe ser positivo y finito")

    n = dataset.n_nodes
    virtual_name = str(name).strip() or VIRTUAL_DEPOT_NAME_PREFIX
    existing_names = {str(item).strip().casefold() for item in dataset.names}
    if virtual_name.casefold() in existing_names:
        virtual_name = f"{VIRTUAL_DEPOT_NAME_PREFIX} ({n})"

    distances = _haversine_distances_from_point(
        longitude,
        latitude,
        np.asarray(dataset.longitudes, dtype=float),
        np.asarray(dataset.latitudes, dtype=float),
    )
    times = distances * ratio

    distance_matrix = np.zeros((n + 1, n + 1), dtype=float)
    time_matrix = np.zeros((n + 1, n + 1), dtype=float)
    distance_matrix[:n, :n] = np.asarray(dataset.distance_matrix, dtype=float)
    time_matrix[:n, :n] = np.asarray(dataset.time_matrix, dtype=float)
    distance_matrix[n, :n] = distances
    distance_matrix[:n, n] = distances
    time_matrix[n, :n] = times
    time_matrix[:n, n] = times

    return Dataset(
        names=[*dataset.names, virtual_name],
        latitudes=np.append(np.asarray(dataset.latitudes, dtype=float), latitude),
        longitudes=np.append(np.asarray(dataset.longitudes, dtype=float), longitude),
        restringe_camion=np.append(np.asarray(dataset.restringe_camion, dtype=int), 0),
        poblacion=np.append(np.asarray(dataset.poblacion, dtype=int), 0),
        distance_matrix=distance_matrix,
        time_matrix=time_matrix,
        depot_index=n,
    )
