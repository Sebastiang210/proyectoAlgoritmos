"""
Analysis/main.py
================
Dos modos de análisis comparativo:

1. generar_comparacion()       — GeoMIP vs QNodes (bipartición original, xlsx)
2. generar_comparacion_k()     — GeoMIP/KGeoMIP vs QNodes/KQNodes (k=2,k=3, N=8, CSV)

Lee (modo k):
  - source/GeoMIP/results/resultados_kgeomip_n8.csv
  - source/QNodes/results/resultados_kqnodes_n8.csv

Escribe (modo k):
  - source/Analysis/resultados_k_comparacion.csv

Columnas del CSV de salida (modo k)
------------------------------------
caso_id, descripcion, alcance, mecanismo,
geo_perdida, geo_tiempo,
kgeo_k2_perdida, kgeo_k2_tiempo,
kgeo_k3_perdida, kgeo_k3_tiempo,
q_perdida, q_tiempo,
kq_k2_perdida, kq_k2_tiempo,
kq_k3_perdida, kq_k3_tiempo,
mejora_geo_k3_vs_k2,   # geo_k2 - geo_k3  (> 0 = mejora)
mejora_q_k3_vs_k2,     # q_k2  - q_k3
diff_geo_vs_q_base,    # |geo - q| baseline
diff_geo_vs_q_k2,      # |kgeo_k2 - kq_k2|
diff_geo_vs_q_k3,      # |kgeo_k3 - kq_k3|
tv03_geo_ok,           # |kgeo_k2 - geo| < 1e-6
tv03_q_ok,             # |kq_k2  - q|   < 1e-6
tv04_geo_ok,           # kgeo_k3 <= kgeo_k2
tv04_q_ok              # kq_k3  <= kq_k2
"""

import os
from pathlib import Path

import numpy as np
import pandas as pd

# ── Rutas ────────────────────────────────────────────────────────────────────
ANALYSIS_ROOT = Path(__file__).resolve().parent
SOURCE_ROOT   = ANALYSIS_ROOT.parent
GEOMIP_ROOT   = SOURCE_ROOT / "GeoMIP"
QNODES_ROOT   = SOURCE_ROOT / "QNodes"

TOLERANCIA_PERDIDA = 3e-3
TOL_TV03 = 1e-6
TOL_TV04 = 1e-6


# ══════════════════════════════════════════════════════════════════════════════
# MODO 1 — Comparación original GeoMIP vs QNodes (xlsx → csv)
# ══════════════════════════════════════════════════════════════════════════════

def _coma_a_float(valor) -> float | None:
    if valor is None or (isinstance(valor, float) and np.isnan(valor)):
        return None
    try:
        return float(str(valor).replace(",", "."))
    except ValueError:
        return None


def _normalizar_particion(particion) -> str:
    if particion is None or (isinstance(particion, float) and np.isnan(particion)):
        return ""
    return str(particion).strip()


def cargar_resultados(ruta: Path, sufijo: str) -> pd.DataFrame:
    df = pd.read_excel(ruta)
    rename = {
        "Partición":               f"Partición_{sufijo}",
        "Pérdida":                 f"Pérdida_{sufijo}",
        "Tiempo de ejecución (s)": f"Tiempo_{sufijo}",
    }
    return df.rename(columns=rename)


def generar_comparacion(ruta_geo: Path, ruta_qn: Path, ruta_salida: Path) -> pd.DataFrame:
    """GeoMIP vs QNodes desde xlsx, produce resultados_comparacion.csv."""
    df_geo = cargar_resultados(ruta_geo, "GeoMIP")
    df_qn  = cargar_resultados(ruta_qn,  "QNodes")

    df = pd.merge(
        df_geo,
        df_qn[["Iteración", "Alcance", "Mecanismo",
               "Partición_QNodes", "Pérdida_QNodes", "Tiempo_QNodes"]],
        on=["Iteración"],
        how="outer",
    )

    df["_pg"] = df["Pérdida_GeoMIP"].apply(_coma_a_float)
    df["_pq"] = df["Pérdida_QNodes"].apply(_coma_a_float)

    df["Pérdida_diff"] = df.apply(
        lambda r: abs(r["_pg"] - r["_pq"])
        if r["_pg"] is not None and r["_pq"] is not None else None,
        axis=1,
    )
    df["Coinciden_particion"] = df.apply(
        lambda r: (
            _normalizar_particion(r["Partición_GeoMIP"])
            == _normalizar_particion(r["Partición_QNodes"])
        ),
        axis=1,
    )
    df["Dentro_tolerancia"] = df["Pérdida_diff"].apply(
        lambda d: (d <= TOLERANCIA_PERDIDA) if d is not None else None
    )

    cols = [
        "Iteración",
        "Partición_GeoMIP", "Pérdida_GeoMIP", "Tiempo_GeoMIP",
        "Partición_QNodes", "Pérdida_QNodes",  "Tiempo_QNodes",
        "Pérdida_diff", "Coinciden_particion", "Dentro_tolerancia",
    ]
    df_salida = df[cols]
    ruta_salida.parent.mkdir(parents=True, exist_ok=True)
    df_salida.to_csv(ruta_salida, index=False, encoding="utf-8-sig")

    total     = len(df_salida)
    coinciden = int(df_salida["Coinciden_particion"].sum())
    dentro    = int(df_salida["Dentro_tolerancia"].sum())
    print(f"[Modo 1] Guardado en {ruta_salida}")
    print(f"  Filas            : {total}")
    print(f"  Partición igual  : {coinciden}/{total} ({100*coinciden/total:.1f}%)")
    print(f"  Dentro tolerancia: {dentro}/{total} ({100*dentro/total:.1f}%)")
    return df_salida


# ══════════════════════════════════════════════════════════════════════════════
# MODO 2 — Comparación k-particiones N=8 (csv → csv)
# ══════════════════════════════════════════════════════════════════════════════

def _safe(val) -> float | None:
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def _diff(a, b) -> float | None:
    a, b = _safe(a), _safe(b)
    return abs(a - b) if a is not None and b is not None else None


def _mejora(base, nuevo) -> float | None:
    b, n = _safe(base), _safe(nuevo)
    return round(b - n, 8) if b is not None and n is not None else None


def _tv03(base, k2) -> bool | None:
    b, k = _safe(base), _safe(k2)
    return abs(b - k) < TOL_TV03 if b is not None and k is not None else None


def _tv04(k2, k3) -> bool | None:
    a, b = _safe(k2), _safe(k3)
    return (b <= a + TOL_TV04) if a is not None and b is not None else None


def generar_comparacion_k(
    ruta_geo_csv: Path,
    ruta_q_csv: Path,
    ruta_salida: Path,
) -> pd.DataFrame:
    """
    Une los CSVs de KGeoMIP y KQNodes (N=8, k∈{2,3}), calcula métricas
    de validación y escribe resultados_k_comparacion.csv.
    """
    df_geo = pd.read_csv(ruta_geo_csv)
    df_q   = pd.read_csv(ruta_q_csv)

    df = pd.merge(df_geo, df_q, on=["caso_id", "descripcion", "alcance", "mecanismo"])

    # Métricas derivadas
    df["mejora_geo_k3_vs_k2"] = df.apply(
        lambda r: _mejora(r.get("kgeo_k2_perdida"), r.get("kgeo_k3_perdida")), axis=1
    )
    df["mejora_q_k3_vs_k2"] = df.apply(
        lambda r: _mejora(r.get("kq_k2_perdida"), r.get("kq_k3_perdida")), axis=1
    )
    df["diff_geo_vs_q_base"] = df.apply(
        lambda r: _diff(r.get("geo_perdida"), r.get("q_perdida")), axis=1
    )
    df["diff_geo_vs_q_k2"] = df.apply(
        lambda r: _diff(r.get("kgeo_k2_perdida"), r.get("kq_k2_perdida")), axis=1
    )
    df["diff_geo_vs_q_k3"] = df.apply(
        lambda r: _diff(r.get("kgeo_k3_perdida"), r.get("kq_k3_perdida")), axis=1
    )

    # Validaciones
    df["tv03_geo_ok"] = df.apply(
        lambda r: _tv03(r.get("geo_perdida"), r.get("kgeo_k2_perdida")), axis=1
    )
    df["tv03_q_ok"] = df.apply(
        lambda r: _tv03(r.get("q_perdida"), r.get("kq_k2_perdida")), axis=1
    )
    df["tv04_geo_ok"] = df.apply(
        lambda r: _tv04(r.get("kgeo_k2_perdida"), r.get("kgeo_k3_perdida")), axis=1
    )
    df["tv04_q_ok"] = df.apply(
        lambda r: _tv04(r.get("kq_k2_perdida"), r.get("kq_k3_perdida")), axis=1
    )

    cols = [
        "caso_id", "descripcion", "alcance", "mecanismo",
        "geo_perdida",      "geo_tiempo",
        "kgeo_k2_perdida",  "kgeo_k2_tiempo",
        "kgeo_k3_perdida",  "kgeo_k3_tiempo",
        "q_perdida",        "q_tiempo",
        "kq_k2_perdida",    "kq_k2_tiempo",
        "kq_k3_perdida",    "kq_k3_tiempo",
        "mejora_geo_k3_vs_k2", "mejora_q_k3_vs_k2",
        "diff_geo_vs_q_base",  "diff_geo_vs_q_k2",  "diff_geo_vs_q_k3",
        "tv03_geo_ok", "tv03_q_ok",
        "tv04_geo_ok", "tv04_q_ok",
    ]
    df_salida = df[[c for c in cols if c in df.columns]]

    ruta_salida.parent.mkdir(parents=True, exist_ok=True)
    df_salida.to_csv(ruta_salida, index=False, encoding="utf-8-sig")

    total       = len(df_salida)
    tv03_geo_ok = df_salida["tv03_geo_ok"].sum() if "tv03_geo_ok" in df_salida else 0
    tv03_q_ok   = df_salida["tv03_q_ok"].sum()   if "tv03_q_ok"  in df_salida else 0
    tv04_geo_ok = df_salida["tv04_geo_ok"].sum()  if "tv04_geo_ok" in df_salida else 0
    tv04_q_ok   = df_salida["tv04_q_ok"].sum()   if "tv04_q_ok"  in df_salida else 0

    print(f"\n[Modo 2] Guardado en {ruta_salida}")
    print(f"  Casos            : {total}")
    print(f"  TV-03 geo OK     : {tv03_geo_ok}/{total}")
    print(f"  TV-03 q   OK     : {tv03_q_ok}/{total}")
    print(f"  TV-04 geo OK     : {tv04_geo_ok}/{total}")
    print(f"  TV-04 q   OK     : {tv04_q_ok}/{total}")

    return df_salida


# ══════════════════════════════════════════════════════════════════════════════
# ENTRYPOINT
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys

    modo = sys.argv[1] if len(sys.argv) > 1 else "k"

    if modo == "1" or modo == "base":
        # ── Modo 1: GeoMIP vs QNodes desde xlsx ──────────────────────────────
        ruta_geo = SOURCE_ROOT / "GeoMIP" / "results" / "resultados_Geometric.xlsx"
        ruta_qn  = SOURCE_ROOT / "QNodes" / "results" / "resultados_QNodes.xlsx"
        ruta_sal = ANALYSIS_ROOT / "resultados_comparacion.csv"
        generar_comparacion(ruta_geo, ruta_qn, ruta_sal)

    else:
        # ── Modo 2 (por defecto): k-particiones N=8, csv → csv ───────────────
        ruta_geo_csv = SOURCE_ROOT / "GeoMIP" / "results" / "resultados_kgeomip_n8.csv"
        ruta_q_csv   = SOURCE_ROOT / "QNodes" / "results"  / "resultados_kqnodes_n8.csv"
        ruta_sal     = ANALYSIS_ROOT / "resultados_k_comparacion.csv"

        missing = [r for r in [ruta_geo_csv, ruta_q_csv] if not r.exists()]
        if missing:
            print("[ERROR] Faltan los siguientes CSVs de entrada:")
            for m in missing:
                print(f"  {m}")
            print("\nEjecuta primero:")
            print("  cd source\\GeoMIP\\src\\Method2_Dynamic_Programming_Reformulation")
            print("  uv run python run_kgeomip_batch.py")
            print("  cd ..\\..\\..\\..\\QNodes")
            print("  uv run python run_kqnodes_batch.py")
            sys.exit(1)

        generar_comparacion_k(ruta_geo_csv, ruta_q_csv, ruta_sal)
        print(f"\n  → Abre: {ruta_sal}")
