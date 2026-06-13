"""Helpers compartidos por los scripts de `src/shared/run_*.py`.

Construye subsistemas a partir de los CSV de casos (`input/N5.csv`,
`input/N10.csv`) y centraliza las rutas y configuraciones de red usadas
por los corredores de estrategias.
"""

import os

import numpy as np

from src.funcs.iit import ABECEDARY
from src.models.core.system import System

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SAMPLES_DIR = os.path.join(ROOT, "src", ".samples")
INPUT_DIR = os.path.join(ROOT, "src", "shared", "input")
OUTPUT_DIR = os.path.join(ROOT, "src", "shared", "output")

# Cada entrada describe una red de prueba: `input` (casos en src/shared/input),
# `tpm` (matriz en src/.samples) y `net` (nombre de red usado como prefijo
# `{net}-{ALGO}.csv` en src/shared/output).
CONFIGS = [
    dict(input="N5.csv", tpm="N5B.csv", n=5, net="N5B"),
    dict(input="N10.csv", tpm="N10A.csv", n=10, net="N10A"),
]


def letters_to_bits(letters: str, n: int) -> str:
    """Codifica 'ABCD' como bits posicionales según ABECEDARY (A=0, B=1, ...)."""
    letset = set(letters)
    return "".join("1" if ABECEDARY[i] in letset else "0" for i in range(n))


def zero_dims(bits: str) -> np.ndarray:
    """Índices donde el bit es '0' (dimensiones a condicionar/substraer)."""
    return np.array([i for i, b in enumerate(bits) if b == "0"], dtype=np.int8)


def build_subsistema(tpm, estado_str, condicion_bits, alcance_bits, mecanismo_bits) -> System:
    estado = np.array([int(c) for c in estado_str], dtype=np.int8)
    completo = System(tpm, estado)
    candidato = completo.condicionar(zero_dims(condicion_bits))
    return candidato.substraer(zero_dims(alcance_bits), zero_dims(mecanismo_bits))
