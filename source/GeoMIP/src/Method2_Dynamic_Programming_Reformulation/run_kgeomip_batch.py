"""
run_kgeomip_batch.py — Experimentos K-particiones con GeoMIP, N=8
==================================================================
Ejecuta GeometricSIA (baseline), KGeoMIP(k=2) y KGeoMIP(k=3) sobre
los 10 casos definidos para N=8 (N8A.csv) y escribe los resultados en:

    source/GeoMIP/results/resultados_kgeomip_n8.csv

Columnas del CSV
----------------
caso_id, descripcion, alcance, mecanismo,
geo_perdida, geo_tiempo,
kgeo_k2_perdida, kgeo_k2_tiempo,
kgeo_k3_perdida, kgeo_k3_tiempo

Uso
---
cd source\\GeoMIP\\src\\Method2_Dynamic_Programming_Reformulation
uv run python run_kgeomip_batch.py
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

# ── Setup de aplicación (obligatorio antes de importar estrategias) ──────────
from src.models.base.application import aplicacion
aplicacion.pagina_sample_network = "A"

from src.controllers.manager import Manager
from src.controllers.strategies.geometric import GeometricSIA
from src.controllers.strategies.kgeomip import KGeoMIP

# ── Constantes ────────────────────────────────────────────────────────────────
N      = 8
ESTADO = "10000000"
COND   = "1" * N
K_VALS = [2, 3]

GEOMIP_ROOT = Path(__file__).resolve().parents[2]
SALIDA_CSV  = GEOMIP_ROOT / "results" / "resultados_kgeomip_n8.csv"


@dataclass
class Caso:
    id: str
    descripcion: str
    alcance: str
    mecanismo: str
    condicion: str = field(default=COND)


CASOS = [
    Caso("C01", "Completo ABCDEFGH|ABCDEFGH",      "11111111", "11111111"),
    Caso("C02", "Mitad sup ABCD|ABCD",             "11110000", "11110000"),
    Caso("C03", "Mitad inf EFGH|EFGH",             "00001111", "00001111"),
    Caso("C04", "Alternado pares ACEG|ACEG",       "10101010", "10101010"),
    Caso("C05", "Alternado impares BDFH|BDFH",     "01010101", "01010101"),
    Caso("C06", "Cruzado ABCD|EFGH",               "11110000", "00001111"),
    Caso("C07", "Cruzado EFGH|ABCD",               "00001111", "11110000"),
    Caso("C08", "Reducido AB|ABCD",                "11000000", "11110000"),
    Caso("C09", "Reducido ABCDEF|ABCDEF",          "11111100", "11111100"),
    Caso("C10", "Asimetrico ABCDE|BCDEFG",         "11111000", "01111110"),
]


def _cargar_tpm() -> np.ndarray:
    ruta = GEOMIP_ROOT / "data" / "samples" / f"N{N}A.csv"
    return np.genfromtxt(str(ruta), delimiter=",")


def _ejecutar(caso: Caso, tpm: np.ndarray) -> dict:
    """Corre geo-baseline + KGeoMIP(k) para todos los K_VALS."""
    fila: dict = {
        "caso_id": caso.id,
        "descripcion": caso.descripcion,
        "alcance": caso.alcance,
        "mecanismo": caso.mecanismo,
    }

    # ── Baseline GeometricSIA ───────────────────────────────────────────────
    try:
        t0 = time.perf_counter()
        sol = GeometricSIA(Manager(ESTADO)).aplicar_estrategia(
            caso.condicion, caso.alcance, caso.mecanismo, tpm
        )
        fila["geo_perdida"] = float(sol.perdida)
        fila["geo_tiempo"]  = round(time.perf_counter() - t0, 6)
    except Exception as exc:
        fila["geo_perdida"] = None
        fila["geo_tiempo"]  = None
        print(f"  [ERROR geo] {exc}")

    # ── KGeoMIP por cada k ──────────────────────────────────────────────────
    for k in K_VALS:
        try:
            t0 = time.perf_counter()
            sol = KGeoMIP(Manager(ESTADO), k=k).aplicar_estrategia(
                caso.condicion, caso.alcance, caso.mecanismo, tpm
            )
            fila[f"kgeo_k{k}_perdida"] = float(sol.perdida)
            fila[f"kgeo_k{k}_tiempo"]  = round(time.perf_counter() - t0, 6)
        except Exception as exc:
            fila[f"kgeo_k{k}_perdida"] = None
            fila[f"kgeo_k{k}_tiempo"]  = None
            print(f"  [ERROR kgeo k={k}] {exc}")

    return fila


def main():
    sep = "=" * 68
    print(sep)
    print("  KGeoMIP Batch N=8  |  k ∈ {2,3}  →  resultados_kgeomip_n8.csv")
    print(sep)

    tpm = _cargar_tpm()
    print(f"  TPM: N{N}A.csv  shape={tpm.shape}\n")

    filas = []
    for caso in CASOS:
        print(f"[{caso.id}] {caso.descripcion}")
        fila = _ejecutar(caso, tpm)
        filas.append(fila)

        geo_p  = fila.get("geo_perdida")
        k2_p   = fila.get("kgeo_k2_perdida")
        k3_p   = fila.get("kgeo_k3_perdida")
        geo_t  = fila.get("geo_tiempo")
        k2_t   = fila.get("kgeo_k2_tiempo")
        k3_t   = fila.get("kgeo_k3_tiempo")

        print(f"  geo   : perdida={geo_p}  t={geo_t}s")
        print(f"  k=2   : perdida={k2_p}  t={k2_t}s")
        print(f"  k=3   : perdida={k3_p}  t={k3_t}s")
        print()

    # ── Guardar CSV ──────────────────────────────────────────────────────────
    cols = [
        "caso_id", "descripcion", "alcance", "mecanismo",
        "geo_perdida", "geo_tiempo",
        "kgeo_k2_perdida", "kgeo_k2_tiempo",
        "kgeo_k3_perdida", "kgeo_k3_tiempo",
    ]
    df = pd.DataFrame(filas, columns=cols)
    SALIDA_CSV.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(SALIDA_CSV, index=False, encoding="utf-8-sig")
    print(f"{sep}")
    print(f"  CSV guardado → {SALIDA_CSV}")
    print(sep)


if __name__ == "__main__":
    main()
