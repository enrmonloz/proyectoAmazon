"""Carga de matrices OD externas para un depot adicional.

Este modulo prepara la estructura para integrar tablas externas sin modificar
la logica de rutas todavia.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

from .data_loader import Dataset


_REQUIRED_COLUMNS = ("center_name", "destination", "distance_km", "time_min")


def _normalize_text(value: object) -> str:
    return str(value).strip()


def _normalize_key(value: object) -> str:
    return _normalize_text(value).casefold()


def _validate_columns(df: pd.DataFrame) -> None:
    missing = set(_REQUIRED_COLUMNS) - set(df.columns)
    if missing:
        raise ValueError(
            "Faltan columnas en la tabla OD externa: "
            f"{sorted(missing)}. Encontradas: {df.columns.tolist()}"
        )


def _validate_numeric(df: pd.DataFrame, columns: Iterable[str]) -> None:
    for col in columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    if df[list(columns)].isna().any().any():
        raise ValueError("Hay valores no numericos o nulos en la tabla OD externa")
    if (df["distance_km"] < 0).any() or (df["time_min"] < 0).any():
        raise ValueError("Hay distancias o tiempos negativos en la tabla OD externa")


def load_center_od_from_excel(path: str | Path, center_name: str) -> pd.DataFrame:
    """Carga una tabla OD externa desde Excel para un centro especifico."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"No se encuentra el archivo OD externo: {path}")

    df = pd.read_excel(path)
    df = df.copy()
    df.columns = [_normalize_text(col) for col in df.columns]
    _validate_columns(df)

    df["center_name"] = df["center_name"].apply(_normalize_text)
    df["destination"] = df["destination"].apply(_normalize_text)
    _validate_numeric(df, ["distance_km", "time_min"])

    center_key = _normalize_key(center_name)
    df = df[df["center_name"].apply(_normalize_key) == center_key]
    if df.empty:
        raise ValueError(f"No hay filas OD para el centro '{center_name}'")

    if df["destination"].duplicated().any():
        duplicates = df[df["destination"].duplicated()]["destination"].tolist()
        raise ValueError(f"Destinos duplicados en la tabla OD externa: {duplicates}")

    return df[list(_REQUIRED_COLUMNS)].reset_index(drop=True)


def dataset_with_external_depot_od(
    dataset: Dataset,
    center_name: str,
    latitude: float,
    longitude: float,
    od_table: pd.DataFrame,
) -> Dataset:
    """Devuelve un dataset extendido con OD externo para un nuevo depot."""
    if _normalize_key(center_name) in {_normalize_key(name) for name in dataset.names}:
        raise ValueError("center_name ya existe en el dataset base")

    df = od_table.copy()
    df.columns = [_normalize_text(col) for col in df.columns]
    _validate_columns(df)

    df["center_name"] = df["center_name"].apply(_normalize_text)
    df["destination"] = df["destination"].apply(_normalize_text)
    _validate_numeric(df, ["distance_km", "time_min"])

    center_key = _normalize_key(center_name)
    if any(df["center_name"].apply(_normalize_key) != center_key):
        raise ValueError("La tabla OD externa contiene multiples center_name")

    if df["destination"].duplicated().any():
        duplicates = df[df["destination"].duplicated()]["destination"].tolist()
        raise ValueError(f"Destinos duplicados en la tabla OD externa: {duplicates}")

    destination_map = {
        _normalize_key(dest): (float(dist), float(time))
        for dest, dist, time in df[["destination", "distance_km", "time_min"]].itertuples(index=False)
    }

    missing = [
        name for name in dataset.names if _normalize_key(name) not in destination_map
    ]
    if missing:
        raise ValueError(
            "Faltan destinos en la tabla OD externa: "
            f"{missing}"
        )

    n = dataset.n_nodes
    distance_matrix = np.zeros((n + 1, n + 1), dtype=float)
    time_matrix = np.zeros((n + 1, n + 1), dtype=float)
    distance_matrix[:n, :n] = np.asarray(dataset.distance_matrix, dtype=float)
    time_matrix[:n, :n] = np.asarray(dataset.time_matrix, dtype=float)

    for idx, name in enumerate(dataset.names):
        dist, time = destination_map[_normalize_key(name)]
        distance_matrix[n, idx] = dist
        distance_matrix[idx, n] = dist
        time_matrix[n, idx] = time
        time_matrix[idx, n] = time

    distance_matrix[n, n] = 0.0
    time_matrix[n, n] = 0.0

    return Dataset(
        names=list(dataset.names) + [center_name],
        latitudes=np.append(np.asarray(dataset.latitudes, dtype=float), float(latitude)),
        longitudes=np.append(np.asarray(dataset.longitudes, dtype=float), float(longitude)),
        restringe_camion=np.append(np.asarray(dataset.restringe_camion, dtype=int), 0),
        poblacion=np.append(np.asarray(dataset.poblacion, dtype=int), 0),
        distance_matrix=distance_matrix,
        time_matrix=time_matrix,
        depot_index=n,
    )
