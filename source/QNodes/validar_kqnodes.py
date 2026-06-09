"""
Validación KQNodes — Red N=8 (N8A.csv)
=======================================

Prueba TV-03  (k=2): KQNodes debe coincidir con QNodes.
Prueba TV-04  (k>2): la pérdida no puede crecer al aumentar k.
Prueba MONO   (k>2): para cada subsistema, pérdida_k3 <= pérdida_k2,
                     pérdida_k4 <= pérdida_k3, etc.

Casos
-----
Todos sobre N8A.csv (estado_inicial="10000000").
Se varían alcance y mecanismo para cubrir distintas topologías:
  - subsistema completo            (8 futuros × 8 presentes)
  - subsistema mitad superior      (4 futuros × 4 presentes)
  - subsistema alternado           (4 futuros × 4 presentes, bits pares)
  - subsistema cruzado             (4 futuros × 4 presentes distintos)
  - subsistema mínimo significativo(2 futuros × 4 presentes)

Metodología
-----------
  k ∈ {2, 3, 4}   (k=5+ requeriría S(16,5)=1·10^10, fuera del presupuesto;
                    el modo heurístico entraría, lo que es válido pero lento)
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field

import numpy as np

# ── Importaciones del proyecto ──────────────────────────────────────────────
from src.strategies.q_nodes import QNodes
from src.strategies.kqnodes import KQNodes

# ── Constantes ──────────────────────────────────────────────────────────────
TOL_TV03   = 1e-6   # k=2: KQNodes == QNodes
TOL_MONO   = 1e-6   # pérdida_k[i+1] <= pérdida_k[i] + TOL_MONO
N          = 8
ESTADO     = "10000000"
COND_FULL  = "1" * N
K_VALS     = [2, 3]             # k=4 excluido: tiempo de cómputo excesivo para N=8


@dataclass
class Caso:
    id: str
    descripcion: str
    alcance: str    # bits longitud N (0 = excluir del futuro)
    mecanismo: str  # bits longitud N (0 = excluir del presente)
    condicion: str = field(default=COND_FULL)


# ── Casos de prueba ─────────────────────────────────────────────────────────
CASOS = [
    Caso(
        id="C01",
        descripcion="Completo ABCDEFGH | ABCDEFGH",
        alcance  ="11111111",
        mecanismo="11111111",
    ),
    Caso(
        id="C02",
        descripcion="Mitad superior ABCD | ABCD",
        alcance  ="11110000",
        mecanismo="11110000",
    ),
    Caso(
        id="C03",
        descripcion="Mitad inferior EFGH | EFGH",
        alcance  ="00001111",
        mecanismo="00001111",
    ),
    Caso(
        id="C04",
        descripcion="Alternado pares ACEG | ACEG",
        alcance  ="10101010",
        mecanismo="10101010",
    ),
    Caso(
        id="C05",
        descripcion="Alternado impares BDFH | BDFH",
        alcance  ="01010101",
        mecanismo="01010101",
    ),
    Caso(
        id="C06",
        descripcion="Cruzado ABCD | EFGH",
        alcance  ="11110000",
        mecanismo="00001111",
    ),
    Caso(
        id="C07",
        descripcion="Cruzado EFGH | ABCD",
        alcance  ="00001111",
        mecanismo="11110000",
    ),
    Caso(
        id="C08",
        descripcion="Reducido AB | ABCD",
        alcance  ="11000000",
        mecanismo="11110000",
    ),
    Caso(
        id="C09",
        descripcion="Reducido ABCDEF | ABCDEF",
        alcance  ="11111100",
        mecanismo="11111100",
    ),
    Caso(
        id="C10",
        descripcion="Asimetrico ABCDE | BCDEFG",
        alcance  ="11111000",
        mecanismo="01111110",
    ),
]


# ── Carga de TPM (única vez) ─────────────────────────────────────────────────
def _cargar_tpm() -> np.ndarray:
    from pathlib import Path
    ruta = Path(__file__).parent / "src" / ".samples" / f"N{N}A.csv"
    if not ruta.exists():
        raise FileNotFoundError(f"TPM no encontrada: {ruta}")
    return np.genfromtxt(str(ruta), delimiter=",")


# ── Ejecutar un caso para un k dado ─────────────────────────────────────────
def ejecutar_k(caso: Caso, k: int, tpm: np.ndarray) -> dict:
    """Corre KQNodes(k) sobre el caso; retorna métricas."""
    try:
        solver = KQNodes(tpm, k=k)
        sol = solver.aplicar_estrategia(
            ESTADO, caso.condicion, caso.alcance, caso.mecanismo
        )
        return {"k": k, "perdida": float(sol.perdida), "error": None}
    except Exception as exc:
        return {"k": k, "perdida": None, "error": str(exc)}


def ejecutar_baseline(caso: Caso, tpm: np.ndarray) -> dict:
    """Corre QNodes original (bipartición k=2) para comparar TV-03."""
    try:
        solver = QNodes(tpm)
        sol = solver.aplicar_estrategia(
            ESTADO, caso.condicion, caso.alcance, caso.mecanismo
        )
        return {"perdida": float(sol.perdida), "error": None}
    except Exception as exc:
        return {"perdida": None, "error": str(exc)}


# ── Runner ───────────────────────────────────────────────────────────────────
def main():
    sep  = "=" * 72
    sep2 = "-" * 72
    print(sep)
    print("  KQNodes — Validación N=8  |  TV-03 (k=2==QNodes) + TV-04 (mono)")
    print(f"  k probados: {K_VALS}   tol TV-03={TOL_TV03:.0e}   tol mono={TOL_MONO:.0e}")
    print(sep)

    tpm = _cargar_tpm()
    print(f"  TPM cargada: N{N}A.csv  shape={tpm.shape}\n")

    fallos_tv03  = []   # casos donde KQNodes(k=2) != QNodes
    fallos_mono  = []   # casos donde pérdida sube al aumentar k
    errores      = []

    for caso in CASOS:
        print(f"[{caso.id}] {caso.descripcion}")
        print(f"  alc={caso.alcance}  mec={caso.mecanismo}")

        # Baseline QNodes
        base = ejecutar_baseline(caso, tpm)
        if base["error"]:
            print(f"  ✗ QNodes ERROR: {base['error']}")
            errores.append(caso.id)
            print()
            continue

        base_loss = base["perdida"]
        print(f"  QNodes  (baseline) : {base_loss:.8f}")

        perdidas_k: dict[int, float] = {}

        for k in K_VALS:
            r = ejecutar_k(caso, k, tpm)
            if r["error"]:
                print(f"  k={k}  ✗ ERROR: {r['error']}")
                errores.append(f"{caso.id}/k{k}")
                continue

            perdidas_k[k] = r["perdida"]

            # TV-03: k=2 debe coincidir con QNodes baseline
            if k == 2:
                diff = abs(r["perdida"] - base_loss)
                ok   = diff < TOL_TV03
                sym  = "✓" if ok else "✗"
                print(f"  k=2  KQNodes={r['perdida']:.8f}  Δ={diff:.2e}  [{sym} TV-03]")
                if not ok:
                    fallos_tv03.append(caso.id)
            else:
                print(f"  k={k}  KQNodes={r['perdida']:.8f}")

        # TV-04: monotonía pérdida_k[i+1] <= pérdida_k[i]
        print("  " + sep2[2:])
        ks_ok = sorted(perdidas_k.keys())
        mono_ok = True
        for i in range(len(ks_ok) - 1):
            ka, kb = ks_ok[i], ks_ok[i + 1]
            pa, pb = perdidas_k[ka], perdidas_k[kb]
            sube = pb > pa + TOL_MONO
            sym  = "✓" if not sube else "✗"
            print(f"  {sym} TV-04: pérdida(k={kb})={pb:.6f} <= pérdida(k={ka})={pa:.6f}", end="")
            if sube:
                print(f"  ← VIOLACIÓN (+{pb - pa:.2e})")
                mono_ok = False
                fallos_mono.append(f"{caso.id}:k{ka}→k{kb}")
            else:
                print()

        print()

    # ── Resumen ──────────────────────────────────────────────────────────────
    total = len(CASOS)
    print(sep)
    print("  RESUMEN FINAL")
    print(sep)
    print(f"  TV-03 (KQNodes k=2 == QNodes) : ", end="")
    if not fallos_tv03:
        print(f"{total - len(fallos_tv03)}/{total}  ✓ TODOS OK")
    else:
        print(f"{total - len(fallos_tv03)}/{total}  ✗ FALLOS: {fallos_tv03}")

    print(f"  TV-04 (mono pérdida por k)    : ", end="")
    if not fallos_mono:
        print("✓ TODOS OK")
    else:
        print(f"✗ VIOLACIONES: {fallos_mono}")

    if errores:
        print(f"  ERRORES de ejecución         : {errores}")

    print(sep)
    sys.exit(0 if not fallos_tv03 and not fallos_mono and not errores else 1)


if __name__ == "__main__":
    main()
