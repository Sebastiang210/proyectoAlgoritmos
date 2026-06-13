"""Transformada Zeta sobre caras del hipercubo (oráculo para QNodes).

hyperfaces(N, D, delta_nd) precomputa todas las sumas de cara en O((N+D)·2^D),
permitiendo que cada consulta de EMD en QNodes cueste O(N) en lugar de O(N·2^D).
Ver src/strategies/QNodes/oracle.md para la derivación completa.
"""

import numpy as np


def hyperfaces(N: int, D: int, delta_nd: np.ndarray, _pivot_idx=None) -> np.ndarray:
    """Precomputa sumas Zeta: sumas[i, m] = Σ_{x ⊆ m} delta_nd[i, *bits(x)].

    Args:
        N: número de ncubos de efecto.
        D: número de dimensiones del mecanismo.
        delta_nd: array (N, 2, 2, ..., 2) con D ejes binarios,
                  ya normalizado: δ = H − pivot.
        _pivot_idx: ignorado (delta_nd ya viene normalizado).

    Returns:
        sumas: array (N, 2^D) donde sumas[i, m] es la suma Zeta sobre la cara m.
        El bit d de m corresponde a la d-ésima dimensión (eje d+1 de delta_nd).
    """
    size = 1 << D
    sumas = np.empty((N, size), dtype=np.float64)

    # Init: sumas[:, m] = delta_nd[:, b0(m), b1(m), ..., b{D-1}(m)]
    # donde b_d(m) = (m >> d) & 1  (little-endian: bit d = eje d)
    for m in range(size):
        idx = tuple((m >> d) & 1 for d in range(D))
        sumas[:, m] = delta_nd[(slice(None),) + idx]

    # Transformada Zeta: sumas[i, m] += sumas[i, m sin bit d], para cada d
    for d in range(D):
        bit = 1 << d
        for m in range(size):
            if m & bit:
                sumas[:, m] += sumas[:, m ^ bit]

    return sumas
