"""Corre QNodes y Phi sobre los casos de N5.csv / N10.csv y guarda resultados.

Uso:
    cd /Users/oh/World/External/Study/UC/Algorithms/2026-JSGH
    PYPHI_WELCOME_OFF=yes \\
      /Users/oh/World/External/Study/UC/Algorithms/IIT-2026A/.venv/bin/python \\
      src/shared/run_phi_qnodes.py
"""

import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import numpy as np

from src.shared.casos import CONFIGS, INPUT_DIR, OUTPUT_DIR, SAMPLES_DIR, build_subsistema, letters_to_bits
from src.strategies.QNodes.qnodes import QNodes
from src.strategies.phi import Phi


def main():
    for cfg in CONFIGS:
        tpm = np.genfromtxt(os.path.join(SAMPLES_DIR, cfg["tpm"]), delimiter=",")
        net = cfg["net"]

        with open(os.path.join(INPUT_DIR, cfg["input"]), newline="") as f_in, \
             open(os.path.join(OUTPUT_DIR, f"{net}-PHI.csv"), "w", newline="") as f_phi, \
             open(os.path.join(OUTPUT_DIR, f"{net}-QN.csv"), "w", newline="") as f_qn:

            reader = csv.DictReader(f_in)
            w_phi = csv.writer(f_phi)
            w_phi.writerow(["index", "loss", "time", "partition"])
            w_qn = csv.writer(f_qn)
            w_qn.writerow(["index", "loss", "time", "partition"])

            n = cfg["n"]
            for row in reader:
                condicion_bits = letters_to_bits(row["conditions"], n)
                alcance_bits = letters_to_bits(row["purview"], n)
                mecanismo_bits = letters_to_bits(row["mechanism"], n)
                estado_str = row["state"]

                sub_qn = build_subsistema(tpm, estado_str, condicion_bits, alcance_bits, mecanismo_bits)
                sol_qn = QNodes(sub_qn).resolver()
                w_qn.writerow([row["index"], sol_qn.perdida, sol_qn.tiempo_ejecucion, sol_qn.particion.strip().replace("\n", "\\n")])

                sub_phi = build_subsistema(tpm, estado_str, condicion_bits, alcance_bits, mecanismo_bits)
                sol_phi = Phi(sub_phi, tpm, params=None).resolver()
                w_phi.writerow([row["index"], sol_phi.perdida, sol_phi.tiempo_ejecucion, sol_phi.particion.strip().replace("\n", "\\n")])

                diff = abs(sol_qn.perdida - sol_phi.perdida)
                tag = "OK" if diff < 1e-9 else f"DIFF={diff:.4f}"
                print(
                    f"[{net} #{row['index']}] "
                    f"qn={sol_qn.perdida:.6f}  phi={sol_phi.perdida:.6f}  {tag}"
                )


if __name__ == "__main__":
    main()
