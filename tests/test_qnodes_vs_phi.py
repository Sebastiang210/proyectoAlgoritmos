"""Compara estrategias sobre redes pequeñas.

QNodes (oracle Zeta) vs q_nodes.py (implementación clásica):
  → deben dar φ IDÉNTICO (misma fórmula emd_efecto, distinto oráculo).

QNodes vs Phi (pyphi):
  → valores DIFERENTES por diseño: nuestro emd_efecto usa distribuciones
  marginales (L1 factorizado), pyphi usa EMD sobre repertorios completos.

Uso:
    cd /Users/oh/World/External/Study/UC/Algorithms/2026-JSGH
    PYPHI_WELCOME_OFF=yes \\
      /Users/oh/World/External/Study/UC/Algorithms/IIT-2026A/.venv/bin/python \\
      tests/test_qnodes_vs_phi.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from src.models.core.system import System
from src.strategies.QNodes.qnodes import QNodes

SAMPLES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "src", ".samples")


def cargar_tpm(nombre: str) -> np.ndarray:
    return np.genfromtxt(os.path.join(SAMPLES_DIR, nombre), delimiter=",")


def preparar_subsistema(tpm: np.ndarray, estado: str) -> System:
    return System(tpm, np.array([int(b) for b in estado], dtype=np.int8))


def correr_qnodes(tpm, estado_str) -> float:
    subsistema = preparar_subsistema(tpm, estado_str)
    sol = QNodes(subsistema).resolver()
    print(f"  [QNodes]  φ={sol.perdida:.6f}  t={sol.tiempo_ejecucion:.4f}s")
    print(f"           {sol.particion.strip()}")
    return sol.perdida


def correr_qnodes_clasico(tpm, estado_str) -> float | None:
    try:
        from src.strategies.QNodes.q_nodes import QNodes as QNodesOld
        q = QNodesOld(tpm)
        sol = q.aplicar_estrategia(
            estado_str,
            "1" * len(estado_str),
            "1" * len(estado_str),
            "1" * len(estado_str),
        )
        print(f"  [q_nodes] φ={sol.perdida:.6f}  t={sol.tiempo_ejecucion:.4f}s")
        return sol.perdida
    except Exception as e:
        print(f"  [q_nodes] no disponible: {e}")
        return None


def correr_phi(tpm, estado_str) -> float | None:
    try:
        from src.strategies.phi import Phi
        subsistema = preparar_subsistema(tpm, estado_str)
        sol = Phi(subsistema, tpm, params=None).resolver()
        print(f"  [Phi]     φ={sol.perdida:.6f}  t={sol.tiempo_ejecucion:.4f}s  (pyphi EMD)")
        return sol.perdida
    except Exception as e:
        print(f"  [Phi]     error: {e}")
        return None


def comparar(red: str, estado: str):
    print(f"\n{'─'*60}")
    print(f"  {red}  estado={estado}")
    print(f"{'─'*60}")

    tpm = cargar_tpm(red)
    phi_q = correr_qnodes(tpm, estado)
    phi_old = correr_qnodes_clasico(tpm, estado)
    phi_p = correr_phi(tpm, estado)

    if phi_old is not None:
        diff_old = abs(phi_q - phi_old)
        tag = "✓ IDÉNTICO" if diff_old < 1e-9 else f"✗ DIFERENCIA={diff_old:.2e}"
        print(f"\n  QNodes vs q_nodes : {tag}")

    if phi_p is not None:
        diff_phi = abs(phi_q - phi_p)
        print(f"  QNodes vs Phi     : |Δ|={diff_phi:.4f}  (diferencia esperada, EMD distinto)")


if __name__ == "__main__":
    casos = [
        ("N3A.csv", "000"),
        ("N3A.csv", "101"),
        ("N4A.csv", "0000"),
        ("N4A.csv", "1010"),
    ]
    for red, estado in casos:
        try:
            comparar(red, estado)
        except Exception as e:
            print(f"\nError en {red}/{estado}: {e}")
            import traceback
            traceback.print_exc()
    print()
