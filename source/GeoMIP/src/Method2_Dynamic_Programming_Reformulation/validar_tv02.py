"""
Validación TV-02 expandida: KGeoMIP(k=2) debe coincidir con GeometricSIA.

Fuente de verdad
----------------
- Casos N=3 : hoja "3 elementos" de Pruebas_Metodo2.xlsx  (pérdida PyPhi = ground truth)
- Casos N=4 : N4A.csv  (sin PyPhi; sólo se verifica geo == kgeo)
- Casos N=5 : N5A.csv  (sin PyPhi; sólo se verifica geo == kgeo)
- Casos N=6 : N6A.csv  (sin PyPhi; sólo se verifica geo == kgeo)
- Casos N=8 : N8A.csv  (sin PyPhi; sólo se verifica geo == kgeo)

Criterios
---------
- TV-02 : |perdida_geo - perdida_kgeo| < 1e-6
- TV-01* : |perdida_geo - perdida_pyphi| < 1e-4  (sólo cuando hay verdad PyPhi)

Nodos máximos probados: 8  (conforme a la metodología del proyecto)
"""
from __future__ import annotations

import sys
import os
from dataclasses import dataclass

# ── Setup de aplicación (SIEMPRE antes de importar estrategias) ──────────────
from src.models.base.application import aplicacion

aplicacion.pagina_sample_network = "A"

import numpy as np

from src.controllers.manager import Manager
from src.controllers.strategies.geometric import GeometricSIA
from src.controllers.strategies.kgeomip import KGeoMIP

# ── Constantes de tolerancia ─────────────────────────────────────────────────
TOL_TV02 = 1e-6   # geo vs kgeo
TOL_TV01 = 1e-4   # geo vs pyphi (cuando aplica)


# ── Definición de casos de prueba ────────────────────────────────────────────
@dataclass
class Caso:
    id: str
    descripcion: str      # notación subsistema "AB_{t+1}|BC_{t}"
    estado: str           # estado inicial (longitud = N nodos)
    condicion: str        # bits: 0 = condicionar
    alcance: str          # bits: 0 = excluir futuro
    mecanismo: str        # bits: 0 = excluir presente
    pyphi_loss: float | None = None  # None si no hay verdad PyPhi


# ─────────────────────────────────────────────────────────────────────────────
# N = 3  (N3A.csv, estado_inicial="100")
# Fuente: hoja "3 elementos" Pruebas_Metodo2.xlsx, columnas PyPhi y GeoMIP
# ─────────────────────────────────────────────────────────────────────────────
CASOS_N3 = [
    Caso("N3-01", "ABC_{t+1}|ABC_{t}", "100", "111", "111", "111", pyphi_loss=0.25),
    Caso("N3-02", "ABC_{t+1}|AB_{t}",  "100", "111", "111", "110", pyphi_loss=0.25),
    Caso("N3-03", "ABC_{t+1}|BC_{t}",  "100", "111", "111", "011", pyphi_loss=0.0),
    Caso("N3-04", "ABC_{t+1}|B_{t}",   "100", "111", "111", "010", pyphi_loss=0.0),
    Caso("N3-05", "AB_{t+1}|BC_{t}",   "100", "111", "110", "011", pyphi_loss=0.25),
    Caso("N3-06", "BC_{t+1}|AB_{t}",   "100", "111", "011", "110", pyphi_loss=0.25),
]

# ─────────────────────────────────────────────────────────────────────────────
# N = 4  (N4A.csv, estado_inicial="1000")
# Sin verdad PyPhi; sólo se verifica TV-02 geo == kgeo
# ─────────────────────────────────────────────────────────────────────────────
CASOS_N4 = [
    Caso("N4-01", "ABCD_{t+1}|ABCD_{t}", "1000", "1111", "1111", "1111"),
    Caso("N4-02", "ABC_{t+1}|ABC_{t}",   "1000", "1110", "1110", "1110"),
    Caso("N4-03", "AC_{t+1}|AC_{t}",     "1000", "1111", "1010", "1010"),
    Caso("N4-04", "BCD_{t+1}|BCD_{t}",   "1000", "0111", "0111", "0111"),
    Caso("N4-05", "AB_{t+1}|CD_{t}",     "1000", "1111", "1100", "0011"),
]

# ─────────────────────────────────────────────────────────────────────────────
# N = 5  (N5A.csv, estado_inicial="10000")
# ─────────────────────────────────────────────────────────────────────────────
CASOS_N5 = [
    Caso("N5-01", "ABCDE_{t+1}|ABCDE_{t}", "10000", "11111", "11111", "11111"),
    Caso("N5-02", "ABCD_{t+1}|ABCD_{t}",   "10000", "11110", "11110", "11110"),
    Caso("N5-03", "ACE_{t+1}|ACE_{t}",     "10000", "11111", "10101", "10101"),
]

# ─────────────────────────────────────────────────────────────────────────────
# N = 6  (N6A.csv, estado_inicial="100000")
# ─────────────────────────────────────────────────────────────────────────────
CASOS_N6 = [
    Caso("N6-01", "ABCDEF_{t+1}|ABCDEF_{t}", "100000", "111111", "111111", "111111"),
    Caso("N6-02", "ABCD_{t+1}|ABCD_{t}",     "100000", "111111", "111100", "111100"),
    Caso("N6-03", "ACE_{t+1}|BDF_{t}",       "100000", "111111", "101010", "010101"),
]

# ─────────────────────────────────────────────────────────────────────────────
# N = 8  (N8A.csv, estado_inicial="10000000")
# ─────────────────────────────────────────────────────────────────────────────
CASOS_N8 = [
    Caso("N8-01", "ABCD_{t+1}|ABCD_{t}",         "10000000", "11111111", "11110000", "11110000"),
    Caso("N8-02", "ABCDEFGH_{t+1}|ABCDEFGH_{t}", "10000000", "11111111", "11111111", "11111111"),
]

TODOS_LOS_CASOS = CASOS_N3 + CASOS_N4 + CASOS_N5 + CASOS_N6 + CASOS_N8


# ── Función de ejecución de un caso ─────────────────────────────────────────
def ejecutar_caso(caso: Caso) -> dict:
    """
    Ejecuta GeometricSIA y KGeoMIP(k=2) para un caso dado.
    Retorna un dict con todos los resultados y flags de validación.
    """
    try:
        tpm = np.genfromtxt(
            str(Manager(caso.estado).tpm_filename), delimiter=","
        )

        geo  = GeometricSIA(Manager(caso.estado)).aplicar_estrategia(
            caso.condicion, caso.alcance, caso.mecanismo, tpm
        )
        kgeo = KGeoMIP(Manager(caso.estado), k=2).aplicar_estrategia(
            caso.condicion, caso.alcance, caso.mecanismo, tpm
        )

        g_loss  = float(geo.perdida)
        kg_loss = float(kgeo.perdida)
        diff_tv02 = abs(g_loss - kg_loss)
        tv02_ok   = diff_tv02 < TOL_TV02

        # TV-01* sólo si hay verdad PyPhi
        tv01_ok = None
        diff_tv01 = None
        if caso.pyphi_loss is not None:
            diff_tv01 = abs(g_loss - caso.pyphi_loss)
            tv01_ok   = diff_tv01 < TOL_TV01

        return {
            "id": caso.id,
            "desc": caso.descripcion,
            "n": len(caso.estado),
            "geo_loss": g_loss,
            "kgeo_loss": kg_loss,
            "pyphi_loss": caso.pyphi_loss,
            "diff_tv02": diff_tv02,
            "tv02_ok": tv02_ok,
            "diff_tv01": diff_tv01,
            "tv01_ok": tv01_ok,
            "error": None,
        }

    except Exception as exc:
        return {
            "id": caso.id,
            "desc": caso.descripcion,
            "n": len(caso.estado),
            "error": str(exc),
            "tv02_ok": False,
            "tv01_ok": None,
        }


# ── Runner principal ─────────────────────────────────────────────────────────
def main():
    sep = "=" * 72
    print(sep)
    print("  TV-02 EXPANDIDO: KGeoMIP(k=2) == GeometricSIA  |  multi-caso")
    print(f"  Tolerancia TV-02 = {TOL_TV02:.0e}   Tolerancia TV-01* = {TOL_TV01:.0e}")
    print(sep)

    resultados = []
    fallos_tv02 = []
    fallos_tv01 = []

    for caso in TODOS_LOS_CASOS:
        n_tag = f"N={len(caso.estado)}"
        print(f"\n  [{caso.id}] {caso.descripcion:<30}  ({n_tag})")
        r = ejecutar_caso(caso)
        resultados.append(r)

        if r["error"]:
            print(f"    ❌ ERROR: {r['error']}")
            fallos_tv02.append(caso.id)
            continue

        tv02_sym = "✓" if r["tv02_ok"] else "✗"
        print(f"    GeoMIP  : {r['geo_loss']:.8f}")
        print(f"    KGeoMIP : {r['kgeo_loss']:.8f}")
        print(f"    Δ TV-02 : {r['diff_tv02']:.2e}  [{tv02_sym} TV-02]")

        if not r["tv02_ok"]:
            fallos_tv02.append(caso.id)

        if r["pyphi_loss"] is not None:
            tv01_sym = "✓" if r["tv01_ok"] else "✗"
            print(f"    PyPhi   : {r['pyphi_loss']:.8f}")
            print(f"    Δ TV-01*: {r['diff_tv01']:.2e}  [{tv01_sym} TV-01*]")
            if not r["tv01_ok"]:
                fallos_tv01.append(caso.id)

    # ── Resumen ──────────────────────────────────────────────────────────────
    total = len(TODOS_LOS_CASOS)
    ok_tv02 = total - len(fallos_tv02)
    print(f"\n{sep}")
    print(f"  RESUMEN")
    print(f"{sep}")
    print(f"  TV-02  (geo == kgeo)  : {ok_tv02}/{total} OK", end="")
    print("  ✓ TODOS" if not fallos_tv02 else f"  ✗ FALLOS: {fallos_tv02}")

    n3_con_pyphi = [c for c in CASOS_N3 if c.pyphi_loss is not None]
    ok_tv01 = len(n3_con_pyphi) - len(fallos_tv01)
    print(f"  TV-01* (geo ~ pyphi)  : {ok_tv01}/{len(n3_con_pyphi)} OK", end="")
    print("  ✓ TODOS" if not fallos_tv01 else f"  ✗ FALLOS: {fallos_tv01}")
    print(sep)

    sys.exit(0 if not fallos_tv02 else 1)


if __name__ == "__main__":
    main()
