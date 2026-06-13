"""Corre QNodes y GeometricSIA sobre los casos de N5.csv / N10.csv, guarda
resultados y compara phi de Geometric contra QNodes (fuente de verdad).

Uso:
    cd /Users/oh/World/External/Study/UC/Algorithms/2026-JSGH
    PYPHI_WELCOME_OFF=yes \\
      /Users/oh/World/External/Study/UC/Algorithms/IIT-2026A/.venv/bin/python \\
      src/shared/run_geo_qnodes.py
"""

import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import numpy as np

from src.shared.casos import CONFIGS, INPUT_DIR, OUTPUT_DIR, SAMPLES_DIR, build_subsistema, letters_to_bits
from strategies.GeoMIP.geomip import GeoMIP
from src.strategies.QNodes.qnodes import QNodes


def main():
    total_ok = 0
    total_diff = 0

    for cfg in CONFIGS:
        tpm = np.genfromtxt(os.path.join(SAMPLES_DIR, cfg["tpm"]), delimiter=",")
        net = cfg["net"]
        ok = 0
        diff_count = 0

        with open(os.path.join(INPUT_DIR, cfg["input"]), newline="") as f_in, \
             open(os.path.join(OUTPUT_DIR, f"{net}-QN.csv"), "w", newline="") as f_qn, \
             open(os.path.join(OUTPUT_DIR, f"{net}-GEO.csv"), "w", newline="") as f_geo:

            reader = csv.DictReader(f_in)
            w_qn = csv.writer(f_qn)
            w_qn.writerow(["index", "loss", "time", "partition"])
            w_geo = csv.writer(f_geo)
            w_geo.writerow(["index", "loss", "time", "partition"])

            n = cfg["n"]
            for row in reader:
                condicion_bits = letters_to_bits(row["conditions"], n)
                alcance_bits = letters_to_bits(row["purview"], n)
                mecanismo_bits = letters_to_bits(row["mechanism"], n)
                estado_str = row["state"]

                sub_qn = build_subsistema(tpm, estado_str, condicion_bits, alcance_bits, mecanismo_bits)
                sol_qn = QNodes(sub_qn).resolver()
                w_qn.writerow([row["index"], sol_qn.perdida, sol_qn.tiempo_ejecucion, sol_qn.particion.strip().replace("\n", "\\n")])

                sub_geo = build_subsistema(tpm, estado_str, condicion_bits, alcance_bits, mecanismo_bits)
                sol_geo = GeoMIP(sub_geo).resolver()
                w_geo.writerow([row["index"], sol_geo.perdida, sol_geo.tiempo_ejecucion, sol_geo.particion.strip().replace("\n", "\\n")])

                diff = abs(sol_geo.perdida - sol_qn.perdida)
                if diff < 1e-9:
                    tag = "OK"
                    ok += 1
                else:
                    tag = f"DIFF={diff:.4f}"
                    diff_count += 1
                print(
                    f"[{net} #{row['index']}] "
                    f"geo={sol_geo.perdida:.6f}  qn={sol_qn.perdida:.6f}  {tag}"
                )

        print(f"\n{net}: {ok} OK / {diff_count} DIFF (de {ok + diff_count})\n")
        total_ok += ok
        total_diff += diff_count

    print(f"TOTAL: {total_ok} OK / {total_diff} DIFF (de {total_ok + total_diff})")


if __name__ == "__main__":
    main()
