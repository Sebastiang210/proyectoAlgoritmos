"""Corre KGeoMIP y GeometricSIA sobre los casos de N5.csv / N10.csv,
guarda resultados en CSVs.

Uso:
    cd /Users/oh/World/External/Study/UC/Algorithms/2026-JSGH
    uv run python src/shared/run_kgeomip.py
"""

import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import numpy as np

from src.shared.casos import CONFIGS, INPUT_DIR, OUTPUT_DIR, SAMPLES_DIR, build_subsistema, letters_to_bits
from strategies.GeoMIP.geomip import GeoMIP
from src.strategies.GeoMIP.kgeomip import KGeoMIP


def run_geo(sub, estado_str, condicion_bits, alcance_bits, mecanismo_bits):
    geo = GeoMIP(sub)
    if geo.tpm is not None:
        geo.sia_preparar_subsistema(estado_str, condicion_bits, alcance_bits, mecanismo_bits)
    return geo.resolver()


def run_kgeo(sub, estado_str, condicion_bits, alcance_bits, mecanismo_bits, k):
    kgeo = KGeoMIP(sub, k=k)
    return kgeo.ejecutar_k(k)


def main():
    for cfg in CONFIGS:
        tpm = np.genfromtxt(os.path.join(SAMPLES_DIR, cfg["tpm"]), delimiter=",")
        net = cfg["net"]

        print(f"\n=== {net} ===\n")

        with open(os.path.join(INPUT_DIR, cfg["input"]), newline="") as f_in:
            reader = csv.DictReader(f_in)
            rows = list(reader)

        n = cfg["n"]

        geo_results = []
        kgeo_results = {k: [] for k in range(2, 6)}

        for row in rows:
            condicion_bits = letters_to_bits(row["conditions"], n)
            alcance_bits = letters_to_bits(row["purview"], n)
            mecanismo_bits = letters_to_bits(row["mechanism"], n)
            estado_str = row["state"]

            sub = build_subsistema(tpm, estado_str, condicion_bits, alcance_bits, mecanismo_bits)

            geo_sol = run_geo(sub, estado_str, condicion_bits, alcance_bits, mecanismo_bits)
            geo_results.append({
                "index": row["index"],
                "loss": geo_sol.perdida,
                "time": geo_sol.tiempo_ejecucion,
                "partition": geo_sol.particion.strip().replace("\n", "\\n")
            })
            print(f"[{net} #{row['index']}] GEO loss={geo_sol.perdida:.6f}")

            for k in range(2, 6):
                kgeo_sol = run_kgeo(sub, estado_str, condicion_bits, alcance_bits, mecanismo_bits, k)
                kgeo_results[k].append({
                    "index": row["index"],
                    "loss": kgeo_sol.perdida,
                    "time": kgeo_sol.tiempo_ejecucion,
                    "partition": kgeo_sol.particion.strip().replace("\n", "\\n")
                })
                print(f"[{net} #{row['index']}] KGeoMIP(k={k}) loss={kgeo_sol.perdida:.6f}")

        with open(os.path.join(OUTPUT_DIR, f"{net}-GEO.csv"), "w", newline="") as f_out:
            w = csv.writer(f_out)
            w.writerow(["index", "loss", "time", "partition"])
            for r in geo_results:
                w.writerow([r["index"], r["loss"], r["time"], r["partition"]])
        print(f"\n{net}-GEO.csv written.")

        for k in range(2, 6):
            with open(os.path.join(OUTPUT_DIR, f"{net}-K{k}GEO.csv"), "w", newline="") as f_out:
                w = csv.writer(f_out)
                w.writerow(["index", "loss", "time", "partition"])
                for r in kgeo_results[k]:
                    w.writerow([r["index"], r["loss"], r["time"], r["partition"]])
            print(f"{net}-K{k}GEO.csv written.")

    print("\n\n=== TV-02 VERIFICATION (k=2 exactness) ===\n")
    verify_tv02()


def verify_tv02():
    """Verifica que KGeoMIP(k=2) == GeometricSIA para todos los casos."""
    for cfg in CONFIGS:
        net = cfg["net"]
        geo_path = os.path.join(OUTPUT_DIR, f"{net}-GEO.csv")
        kgeo_path = os.path.join(OUTPUT_DIR, f"{net}-K2GEO.csv")

        with open(geo_path, newline="") as f:
            geo_rows = {row["index"]: float(row["loss"]) for row in csv.DictReader(f)}
        with open(kgeo_path, newline="") as f:
            kgeo_rows = {row["index"]: float(row["loss"]) for row in csv.DictReader(f)}

        max_diff = 0.0
        fallos = []
        for idx in geo_rows:
            diff = abs(geo_rows[idx] - kgeo_rows[idx])
            if diff > max_diff:
                max_diff = diff
            if diff > 1e-6:
                fallos.append((idx, geo_rows[idx], kgeo_rows[idx]))

        print(f"{net}: max_diff={max_diff:.2e} {'✓' if not fallos else '✗ FALLOS: ' + str(fallos)}")


if __name__ == "__main__":
    main()