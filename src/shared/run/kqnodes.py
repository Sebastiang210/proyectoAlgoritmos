"""Corre KQNodes sobre los casos de N5.csv / N10.csv para k=2..5,
guarda resultados en CSVs diferenciados por k.

Uso:
    cd /Users/oh/World/External/Study/UC/Algorithms/2026-JSGH
    PYPHI_WELCOME_OFF=yes \
      /Users/oh/World/External/Study/UC/Algorithms/IIT-2026A/.venv/bin/python \
      src/shared/run_kqnodes.py
"""

import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import numpy as np

from src.shared.casos import CONFIGS, INPUT_DIR, OUTPUT_DIR, SAMPLES_DIR, build_subsistema, letters_to_bits
from src.strategies.QNodes.kqnodes import KQNodes


def main():
    for cfg in CONFIGS:
        tpm = np.genfromtxt(os.path.join(SAMPLES_DIR, cfg["tpm"]), delimiter=",")
        net = cfg["net"]

        for k in range(2, 6):
            print(f"\n=== {net} k={k} ===\n")

            with open(os.path.join(INPUT_DIR, cfg["input"]), newline="") as f_in, \
                 open(os.path.join(OUTPUT_DIR, f"{net}-K{k}QN.csv"), "w", newline="") as f_out:

                reader = csv.DictReader(f_in)
                w = csv.writer(f_out)
                w.writerow(["index", "loss", "time", "partition"])

                n = cfg["n"]
                for row in reader:
                    condicion_bits = letters_to_bits(row["conditions"], n)
                    alcance_bits = letters_to_bits(row["purview"], n)
                    mecanismo_bits = letters_to_bits(row["mechanism"], n)
                    estado_str = row["state"]

                    sub = build_subsistema(tpm, estado_str, condicion_bits, alcance_bits, mecanismo_bits)

                    sol = KQNodes(sub, k=k).aplicar_estrategia(
                        estado_inicial=estado_str,
                        condicion=condicion_bits,
                        alcance=alcance_bits,
                        mecanismo=mecanismo_bits,
                    )

                    w.writerow([
                        row["index"],
                        sol.perdida,
                        sol.tiempo_ejecucion,
                        sol.particion.strip().replace("\n", "\\n")
                    ])

                    print(f"[{net} #{row['index']}] k={k} loss={sol.perdida:.6f} time={sol.tiempo_ejecucion:.6f}")

            print(f"\n{net}-K{k}QN.csv written.")

    print("\n\n=== COMPARISON ===\n")
    compare_optimal_losses()


def compare_optimal_losses():
    """Compara losses para k=2..5 y reporta el óptimo para cada fila."""
    for cfg in CONFIGS:
        net = cfg["net"]
        print(f"\n--- {net} ---")

        rows_data = {}
        for k in range(2, 6):
            filepath = os.path.join(OUTPUT_DIR, f"{net}-K{k}QN.csv")
            with open(filepath, newline="") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    idx = row["index"]
                    if idx not in rows_data:
                        rows_data[idx] = {}
                    rows_data[idx][k] = float(row["loss"])

        optimal_counts = {k: 0 for k in range(2, 6)}
        for idx in sorted(rows_data.keys(), key=int):
            losses = rows_data[idx]
            min_loss = min(losses.values())
            best_ks = [k for k, v in losses.items() if abs(v - min_loss) < 1e-9]
            for k in best_ks:
                optimal_counts[k] += 1

            print(f"Row {idx}: K2={losses[2]:.4f} K3={losses[3]:.4f} K4={losses[4]:.4f} K5={losses[5]:.4f} -> best=k{best_ks}")

        print(f"Optimal distribution: {optimal_counts}")


if __name__ == "__main__":
    main()