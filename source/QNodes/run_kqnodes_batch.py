"""
run_kqnodes_batch.py — Experimentos K-particiones con QNodes, N=8
=================================================================
Ejecuta KQNodes(k=2) y KQNodes(k=3) sobre los 10 casos definidos para
N=8 (N8A.csv), compartiendo el subsistema y la cache de bipartir entre
ambas ejecuciones para cada caso.

Optimización clave
------------------
Por caso se llama sia_preparar_subsistema UNA sola vez. Luego:
  - ejecutar_k(k=2) → baseline (== QNodes TV-03)
  - ejecutar_k(k=3) → hereda sia_subsistema.memo de k=2

Escribe los resultados en:
    source/QNodes/results/resultados_kqnodes_n8.csv

Columnas del CSV
----------------
caso_id, descripcion, alcance, mecanismo,
q_perdida, q_tiempo,
kq_k2_perdida, kq_k2_tiempo,
kq_k3_perdida, kq_k3_tiempo

Uso
---
cd source\\QNodes
uv run python run_kqnodes_batch.py
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from src.strategies.kqnodes import KQNodes

# ── Constantes ────────────────────────────────────────────────────────────────
N      = 8
ESTADO = "10000000"
COND   = "1" * N
K_VALS = [2, 3]

QNODES_ROOT = Path(__file__).resolve().parent
SALIDA_CSV  = QNODES_ROOT / "results" / "resultados_kqnodes_n8.csv"


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
    ruta = QNODES_ROOT / "src" / ".samples" / f"N{N}A.csv"
    return np.genfromtxt(str(ruta), delimiter=",")


def _ejecutar(caso: Caso, tpm: np.ndarray) -> dict:
    """
    Por caso construye el subsistema UNA sola vez y corre k=2 y k=3
    compartiendo sia_subsistema.memo (cache de bipartir).

    k=2 actúa como baseline QNodes (TV-03 validado).
    k=3 hereda todos los bipartir ya calculados por k=2.
    """
    fila: dict = {
        "caso_id":     caso.id,
        "descripcion": caso.descripcion,
        "alcance":     caso.alcance,
        "mecanismo":   caso.mecanismo,
    }

    solver = KQNodes(tpm, k=2)

    # ── Preparar subsistema una sola vez ──────────────────────────────────────
    try:
        solver.sia_preparar_subsistema(
            ESTADO, caso.condicion, caso.alcance, caso.mecanismo
        )
    except Exception as exc:
        print(f"  [ERROR preparar subsistema] {exc}")
        for k in K_VALS:
            fila[f"kq_k{k}_perdida"] = None
            fila[f"kq_k{k}_tiempo"]  = None
        fila["q_perdida"] = None
        fila["q_tiempo"]  = None
        return fila

    # ── k=2 (== baseline QNodes, TV-03) ──────────────────────────────────────
    try:
        t0  = time.perf_counter()
        sol = solver.ejecutar_k(k=2)
        t_k2 = round(time.perf_counter() - t0, 6)
        fila["q_perdida"]      = float(sol.perdida)   # baseline reutilizado
        fila["q_tiempo"]       = t_k2
        fila["kq_k2_perdida"]  = float(sol.perdida)
        fila["kq_k2_tiempo"]   = t_k2
    except Exception as exc:
        print(f"  [ERROR kqnodes k=2] {exc}")
        fila["q_perdida"]     = None
        fila["q_tiempo"]      = None
        fila["kq_k2_perdida"] = None
        fila["kq_k2_tiempo"]  = None

    # ── k=3 (hereda sia_subsistema.memo de k=2) ───────────────────────────────
    try:
        t0  = time.perf_counter()
        sol = solver.ejecutar_k(k=3)
        fila["kq_k3_perdida"] = float(sol.perdida)
        fila["kq_k3_tiempo"]  = round(time.perf_counter() - t0, 6)
    except Exception as exc:
        print(f"  [ERROR kqnodes k=3] {exc}")
        fila["kq_k3_perdida"] = None
        fila["kq_k3_tiempo"]  = None

    return fila


def main():
    sep = "=" * 68
    print(sep)
    print("  KQNodes Batch N=8  |  k ∈ {2,3}  →  resultados_kqnodes_n8.csv")
    print("  Subsistema compartido por caso | bipartir.memo heredado k2→k3")
    print(sep)

    tpm = _cargar_tpm()
    print(f"  TPM: N{N}A.csv  shape={tpm.shape}\n")

    filas = []
    for caso in CASOS:
        print(f"[{caso.id}] {caso.descripcion}")
        fila = _ejecutar(caso, tpm)
        filas.append(fila)

        q_p  = fila.get("q_perdida")
        k2_p = fila.get("kq_k2_perdida")
        k3_p = fila.get("kq_k3_perdida")
        k2_t = fila.get("kq_k2_tiempo")
        k3_t = fila.get("kq_k3_tiempo")

        print(f"  baseline/k=2: perdida={k2_p}  t={k2_t}s")
        print(f"  k=3         : perdida={k3_p}  t={k3_t}s")
        print()

    # ── Guardar CSV ──────────────────────────────────────────────────────────
    cols = [
        "caso_id", "descripcion", "alcance", "mecanismo",
        "q_perdida", "q_tiempo",
        "kq_k2_perdida", "kq_k2_tiempo",
        "kq_k3_perdida", "kq_k3_tiempo",
    ]
    df = pd.DataFrame(filas, columns=cols)
    SALIDA_CSV.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(SALIDA_CSV, index=False, encoding="utf-8-sig")
    print(sep)
    print(f"  CSV guardado → {SALIDA_CSV}")
    print(sep)


if __name__ == "__main__":
    main()
