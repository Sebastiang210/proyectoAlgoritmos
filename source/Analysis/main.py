"""
Analysis/main.py
Comparador de resultados entre GeoMIP (GeometricSIA) y QNodes.

Lee:
  - source/GeoMIP/results/resultados_Geometric.xlsx
  - source/QNodes/results/resultados_QNodes.xlsx   (o variable QNODES_OUTPUT_XLSX)
Genera:
  - source/Analysis/resultados_comparacion.csv

Columnas del CSV de salida:
  Iteración, Alcance, Mecanismo,
  Partición_GeoMIP,  Pérdida_GeoMIP,  Tiempo_GeoMIP,
  Partición_QNodes,  Pérdida_QNodes,   Tiempo_QNodes,
  Pérdida_diff,      Coinciden_particion, Dentro_tolerancia
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

TOLERANCIA_PERDIDA = 1e-4  # según convención del proyecto


def _coma_a_float(valor) -> float | None:
    """Convierte '0,1234' -> 0.1234. Devuelve None si no es parseable."""
    if valor is None or (isinstance(valor, float) and np.isnan(valor)):
        return None
    try:
        return float(str(valor).replace(",", "."))
    except ValueError:
        return None


def _normalizar_particion(particion) -> str:
    """Strip para comparación robusta."""
    if particion is None or (isinstance(particion, float) and np.isnan(particion)):
        return ""
    return str(particion).strip()


def cargar_resultados(ruta: Path, sufijo: str) -> pd.DataFrame:
    """
    Carga un xlsx de resultados y renombra columnas añadiendo sufijo.
    Columnas esperadas: Iteración, Alcance, Mecanismo, Partición, Pérdida, Tiempo de ejecución (s)
    """
    df = pd.read_excel(ruta)
    rename = {
        "Partición":               f"Partición_{sufijo}",
        "Pérdida":                 f"Pérdida_{sufijo}",
        "Tiempo de ejecución (s)": f"Tiempo_{sufijo}",
    }
    return df.rename(columns=rename)


def generar_comparacion(
    ruta_geo: Path,
    ruta_qn: Path,
    ruta_salida: Path,
) -> pd.DataFrame:
    """
    Lee ambos xlsx, los une por (Iteración, Alcance, Mecanismo) y calcula métricas.
    Guarda el resultado en ruta_salida como CSV.
    """
    df_geo = cargar_resultados(ruta_geo, "GeoMIP")
    df_qn  = cargar_resultados(ruta_qn,  "QNodes")

    df = pd.merge(
        df_geo,
        df_qn[["Iteración", "Alcance", "Mecanismo",
               "Partición_QNodes", "Pérdida_QNodes", "Tiempo_QNodes"]],
        on=["Iteración", "Alcance", "Mecanismo"],
        how="outer",
    )

    df["_perdida_geo"] = df["Pérdida_GeoMIP"].apply(_coma_a_float)
    df["_perdida_qn"]  = df["Pérdida_QNodes"].apply(_coma_a_float)

    df["Pérdida_diff"] = df.apply(
        lambda r: abs(r["_perdida_geo"] - r["_perdida_qn"])
        if r["_perdida_geo"] is not None and r["_perdida_qn"] is not None
        else None,
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

    cols_salida = [
        "Iteración", "Alcance", "Mecanismo",
        "Partición_GeoMIP", "Pérdida_GeoMIP", "Tiempo_GeoMIP",
        "Partición_QNodes", "Pérdida_QNodes",  "Tiempo_QNodes",
        "Pérdida_diff", "Coinciden_particion", "Dentro_tolerancia",
    ]
    df_salida = df[cols_salida]

    ruta_salida.parent.mkdir(parents=True, exist_ok=True)
    df_salida.to_csv(ruta_salida, index=False, encoding="utf-8-sig")
    print(f"Comparación guardada en {ruta_salida}")

    total     = len(df_salida)
    coinciden = int(df_salida["Coinciden_particion"].sum())
    dentro    = int(df_salida["Dentro_tolerancia"].sum())
    print(f"  Filas totales        : {total}")
    print(f"  Partición idéntica   : {coinciden}/{total} ({100*coinciden/total:.1f}%)")
    print(f"  Dentro de tolerancia : {dentro}/{total} ({100*dentro/total:.1f}%)")

    return df_salida


def main() -> None:
    ruta_geo = Path(
        os.getenv(
            "GEOMIP_OUTPUT_XLSX",
            str(GEOMIP_ROOT / "results" / "resultados_Geometric.xlsx"),
        )
    )
    ruta_qn = Path(
        os.getenv(
            "QNODES_OUTPUT_XLSX",
            str(QNODES_ROOT / "results" / "resultados_QNodes.xlsx"),
        )
    )
    ruta_salida = Path(
        os.getenv(
            "ANALYSIS_OUTPUT_CSV",
            str(ANALYSIS_ROOT / "resultados_comparacion.csv"),
        )
    )

    if not ruta_geo.exists():
        print(f"[ERROR] No se encontró el xlsx de GeoMIP: {ruta_geo}")
        return
    if not ruta_qn.exists():
        print(f"[ERROR] No se encontró el xlsx de QNodes: {ruta_qn}")
        print("  Ejecuta primero QNodes en modo batch:")
        print("  cd source\\QNodes && uv run exec.py --excel")
        return

    generar_comparacion(ruta_geo, ruta_qn, ruta_salida)


if __name__ == "__main__":
    main()
