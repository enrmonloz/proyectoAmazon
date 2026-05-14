"""Smoke tests sin dependencia de OR-Tools.

Verifica:
- Carga del dataset (121 nodos, deposito en SVQ1).
- Calculo de paquetes y tiempos de servicio.
- Split delivery por tiempo: nodos grandes generan rutas dedicadas.
- Validaciones basicas de input.

Uso: ``python tests/test_pipeline.py``
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.data_loader import load_dataset
from src.demand import (
    DemandConfig,
    apply_seasonality,
    calibrate_market_penetration,
    compute_node_service_time,
    compute_packages,
)
from src.split_delivery import split_oversized_nodes


DATA_DIR = ROOT / "data"


def assert_eq(actual, expected, msg: str) -> None:
    if actual != expected:
        raise AssertionError(f"{msg}: esperado {expected}, obtenido {actual}")
    print(f"  OK {msg}")


def assert_close(actual: float, expected: float, tolerance: float, msg: str) -> None:
    if abs(actual - expected) > tolerance:
        raise AssertionError(
            f"{msg}: esperado {expected} +/- {tolerance}, obtenido {actual}"
        )
    print(f"  OK {msg}")


def assert_raises(fn, expected_msg: str) -> None:
    try:
        fn()
    except ValueError:
        print(f"  OK {expected_msg}")
        return
    raise AssertionError(f"Deberia fallar: {expected_msg}")


def test_dataset_loads() -> None:
    print("test_dataset_loads")
    ds = load_dataset(
        poblacion_path=str(DATA_DIR / "poblacion.csv"),
        rutas_path=str(DATA_DIR / "rutasDistTiempo.csv"),
    )
    assert_eq(ds.n_nodes, 122, "Numero total de nodos")
    assert_eq(ds.names[ds.depot_index], "SVQ1", "Deposito")
    assert_eq(ds.distance_matrix.shape, (122, 122), "Forma matriz distancia")
    assert_eq(ds.time_matrix.shape, (122, 122), "Forma matriz tiempo")
    for capital_name in ("Cádiz", "Málaga", "Córdoba", "Huelva", "Granada"):
        if capital_name not in ds.names:
            raise AssertionError(f"Falta capital: {capital_name}")
    print("  OK Las capitales estan presentes")


def test_demand_and_split() -> None:
    print("test_demand_and_split")
    ds = load_dataset(
        poblacion_path=str(DATA_DIR / "poblacion.csv"),
        rutas_path=str(DATA_DIR / "rutasDistTiempo.csv"),
    )
    cfg = DemandConfig(
        market_penetration=0.001,
        service_time_per_package_min=2.0,
        inter_package_time_min=1.0,
    )
    pkgs = compute_packages(ds.poblacion, cfg, ds.depot_index)
    if pkgs[ds.depot_index] != 0:
        raise AssertionError("Deposito deberia tener 0 paquetes")
    if pkgs.sum() <= 0:
        raise AssertionError("La demanda total deberia ser > 0")
    print(f"  OK Paquetes totales: {int(pkgs.sum())}")

    service = compute_node_service_time(pkgs, cfg)
    if not np.allclose(service[ds.depot_index], 0.0):
        raise AssertionError("Servicio en deposito deberia ser 0")

    res = split_oversized_nodes(
        names=ds.names,
        packages=pkgs,
        service_time_per_node=service,
        distance_matrix=ds.distance_matrix,
        time_matrix=ds.time_matrix,
        depot_index=ds.depot_index,
        max_workday_min=8 * 60,
        service_time_per_package_min=cfg.service_time_per_package_min,
        inter_package_time_min=cfg.inter_package_time_min,
    )
    if not res.dedicated_routes:
        raise AssertionError("Con 0.1% de penetracion Malaga deberia generar rutas dedicadas")

    # Las rutas dedicadas deben ser para los nodos grandes y/o lejanos.
    big_nodes = {r.node_name for r in res.dedicated_routes}
    for expected in ("Málaga", "Córdoba"):
        if expected not in big_nodes:
            raise AssertionError(f"{expected} deberia aparecer entre las rutas dedicadas")
    print(f"  OK Rutas dedicadas generadas: {len(res.dedicated_routes)}")
    print(f"  OK Nodos con dedicada: {sorted(big_nodes)}")

    # Comprobar que ninguna ruta dedicada excede la jornada.
    for r in res.dedicated_routes:
        if r.total_time_min > 8 * 60 + 1e-6:
            raise AssertionError(
                f"Ruta dedicada de {r.node_name} excede jornada: {r.total_time_min:.1f} min"
            )
    print("  OK Ninguna ruta dedicada supera la jornada maxima")


def test_demand_fixed_penetration() -> None:
    print("test_demand_fixed_penetration")
    poblacion = np.array([1000, 2000, 500])
    cfg = DemandConfig(
        market_penetration=0.10,
        service_time_per_package_min=2.0,
        inter_package_time_min=1.0,
    )
    pkgs = compute_packages(poblacion, cfg, depot_index=1)
    if not np.array_equal(pkgs, np.array([100, 0, 50])):
        raise AssertionError(f"Paquetes inesperados: {pkgs}")
    print("  OK Penetracion fija y deposito cero")


def test_demand_target_calibration_allows_rounding_tolerance() -> None:
    print("test_demand_target_calibration_allows_rounding_tolerance")
    poblacion = np.array([101, 101, 0])
    target_daily_volume = 51.0
    depot_index = 2

    penetration = calibrate_market_penetration(
        poblacion,
        depot_index=depot_index,
        target_daily_volume=target_daily_volume,
    )
    assert_close(
        penetration,
        target_daily_volume / 202.0,
        1e-12,
        "Penetracion calibrada",
    )

    cfg = DemandConfig(
        market_penetration=0.10,
        service_time_per_package_min=2.0,
        inter_package_time_min=1.0,
        target_daily_volume=target_daily_volume,
    )
    pkgs = compute_packages(poblacion, cfg, depot_index=depot_index)
    non_depot_nodes = len(poblacion) - 1
    rounding_tolerance = non_depot_nodes * 0.5
    assert_close(
        float(pkgs.sum()),
        target_daily_volume,
        rounding_tolerance,
        "Volumen objetivo aproximado tras redondeo",
    )
    if pkgs.sum() == int(target_daily_volume):
        raise AssertionError("Este caso debe demostrar una diferencia por redondeo")
    print(f"  OK Total final {int(pkgs.sum())} con objetivo {target_daily_volume:.0f}")


def test_demand_seasonality_after_base_demand() -> None:
    print("test_demand_seasonality_after_base_demand")
    poblacion = np.array([100, 400, 30])
    cfg = DemandConfig(
        market_penetration=0.10,
        service_time_per_package_min=2.0,
        inter_package_time_min=1.0,
        seasonality_multiplier=1.50,
    )
    pkgs = compute_packages(poblacion, cfg, depot_index=2)
    if not np.array_equal(pkgs, np.array([15, 60, 0])):
        raise AssertionError(f"Estacionalidad inesperada: {pkgs}")

    seasonal = apply_seasonality(np.array([10, 40, 0]), 1.50)
    if not np.array_equal(seasonal, np.array([15, 60, 0])):
        raise AssertionError(f"Helper de estacionalidad inesperado: {seasonal}")
    print("  OK Estacionalidad aplicada y deposito cero")


def test_demand_validations() -> None:
    print("test_demand_validations")
    poblacion = np.array([100, 200, 0])
    assert_raises(
        lambda: compute_packages(
            poblacion,
            DemandConfig(
                market_penetration=1.1,
                service_time_per_package_min=2.0,
                inter_package_time_min=1.0,
            ),
            depot_index=2,
        ),
        "Penetracion fuera de rango",
    )
    assert_raises(
        lambda: compute_packages(
            poblacion,
            DemandConfig(
                market_penetration=0.1,
                service_time_per_package_min=2.0,
                inter_package_time_min=1.0,
                target_daily_volume=0.0,
            ),
            depot_index=2,
        ),
        "Volumen objetivo no positivo",
    )
    assert_raises(
        lambda: compute_packages(
            poblacion,
            DemandConfig(
                market_penetration=0.1,
                service_time_per_package_min=2.0,
                inter_package_time_min=1.0,
                seasonality_multiplier=0.0,
            ),
            depot_index=2,
        ),
        "Estacionalidad no positiva",
    )
    assert_raises(
        lambda: compute_packages(
            poblacion,
            DemandConfig(
                market_penetration=0.1,
                service_time_per_package_min=2.0,
                inter_package_time_min=1.0,
                target_daily_volume=500.0,
            ),
            depot_index=2,
        ),
        "Volumen objetivo imposible",
    )


def main() -> None:
    test_dataset_loads()
    test_demand_and_split()
    test_demand_fixed_penetration()
    test_demand_target_calibration_allows_rounding_tolerance()
    test_demand_seasonality_after_base_demand()
    test_demand_validations()
    print("\nTodos los tests OK")


if __name__ == "__main__":
    main()
