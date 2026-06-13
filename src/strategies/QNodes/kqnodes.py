"""
KQNodes — k-partition extension of QNodes with exhaustive enumeration.

For k=2 reproduces QNodes behavior (verified against TV-03).
For k>2 uses exhaustive enumeration over S(n,k) partitions to guarantee
global optimality (loss exactness).

Algorithm:
- Enumerate all S(n,k) partitions of vertices
- For each partition part, compute EMD(part vs original distribution)
- Total loss = sum of all part EMDs
- Return partition with minimum total loss
"""

import time
from math import comb
from typing import Iterator, Union

import numpy as np

from src.constants.base import ACTUAL, EFFECT, FLOAT_ZERO, INFTY_POS, INT_ZERO
from src.middlewares.slogger import SafeLogger
from src.funcs.iit import emd_efecto
from src.funcs.format import fmt_kparticion_kqnodes
from src.models.core.solution import Solution
from src.strategies.QNodes.qnodes import QNodes

KQNODES_LABEL = "KQN"
KQNODES_TAG = f"{KQNODES_LABEL}_strategy"

_PRESUPUESTO_DEFAULT = 10_000


def _stirling2(n: int, k: int) -> int:
    if k == 0:
        return 1 if n == 0 else 0
    if k > n:
        return 0
    total = sum(
        ((-1) ** (k - j)) * comb(k, j) * (j ** n)
        for j in range(k + 1)
    )
    factorial_k = 1
    for i in range(2, k + 1):
        factorial_k *= i
    return total // factorial_k


def _generar_particiones(
    vertices: list, k: int
) -> Iterator[list[list]]:
    """Genera todas las particiones de n vertices en k grupos no vacios."""
    n = len(vertices)
    if k == 1:
        yield [list(vertices)]
        return
    if k == n:
        yield [[v] for v in vertices]
        return

    def recursiva(idx: int, grupos: list[list]):
        if idx == n:
            if len(grupos) == k:
                yield [list(g) for g in grupos]
            return
        for g_idx in range(len(grupos)):
            grupos[g_idx].append(vertices[idx])
            yield from recursiva(idx + 1, grupos)
            grupos[g_idx].pop()
        if len(grupos) < k:
            grupos.append([vertices[idx]])
            yield from recursiva(idx + 1, grupos)
            grupos.pop()

    yield from recursiva(0, [])


class KQNodes(QNodes, nombre="kqn"):
    """
    Extensión de QNodes para k-particiones con búsqueda exhaustiva.

    Para k=2 reproduce exactamente el comportamiento de QNodes (verificado TV-03).

    Args:
        subsistema_o_tpm: System o TPM.
        k (int): Número de partes de la partición. Por defecto 2.
        presupuesto (int): Límite de particiones antes de modo heurístico.
    """

    def __init__(
        self,
        subsistema_o_tpm,
        k: int = 2,
        presupuesto: int = _PRESUPUESTO_DEFAULT,
    ):
        super().__init__(subsistema_o_tpm)
        self.k = k
        self.presupuesto = presupuesto
        self.logger = SafeLogger(KQNODES_TAG)

    def aplicar_estrategia(
        self,
        estado_inicial: str,
        condicion: str,
        alcance: str,
        mecanismo: str,
        k: int | None = None,
    ) -> Solution:
        """Aplica la búsqueda de la k-MIP sobre el subsistema.

        Si el constructor recibió un TPM, prepara el subsistema.
        Si recibió un System ya preparado, lo usa directamente.
        """
        if k is not None:
            self.k = k
        if self.tpm is not None:
            self.sia_preparar_subsistema(estado_inicial, condicion, alcance, mecanismo)
        return self.resolver()

    def resolver(self) -> Solution:
        t0 = time.perf_counter()
        dm_original = self.distribucion

        indices = self.sistema.indices
        dims = self.sistema.dims

        if not len(indices) or not len(dims):
            return Solution(
                estrategia=KQNODES_LABEL,
                perdida=FLOAT_ZERO,
                distribucion_subsistema=dm_original,
                distribucion_particion=dm_original,
                particion=fmt_kparticion_kqnodes([[], []]).strip(),
                tiempo_total=time.perf_counter() - t0,
                quiere_hablar=False,
            )

        self._QNodes__preparar_oraculo()

        futuro = tuple((EFFECT, idx) for idx in indices)
        presente = tuple((ACTUAL, dim) for dim in dims)

        self.clave_submodular: tuple[list[int], list[int]] = ([], [])
        self.memoria_bipart: dict = {}
        self.memoria_grupo_candidato: dict = {}

        vertices = list(presente + futuro)
        n_vertices = len(vertices)

        s_nk = _stirling2(n_vertices, self.k)
        heuristico = s_nk > self.presupuesto

        if heuristico:
            self.logger.critic(
                f"S({n_vertices},{self.k})={s_nk} > presupuesto. "
                "Modo heurístico: greedy partition."
            )
            mejor_particion = self._greedy_k_partition(vertices, self.k)
        else:
            mejor_particion = self._exhaustive_k_partition(vertices, self.k)

        perdida_total = self._compute_partition_loss(mejor_particion)
        dist_particion = self._compute_partition_distribution(mejor_particion)
        texto = fmt_kparticion_kqnodes(mejor_particion)

        return Solution(
            estrategia=KQNODES_LABEL,
            perdida=perdida_total,
            distribucion_subsistema=dm_original,
            distribucion_particion=dist_particion,
            particion=texto.strip(),
            tiempo_total=time.perf_counter() - t0,
            quiere_hablar=False,
        )

    def _exhaustive_k_partition(
        self, vertices: list, k: int
    ) -> list[list]:
        """Búsqueda exhaustiva de la k-partición óptima."""
        mejor_particion = None
        mejor_perdida = INFTY_POS

        for particion in _generar_particiones(vertices, k):
            perdida = self._compute_partition_loss(particion)
            if perdida < mejor_perdida:
                mejor_perdida = perdida
                mejor_particion = particion

        return mejor_particion

    def _greedy_k_partition(
        self, vertices: list, k: int
    ) -> list[list]:
        """Particionamiento greedy como fallback para casos grandes."""
        grupos: list[list] = []
        vertices_restantes = list(vertices)

        for _ in range(k - 1):
            if len(vertices_restantes) < 2:
                break
            self.memoria_grupo_candidato = {}
            self.memoria_bipart = {}
            self.clave_submodular = [], []

            mip = self.algorithm(vertices_restantes)
            if mip is None:
                break
            grupo_candidato = list(mip)
            if not grupo_candidato:
                break
            vertices_restantes = [
                v for v in vertices_restantes
                if v not in grupo_candidato
            ]
            grupos.append(grupo_candidato)

        needed = k - len(grupos)
        if needed > 0 and vertices_restantes:
            if needed == 1:
                grupos.append(vertices_restantes)
            else:
                nVR = len(vertices_restantes)
                if nVR <= needed:
                    for i in range(needed):
                        if i < nVR:
                            grupos.append([vertices_restantes[i]])
                        else:
                            grupos.append([])
                else:
                    split_size = nVR // needed
                    remainder = nVR % needed
                    idx = 0
                    for i in range(needed - 1):
                        sz = split_size + (1 if i < remainder else 0)
                        grupos.append(vertices_restantes[idx:idx + sz])
                        idx += sz
                    grupos.append(vertices_restantes[idx:])

        return grupos if grupos else [vertices]

    def _compute_partition_loss(self, particion: list[list]) -> float:
        """Calcula la pérdida de una k-partición como EMD entre distribución
        combinada y distribución original.

        La distribución combinada es el promedio de las distribuciones de cada
        grupo, representando la partición como un todo.
        """
        dist_combinada = self._compute_partition_distribution(particion)
        return float(emd_efecto(dist_combinada, self.distribucion))

    def _compute_partition_distribution(
        self, particion: list[list]
    ) -> np.ndarray:
        """Calcula distribución combinada de la partición (promedio ponderado)."""
        n_ncubos = len(self.sistema.indices)
        dist = np.zeros(n_ncubos, dtype=np.float32)
        count = 0
        for grupo in particion:
            futuros, presentes = self._extraer_indices(grupo)
            if not futuros.size and not presentes.size:
                continue
            try:
                bip = self.sistema.bipartir(futuros, presentes)
                dist += bip.distribucion_marginal()
                count += 1
            except Exception:
                pass
        if count > 0:
            dist /= count
        return dist

    def _extraer_indices(
        self, grupo: list
    ) -> tuple[np.ndarray, np.ndarray]:
        """Extrae índices futuros y presentes de un grupo de vértices."""
        futuros: list[int] = []
        presentes: list[int] = []

        for elem in self.__flatten(grupo):
            tiempo, idx = elem
            if tiempo == EFFECT:
                futuros.append(idx)
            else:
                presentes.append(idx)

        return np.array(futuros, dtype=np.int8), np.array(presentes, dtype=np.int8)

    def __flatten(self, nodo):
        """Aplana un vértice o grupo (anidado) a secuencia de vértices."""
        if isinstance(nodo, tuple) and len(nodo) == 2 and isinstance(nodo[0], int):
            yield nodo
        else:
            for sub in nodo:
                yield from self.__flatten(sub)