"""Calculo de demanda (paquetes) y tiempo nodal por municipio.

A partir de la poblacion y unos parametros de usuario (penetracion de mercado,
tiempo de servicio por paquete y tiempo medio de conduccion entre paquetes
dentro del municipio) se obtiene:

- ``packages_per_node``: paquetes a entregar en cada nodo (entero).
- ``service_time_per_node``: minutos totales que se gastan dentro del nodo
  para entregar todos sus paquetes.

Orden de calculo de paquetes:

calibracion -> demanda base -> deposito cero -> estacionalidad -> redondeo ->
deposito cero -> validacion final.

El deposito siempre tiene 0 paquetes y 0 tiempo de servicio.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class DemandConfig:
    """Parametros de usuario para el calculo de demanda.

    - ``market_penetration``: fraccion de la poblacion que recibe paquete (0..1).
    - ``service_time_per_package_min``: minutos por paquete (entrega).
    - ``inter_package_time_min``: minutos medios de conduccion entre paquetes
      dentro del mismo municipio.
    - ``seasonality_multiplier``: factor multiplicativo sobre la demanda base.
    - ``target_daily_volume``: volumen diario objetivo opcional. Si se informa,
      sustituye a ``market_penetration`` mediante calibracion.
    """

    market_penetration: float
    service_time_per_package_min: float
    inter_package_time_min: float
    seasonality_multiplier: float = 1.0
    target_daily_volume: float | None = None

    def validate(self) -> None:
        if not np.isfinite(self.market_penetration):
            raise ValueError("market_penetration debe ser finito")
        if not (0.0 <= self.market_penetration <= 1.0):
            raise ValueError("market_penetration debe estar en [0, 1]")
        if not np.isfinite(self.service_time_per_package_min):
            raise ValueError("service_time_per_package_min debe ser finito")
        if self.service_time_per_package_min < 0:
            raise ValueError("service_time_per_package_min no puede ser negativo")
        if not np.isfinite(self.inter_package_time_min):
            raise ValueError("inter_package_time_min debe ser finito")
        if self.inter_package_time_min < 0:
            raise ValueError("inter_package_time_min no puede ser negativo")
        if not np.isfinite(self.seasonality_multiplier):
            raise ValueError("seasonality_multiplier debe ser finito")
        if self.seasonality_multiplier <= 0:
            raise ValueError("seasonality_multiplier debe ser positivo")
        if self.target_daily_volume is not None:
            if not np.isfinite(self.target_daily_volume):
                raise ValueError("target_daily_volume debe ser finito")
            if self.target_daily_volume <= 0:
                raise ValueError("target_daily_volume debe ser positivo")


def _population_without_depot(poblacion: np.ndarray, depot_index: int) -> np.ndarray:
    pop = np.asarray(poblacion, dtype=float)
    if pop.ndim != 1:
        raise ValueError("poblacion debe ser un vector unidimensional")
    if np.any(~np.isfinite(pop)):
        raise ValueError("poblacion contiene valores no finitos")
    if np.any(pop < 0):
        raise ValueError("poblacion no puede contener valores negativos")

    mask = np.ones(len(pop), dtype=bool)
    if 0 <= depot_index < len(pop):
        mask[depot_index] = False
    return pop[mask]


def calibrate_market_penetration(
    poblacion: np.ndarray,
    depot_index: int,
    target_daily_volume: float,
) -> float:
    """Calcula la penetracion implicita para un volumen diario objetivo."""
    if target_daily_volume <= 0:
        raise ValueError("target_daily_volume debe ser positivo")

    total_population = float(_population_without_depot(poblacion, depot_index).sum())
    if total_population <= 0:
        raise ValueError("No se puede calibrar demanda sin poblacion no-deposito")

    penetration = float(target_daily_volume) / total_population
    if penetration > 1.0:
        raise ValueError(
            "target_daily_volume implica una penetracion de mercado superior a 1"
        )
    return penetration


def effective_market_penetration(
    poblacion: np.ndarray,
    config: DemandConfig,
    depot_index: int,
) -> float:
    """Devuelve la penetracion realmente usada por la configuracion."""
    config.validate()
    if config.target_daily_volume is None:
        return float(config.market_penetration)
    return calibrate_market_penetration(
        poblacion,
        depot_index,
        float(config.target_daily_volume),
    )


def apply_seasonality(packages: np.ndarray, seasonality_multiplier: float) -> np.ndarray:
    """Escala la demanda por estacionalidad y redondea a paquetes enteros."""
    if not np.isfinite(seasonality_multiplier):
        raise ValueError("seasonality_multiplier debe ser finito")
    if seasonality_multiplier <= 0:
        raise ValueError("seasonality_multiplier debe ser positivo")
    scaled = np.asarray(packages, dtype=float) * float(seasonality_multiplier)
    if np.any(~np.isfinite(scaled)):
        raise ValueError("packages contiene valores no finitos")
    return np.rint(scaled).astype(int)


def compute_packages(poblacion: np.ndarray, config: DemandConfig, depot_index: int) -> np.ndarray:
    """Devuelve un vector entero de paquetes por nodo.

    Si ``target_daily_volume`` esta definido, primero se calibra la penetracion
    necesaria para aproximar ese total. Despues se calcula la demanda base,
    se fuerza el deposito a cero, se aplica estacionalidad, se redondea, se
    fuerza de nuevo el deposito a cero y se valida el resultado final.
    """
    config.validate()
    pop = np.asarray(poblacion, dtype=float)
    non_depot_population = float(_population_without_depot(pop, depot_index).sum())

    penetration = effective_market_penetration(pop, config, depot_index)

    pkgs_base = pop * penetration
    if 0 <= depot_index < len(pkgs_base):
        pkgs_base[depot_index] = 0.0

    pkgs = apply_seasonality(pkgs_base, config.seasonality_multiplier)
    pkgs = np.maximum(pkgs, 0)
    if 0 <= depot_index < len(pkgs):
        pkgs[depot_index] = 0

    if np.any(pkgs < 0):
        raise ValueError("packages_per_node no puede contener valores negativos")
    if 0 <= depot_index < len(pkgs) and pkgs[depot_index] != 0:
        raise ValueError("El deposito debe tener 0 paquetes")
    if penetration > 0 and non_depot_population > 0 and int(pkgs.sum()) <= 0:
        raise ValueError("La demanda calculada debe ser positiva")
    return pkgs


def compute_node_service_time(packages: np.ndarray, config: DemandConfig) -> np.ndarray:
    """Tiempo (min) que cuesta servir todos los paquetes de cada nodo.

    Modelo simple: cada paquete suma ``service_time_per_package_min`` y
    ``inter_package_time_min``. El deposito siempre tiene 0.
    """
    config.validate()
    per_pkg = float(config.service_time_per_package_min) + float(config.inter_package_time_min)
    return np.asarray(packages, dtype=float) * per_pkg
