
"""
Run benchmarks and save results to CSV.

Usage:
    uv run python src/shared/run_benchmark.py
    uv run python src/shared/run_benchmark.py --networks N5B N10A
"""

import argparse
import csv
import time
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.models.base.application import aplicacion
aplicacion.pagina_sample_network = "A"

from src.shared.casos import INPUT_DIR, OUTPUT_DIR, SAMPLES_DIR, build_subsistema, letters_to_bits
from src.strategies.GeoMIP.geomip import GeoMIP
from src.strategies.GeoMIP.kgeomip import KGeoMIP
from src.strategies.QNodes.qnodes import QNodes
from src.strategies.QNodes.kqnodes import KQNodes

NETWORK_CONFIGS = {
    "N5B": {"n": 5, "tpm": "N5B.csv"},
    "N5A": {"n": 5, "tpm": "N5A.csv"},
    "N10A": {"n": 10, "tpm": "N10A.csv"},
    "N10B": {"n": 10, "tpm": "N10B.csv"},
    "N15A": {"n": 15, "tpm": "N15A.csv"},
    "N15B": {"n": 15, "tpm": "N15B.csv"},
    "N20A": {"n": 20, "tpm": "N20A.csv"},
    "N21A": {"n": 21, "tpm": "N21A.csv"},
    "N22A": {"n": 22, "tpm": "N22A.csv"},
    "N23A": {"n": 23, "tpm": "N23A.csv"},
}


def run_benchmark(network: str, n: int, tpm_file: str) -> None:
    """Run all strategies and save to CSV."""
    network_dir = f"{OUTPUT_DIR}/{network}"
    expected_files = {
        "GeoMIP", "K2GeoMIP", "K3GeoMIP", "K4GeoMIP", "K5GeoMIP",
        "QNodes", "K2QNodes", "K3QNodes", "K4QNodes", "K5QNodes"
    }
    existing = set()
    if os.path.isdir(network_dir):
        existing = {f.replace(".csv", "") for f in os.listdir(network_dir) if f.endswith(".csv")}
    missing = expected_files - existing
    if not missing:
        print(f"\n{network} benchmarks already complete, skipping.")
        return
    elif existing:
        print(f"\n{network}: missing {missing}, re-running...")

    tpm = np.genfromtxt(f"{SAMPLES_DIR}/{tpm_file}", delimiter=',')

    results = {
        "GeoMIP": [],
        "K2GeoMIP": [],
        "K3GeoMIP": [],
        "K4GeoMIP": [],
        "K5GeoMIP": [],
        "QNodes": [],
        "K2QNodes": [],
        "K3QNodes": [],
        "K4QNodes": [],
        "K5QNodes": [],
    }

    with open(f"{INPUT_DIR}/N{n}.csv", newline="") as f_in:
        reader = csv.DictReader(f_in)
        rows = list(reader)

    print(f"\nRunning {network} benchmarks ({len(rows)} cases)...")

    for row in rows:
        condicion_bits = letters_to_bits(row["conditions"], n)
        alcance_bits = letters_to_bits(row["purview"], n)
        mecanismo_bits = letters_to_bits(row["mechanism"], n)
        estado_str = row["state"]
        idx = row["index"]

        sub = build_subsistema(tpm, estado_str, condicion_bits, alcance_bits, mecanismo_bits)

        # GeoMIP
        t0 = time.perf_counter()
        geo = GeoMIP(sub)
        geo_result = geo.resolver()
        geo_time = time.perf_counter() - t0
        results["GeoMIP"].append({"index": idx, "loss": float(geo_result.perdida), "time": geo_time})

        # KGeoMIP k=2..5
        for k in [2, 3, 4, 5]:
            t0 = time.perf_counter()
            kgeo = KGeoMIP(sub, k=k)
            kgeo_result = kgeo.ejecutar_k(k)
            kgeo_time = time.perf_counter() - t0
            results[f"K{k}GeoMIP"].append({"index": idx, "loss": float(kgeo_result.perdida), "time": kgeo_time})

        # QNodes
        t0 = time.perf_counter()
        qn = QNodes(sub)
        qn_result = qn.resolver()
        qn_time = time.perf_counter() - t0
        results["QNodes"].append({"index": idx, "loss": float(qn_result.perdida), "time": qn_time})

        # KQNodes k=2..5
        for k in [2, 3, 4, 5]:
            t0 = time.perf_counter()
            kqn = KQNodes(sub, k=k)
            try:
                kqn_result = kqn.resolver()
                kqn_loss = float(kqn_result.perdida)
            except Exception as e:
                print(f"    K{k}QNodes error: {e}")
                kqn_loss = -1.0  # indicates error
            kqn_time = time.perf_counter() - t0
            results[f"K{k}QNodes"].append({"index": idx, "loss": kqn_loss, "time": kqn_time})

        print(f"  Case {idx}: GeoMIP={geo_time:.4f}s, QNodes={qn_time:.4f}s")

    # Save to CSV
    os.makedirs(network_dir, exist_ok=True)
    for name, data in results.items():
        filepath = f"{network_dir}/{name}.csv"
        with open(filepath, "w", newline="") as f_out:
            writer = csv.writer(f_out)
            writer.writerow(["index", "loss", "time", "partition"])
            for d in data:
                writer.writerow([d["index"], d["loss"], d["time"], ""])
        print(f"  Saved {filepath}")


def main():
    parser = argparse.ArgumentParser(description="Run benchmarks")
    parser.add_argument("--networks", nargs="+", default=list(NETWORK_CONFIGS.keys()),
                        help="Networks to benchmark (default: all)")

    args = parser.parse_args()

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    for network in args.networks:
        if network not in NETWORK_CONFIGS:
            print(f"Warning: {network} not configured, skipping")
            continue
        cfg = NETWORK_CONFIGS[network]
        run_benchmark(network, cfg["n"], cfg["tpm"])

    print("\nAll benchmarks complete!")


if __name__ == "__main__":
    main()
