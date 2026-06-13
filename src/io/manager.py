"""Helpers de I/O para construir sistemas desde TPM y estado."""

import numpy as np

from src.models.core.system import System


def crear_sistema(tpm: np.ndarray, estado) -> System:
    """Crea un System a partir de una TPM y un estado inicial.

    Args:
        tpm: Matriz de probabilidad de transición (2^N × N).
        estado: Estado inicial como iterable de bits (0/1).

    Returns:
        System construido con el estado y la TPM dados.
    """
    estado_arr = np.array(list(estado), dtype=np.int8)
    return System(tpm, estado_arr)
