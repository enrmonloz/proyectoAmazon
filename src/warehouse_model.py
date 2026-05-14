"""Modelos parametrizables de dimensionamiento y layout de almacén.

Reimplementa en Python la lógica de los scripts MATLAB de ``codes/almacen_amazon``:

- ``Almacen_dimension.m``: capacidad, huecos y reparto ABC.
- ``Almacen_1floor.m``: índice f y zonificación ABC en una planta.
- ``Almacen_3floor.m``: índice f 3D con penalización vertical.
- ``Almacen_vs.m``: comparación ABC por planta vs ABC global.
- ``Almacen_resultado_variable_3.m``: barrido paramétrico de porcentajes y
  movimientos ABC.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class Door:
    """Punto de entrada/salida usado por el índice f."""

    row: int
    col: int
    weight: float


# Presets exactos de los scripts MATLAB. Se mantienen separados porque los
# scripts no usan siempre la misma tercera puerta ni los mismos pesos.
ALMACEN_1FLOOR_DOORS: tuple[Door, ...] = (
    Door(1, 50, 0.25),
    Door(50, 10, 0.50),
    Door(50, 50, 0.25),
)

ALMACEN_3FLOOR_DOORS: tuple[Door, ...] = (
    Door(1, 50, 0.50),
    Door(50, 10, 0.25),
    Door(50, 50, 0.25),
)

ALMACEN_VS_DOORS: tuple[Door, ...] = (
    Door(1, 50, 0.50),
    Door(50, 10, 0.25),
    Door(50, 90, 0.25),
)


@dataclass(frozen=True)
class DimensionParams:
    """Parámetros físicos del dimensionamiento de almacén."""

    building_length_m: float = 300.0
    building_width_m: float = 150.0
    robotics_length_m: float = 210.0
    robotics_width_m: float = 95.0
    robotics_area_override_m2: float | None = 20_000.0
    shelf_length_m: float = 1.5
    shelf_width_m: float = 1.5
    useful_area_pct: float = 0.50
    shelves_per_floor_override: int | None = 5_000
    shelf_slots_main_a: int = 7
    shelf_slots_main_b: int = 3
    shelf_slots_main_c: int = 2
    shelf_slots_extra_a: int = 7
    shelf_slots_extra_b: int = 2
    packages_per_slot: int = 12
    occupancy_pct: float = 0.67
    floors: int = 3
    pct_a: float = 0.15
    pct_b: float = 0.15


@dataclass(frozen=True)
class DimensionResult:
    """Resultado de capacidad y reparto ABC."""

    building_area_m2: float
    robotics_area_exact_m2: float
    robotics_area_used_m2: float
    useful_area_m2: float
    shelf_area_m2: float
    theoretical_shelves_per_floor: float
    shelves_per_floor: int
    slots_per_shelf: int
    max_packages_per_shelf: float
    real_packages_per_shelf: float
    capacity_per_floor: float
    total_capacity: float
    pct_a: float
    pct_b: float
    pct_c: float
    packages_a: float
    packages_b: float
    packages_c: float

    def metrics_frame(self) -> pd.DataFrame:
        return pd.DataFrame(
            [
                ("Área total edificio", f"{self.building_area_m2:,.0f} m²"),
                ("Área robotizada exacta", f"{self.robotics_area_exact_m2:,.0f} m²"),
                ("Área robotizada usada", f"{self.robotics_area_used_m2:,.0f} m²"),
                ("Área útil por planta", f"{self.useful_area_m2:,.0f} m²"),
                ("Estanterías teóricas/planta", f"{self.theoretical_shelves_per_floor:,.1f}"),
                ("Estanterías de diseño/planta", f"{self.shelves_per_floor:,.0f}"),
                ("Huecos por estantería", f"{self.slots_per_shelf:,.0f}"),
                ("Capacidad máxima/estantería", f"{self.max_packages_per_shelf:,.0f} paquetes"),
                ("Capacidad real/estantería", f"{self.real_packages_per_shelf:,.2f} paquetes"),
                ("Capacidad por planta", f"{self.capacity_per_floor:,.0f} paquetes"),
                ("Capacidad total", f"{self.total_capacity:,.0f} paquetes"),
            ],
            columns=["Concepto", "Valor"],
        )

    def abc_frame(self) -> pd.DataFrame:
        return pd.DataFrame(
            [
                ("A", f"{self.pct_a:.1%}", self.packages_a),
                ("B", f"{self.pct_b:.1%}", self.packages_b),
                ("C", f"{self.pct_c:.1%}", self.packages_c),
            ],
            columns=["Zona", "% inventario", "Paquetes"],
        )


@dataclass(frozen=True)
class LayoutParams:
    """Parámetros del modelo de índice f y asignación ABC."""

    rows: int = 50
    cols: int = 100
    floors: int = 3
    doors: tuple[Door, ...] = ALMACEN_VS_DOORS
    pct_a: float = 0.15
    pct_b: float = 0.15
    move_a: float = 0.80
    move_b: float = 0.15
    cell_size_m: float = 1.5
    conveyor_speed_m_s: float = 1.2
    seconds_per_floor: float = 15.0
    normalize_door_weights: bool = True

    @property
    def pct_c(self) -> float:
        return max(0.0, 1.0 - self.pct_a - self.pct_b)

    @property
    def move_c(self) -> float:
        return max(0.0, 1.0 - self.move_a - self.move_b)


@dataclass(frozen=True)
class LayoutResult:
    """Resultado de un cálculo de layout."""

    f_matrix: np.ndarray
    abc_global: np.ndarray
    abc_by_floor: np.ndarray
    cost_global: float
    cost_by_floor: float
    improvement_pct: float
    vertical_penalty_cells: float
    params: LayoutParams

    @property
    def has_multiple_floors(self) -> bool:
        return self.f_matrix.ndim == 3 and self.f_matrix.shape[2] > 1


def normalize_weights(doors: Iterable[Door]) -> tuple[Door, ...]:
    """Devuelve puertas con pesos normalizados a 1."""
    doors = tuple(doors)
    total = sum(max(0.0, d.weight) for d in doors)
    if total <= 0:
        raise ValueError("La suma de pesos de puertas debe ser positiva")
    return tuple(Door(d.row, d.col, max(0.0, d.weight) / total) for d in doors)


def validate_percentages(*values: float, label: str = "porcentajes") -> None:
    if any(v < 0 for v in values):
        raise ValueError(f"Los {label} no pueden ser negativos")
    if sum(values) > 1.0 + 1e-9:
        raise ValueError(f"La suma de {label} no puede superar 100%")


def compute_dimension(params: DimensionParams) -> DimensionResult:
    """Calcula capacidad física y reparto ABC."""
    validate_percentages(params.pct_a, params.pct_b, label="porcentajes ABC")
    if params.floors <= 0:
        raise ValueError("El número de plantas debe ser positivo")
    if params.useful_area_pct <= 0 or params.occupancy_pct <= 0:
        raise ValueError("El área útil y la ocupación deben ser positivas")

    building_area = params.building_length_m * params.building_width_m
    robotics_exact = params.robotics_length_m * params.robotics_width_m
    robotics_used = (
        params.robotics_area_override_m2
        if params.robotics_area_override_m2 is not None
        else robotics_exact
    )
    shelf_area = params.shelf_length_m * params.shelf_width_m
    useful_area = robotics_used * params.useful_area_pct
    theoretical_shelves = useful_area / shelf_area
    shelves = (
        int(params.shelves_per_floor_override)
        if params.shelves_per_floor_override is not None
        else int(np.floor(theoretical_shelves))
    )
    slots = (
        params.shelf_slots_main_a * params.shelf_slots_main_b * params.shelf_slots_main_c
        + params.shelf_slots_extra_a * params.shelf_slots_extra_b
    )
    max_packages = slots * params.packages_per_slot
    real_packages = max_packages * params.occupancy_pct
    capacity_floor = real_packages * shelves
    total_capacity = capacity_floor * params.floors
    pct_c = 1.0 - params.pct_a - params.pct_b

    return DimensionResult(
        building_area_m2=building_area,
        robotics_area_exact_m2=robotics_exact,
        robotics_area_used_m2=robotics_used,
        useful_area_m2=useful_area,
        shelf_area_m2=shelf_area,
        theoretical_shelves_per_floor=theoretical_shelves,
        shelves_per_floor=shelves,
        slots_per_shelf=slots,
        max_packages_per_shelf=max_packages,
        real_packages_per_shelf=real_packages,
        capacity_per_floor=capacity_floor,
        total_capacity=total_capacity,
        pct_a=params.pct_a,
        pct_b=params.pct_b,
        pct_c=pct_c,
        packages_a=total_capacity * params.pct_a,
        packages_b=total_capacity * params.pct_b,
        packages_c=total_capacity * pct_c,
    )


def compute_f_matrix(params: LayoutParams) -> tuple[np.ndarray, float]:
    """Calcula matriz de índice f siguiendo el criterio de los MATLAB."""
    validate_percentages(params.pct_a, params.pct_b, label="porcentajes ABC")
    validate_percentages(params.move_a, params.move_b, label="movimientos ABC")
    if params.rows <= 0 or params.cols <= 0 or params.floors <= 0:
        raise ValueError("Filas, columnas y plantas deben ser positivas")
    if params.cell_size_m <= 0:
        raise ValueError("El tamaño de celda debe ser positivo")

    doors = normalize_weights(params.doors) if params.normalize_door_weights else params.doors
    if not doors:
        raise ValueError("Debe haber al menos una puerta")
    for door in doors:
        if door.row < 1 or door.row > params.rows or door.col < 1 or door.col > params.cols:
            raise ValueError(
                f"Puerta fuera de rango: fila {door.row}, columna {door.col}"
            )

    row_idx = np.arange(1, params.rows + 1)[:, None]
    col_idx = np.arange(1, params.cols + 1)[None, :]
    base = np.zeros((params.rows, params.cols), dtype=float)
    for door in doors:
        base += door.weight * (np.abs(row_idx - door.row) + np.abs(col_idx - door.col))

    vertical_m = params.conveyor_speed_m_s * params.seconds_per_floor
    vertical_penalty_cells = vertical_m / params.cell_size_m

    if params.floors == 1:
        return base, vertical_penalty_cells

    penalties = vertical_penalty_cells * np.arange(1, params.floors + 1)
    f_matrix = np.stack([base + penalty for penalty in penalties], axis=2)
    return f_matrix, vertical_penalty_cells


def assign_abc_global(f_matrix: np.ndarray, pct_a: float, pct_b: float) -> np.ndarray:
    """Asigna ABC ordenando todas las celdas del edificio juntas."""
    validate_percentages(pct_a, pct_b, label="porcentajes ABC")
    total = f_matrix.size
    num_a = int(round(total * pct_a))
    num_b = int(round(total * pct_b))

    abc = np.zeros(f_matrix.shape, dtype=np.int8)
    order = np.argsort(f_matrix, axis=None)
    flat = abc.reshape(-1)
    flat[order[:num_a]] = 1
    flat[order[num_a : num_a + num_b]] = 2
    flat[order[num_a + num_b :]] = 3
    return abc


def assign_abc_by_floor(f_matrix: np.ndarray, pct_a: float, pct_b: float) -> np.ndarray:
    """Asigna ABC planta a planta, como la estrategia individual del MATLAB."""
    validate_percentages(pct_a, pct_b, label="porcentajes ABC")
    if f_matrix.ndim == 2:
        return assign_abc_global(f_matrix, pct_a, pct_b)

    abc = np.zeros(f_matrix.shape, dtype=np.int8)
    for floor in range(f_matrix.shape[2]):
        abc[:, :, floor] = assign_abc_global(f_matrix[:, :, floor], pct_a, pct_b)
    return abc


def weighted_layout_cost(
    f_matrix: np.ndarray,
    abc_matrix: np.ndarray,
    move_a: float,
    move_b: float,
) -> float:
    """Calcula coste logístico diario ponderado por movimientos ABC."""
    validate_percentages(move_a, move_b, label="movimientos ABC")
    move_c = 1.0 - move_a - move_b
    total_cost = 0.0
    for category, movement in ((1, move_a), (2, move_b), (3, move_c)):
        mask = abc_matrix == category
        count = int(mask.sum())
        if count == 0:
            continue
        total_cost += float(f_matrix[mask].sum()) * movement / count
    return total_cost


def solve_layout(params: LayoutParams) -> LayoutResult:
    """Calcula f, ABC global, ABC por planta y comparación de coste."""
    f_matrix, vertical_penalty_cells = compute_f_matrix(params)
    abc_global = assign_abc_global(f_matrix, params.pct_a, params.pct_b)
    abc_by_floor = assign_abc_by_floor(f_matrix, params.pct_a, params.pct_b)
    cost_global = weighted_layout_cost(f_matrix, abc_global, params.move_a, params.move_b)
    cost_by_floor = weighted_layout_cost(f_matrix, abc_by_floor, params.move_a, params.move_b)
    improvement = (
        (cost_by_floor - cost_global) / cost_by_floor * 100.0
        if cost_by_floor > 0
        else 0.0
    )
    return LayoutResult(
        f_matrix=f_matrix,
        abc_global=abc_global,
        abc_by_floor=abc_by_floor,
        cost_global=cost_global,
        cost_by_floor=cost_by_floor,
        improvement_pct=improvement,
        vertical_penalty_cells=vertical_penalty_cells,
        params=params,
    )


def category_summary(abc_matrix: np.ndarray) -> pd.DataFrame:
    """Cuenta celdas por zona y planta."""
    rows: list[dict[str, object]] = []
    labels = {1: "A", 2: "B", 3: "C"}
    if abc_matrix.ndim == 2:
        for cat, label in labels.items():
            rows.append({"Planta": "Única", "Zona": label, "Celdas": int((abc_matrix == cat).sum())})
        return pd.DataFrame(rows)

    for floor in range(abc_matrix.shape[2]):
        floor_matrix = abc_matrix[:, :, floor]
        for cat, label in labels.items():
            rows.append(
                {
                    "Planta": floor + 1,
                    "Zona": label,
                    "Celdas": int((floor_matrix == cat).sum()),
                }
            )
    return pd.DataFrame(rows)


def floor_cost_summary(result: LayoutResult) -> pd.DataFrame:
    """Resume la penalización vertical y la distribución ABC por planta.

    En ``Almacen_3floor.m`` cada planta suma una penalización creciente
    ``[12, 24, 36]`` celdas con los parámetros por defecto. Esta tabla hace
    visible ese efecto y ayuda a auditar que las plantas superiores son más
    caras en el índice f.
    """
    f_matrix = result.f_matrix
    global_abc = result.abc_global
    by_floor_abc = result.abc_by_floor
    params = result.params

    if f_matrix.ndim == 2:
        f_matrix = f_matrix[:, :, None]
        global_abc = global_abc[:, :, None]
        by_floor_abc = by_floor_abc[:, :, None]

    rows: list[dict[str, float | int]] = []
    for floor_idx in range(f_matrix.shape[2]):
        f_slice = f_matrix[:, :, floor_idx]
        g_slice = global_abc[:, :, floor_idx]
        ind_slice = by_floor_abc[:, :, floor_idx]
        vertical_cells = (
            result.vertical_penalty_cells * (floor_idx + 1)
            if result.params.floors > 1
            else 0.0
        )
        rows.append(
            {
                "Planta": floor_idx + 1,
                "Penalización vertical (celdas)": vertical_cells,
                "Penalización vertical (m)": vertical_cells * params.cell_size_m,
                "f mínimo": float(f_slice.min()),
                "f medio": float(f_slice.mean()),
                "f máximo": float(f_slice.max()),
                "A global": int((g_slice == 1).sum()),
                "B global": int((g_slice == 2).sum()),
                "C global": int((g_slice == 3).sum()),
                "A por planta": int((ind_slice == 1).sum()),
                "B por planta": int((ind_slice == 2).sum()),
                "C por planta": int((ind_slice == 3).sum()),
            }
        )
    return pd.DataFrame(rows)


def sweep_abc_layout(
    base_params: LayoutParams,
    pct_a_values: Iterable[float],
    move_a_values: Iterable[float],
    b_inventory_share_of_remaining: float = 0.20,
    b_movement_share_of_remaining: float = 0.75,
) -> pd.DataFrame:
    """Barrido equivalente a ``Almacen_resultado_variable_3.m``.

    Para cada ``pct_A`` se calcula ``pct_B`` como proporción del inventario
    restante. Para cada ``mov_A`` se calcula ``mov_B`` como proporción de los
    movimientos restantes.
    """
    rows: list[dict[str, float]] = []
    for pct_a in pct_a_values:
        pct_b = (1.0 - pct_a) * b_inventory_share_of_remaining
        for move_a in move_a_values:
            move_b = (1.0 - move_a) * b_movement_share_of_remaining
            params = LayoutParams(
                rows=base_params.rows,
                cols=base_params.cols,
                floors=base_params.floors,
                doors=base_params.doors,
                pct_a=float(pct_a),
                pct_b=float(pct_b),
                move_a=float(move_a),
                move_b=float(move_b),
                cell_size_m=base_params.cell_size_m,
                conveyor_speed_m_s=base_params.conveyor_speed_m_s,
                seconds_per_floor=base_params.seconds_per_floor,
                normalize_door_weights=base_params.normalize_door_weights,
            )
            result = solve_layout(params)
            rows.append(
                {
                    "pct_A": pct_a,
                    "pct_B": pct_b,
                    "pct_C": 1.0 - pct_a - pct_b,
                    "mov_A": move_a,
                    "mov_B": move_b,
                    "mov_C": 1.0 - move_a - move_b,
                    "coste_por_planta": result.cost_by_floor,
                    "coste_global": result.cost_global,
                    "mejora_pct": result.improvement_pct,
                }
            )
    return pd.DataFrame(rows)
