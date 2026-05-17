"""
KQNodes — Extensión de QNodes para k-particiones.

Hereda toda la infraestructura de QNodes (preparación del subsistema,
algoritmo de Queyranne, función submodular, memoización de EMDs) y añade:

  - algorithm_k(vertices, k): en lugar de devolver un único par candidato,
    aplica k-1 cortes sucesivos del proceso de Queyranne para obtener k grupos.
  - aplicar_estrategia: sobrescribe la de QNodes, acepta parámetro k.

Para k=2 el resultado debe coincidir con QNodes (TV-03).
"""

import time
from math import comb

import numpy as np

from src.constants.base import ACTUAL, EFFECT
from src.middlewares.slogger import SafeLogger
from src.funcs.iit import emd_efecto
from src.funcs.format import fmt_biparticion_q
from src.models.core.solution import Solution
from src.strategies.q_nodes import QNodes

KQNODES_LABEL = "KQNodes"
KQNODES_TAG = f"{KQNODES_LABEL}_strategy"

_PRESUPUESTO_DEFAULT = 10_000
_K_TOPE_DEFAULT = 8


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


class KQNodes(QNodes):
    """
    Extensión de QNodes que busca la k-partición óptima del subsistema.

    Para k=2 reproduce exactamente el comportamiento de QNodes (TV-03).

    Args:
        tpm (np.ndarray): Matriz de Probabilidad de Transición.
        k (int): Número de partes de la partición. Por defecto 2.
        k_tope (int): Límite superior para barridos automáticos.
        presupuesto (int): Máximo de evaluaciones antes de modo heurístico.
    """

    def __init__(
        self,
        tpm: np.ndarray,
        k: int = 2,
        k_tope: int = _K_TOPE_DEFAULT,
        presupuesto: int = _PRESUPUESTO_DEFAULT,
    ):
        super().__init__(tpm)
        self.k = k
        self.k_tope = k_tope
        self.presupuesto = presupuesto
        self.logger = SafeLogger(KQNODES_TAG)
        # Memoria para k-particiones: clave -> (emd, dist_marginal)
        self.memoria_k_particiones: dict[tuple, tuple[float, np.ndarray]] = {}


    def aplicar_estrategia(
        self,
        estado_inicial: str,
        condicion: str,
        alcance: str,
        mecanismo: str,
        k: int | None = None,
    ) -> Solution:
        """
        Aplica la búsqueda de la k-MIP usando el algoritmo de Queyranne extendido.

        Args:
            estado_inicial: cadena binaria del estado inicial del sistema.
            condicion: cadena binaria de condición de fondo.
            alcance: cadena binaria de alcance (futuro).
            mecanismo: cadena binaria de mecanismo (presente).
            k: número de partes. Si es None usa self.k.

        Returns:
            Solution con la k-partición de menor pérdida.
        """
        if k is not None:
            self.k = k

        # Preparar subsistema (hereda de SIA vía QNodes)
        self.sia_preparar_subsistema(estado_inicial, condicion, alcance, mecanismo)

        futuro = tuple(
            (EFFECT, idx) for idx in self.sia_subsistema.indices_ncubos
        )
        presente = tuple(
            (ACTUAL, idx) for idx in self.sia_subsistema.dims_ncubos
        )

        self.m = self.sia_subsistema.indices_ncubos.size
        self.n = self.sia_subsistema.dims_ncubos.size
        self.indices_alcance = self.sia_subsistema.indices_ncubos
        self.indices_mecanismo = self.sia_subsistema.dims_ncubos
        self.tiempos = (
            np.zeros(self.n, dtype=np.int8),
            np.zeros(self.m, dtype=np.int8),
        )

        vertices = list(presente + futuro)
        self.vertices = set(presente + futuro)

        # Limpiar memoización de la llamada anterior
        self.memoria_delta = {}
        self.memoria_grupo_candidato = {}
        self.memoria_k_particiones = {}
        self.clave_submodular = [], []

        # k=2: delegar al algoritmo original de QNodes (garantiza TV-03)
        if self.k == 2:
            mip = self.algorithm(vertices)
            fmt_mip = fmt_biparticion_q(list(mip), self.nodes_complement(mip))
            perdida, dist = self.memoria_grupo_candidato[mip]
            return Solution(
                estrategia=KQNODES_LABEL,
                perdida=perdida,
                distribucion_subsistema=self.sia_dists_marginales,
                distribucion_particion=dist,
                tiempo_total=time.time() - self.sia_tiempo_inicio,
                particion=fmt_mip,
            )

        # k>2: algoritmo k extendido
        mejor_grupos = self.algorithm_k(vertices, self.k)
        clave = tuple(sorted(mejor_grupos[0]))
        perdida, dist = self.memoria_k_particiones.get(
            clave, (float("inf"), self.sia_dists_marginales)
        )
        fmt_mip = fmt_biparticion_q(list(clave), self.nodes_complement(list(clave)))

        return Solution(
            estrategia=KQNODES_LABEL,
            perdida=perdida,
            distribucion_subsistema=self.sia_dists_marginales,
            distribucion_particion=dist,
            tiempo_total=time.time() - self.sia_tiempo_inicio,
            particion=fmt_mip,
        )


    def algorithm_k(
        self, vertices: list, k: int
    ) -> list[list]:
        """
        Extiende el algoritmo de Queyranne para encontrar la k-partición óptima
        aplicando k-1 cortes sucesivos.

        Proceso:
        1. Sobre los vértices actuales ejecuta el algoritmo de Queyranne original
           para identificar el mejor corte (grupo candidato vs. resto).
        2. El grupo candidato pasa a ser un subgrupo fijo de la k-partición.
        3. El "resto" de vértices se convierte en la entrada para el siguiente corte.
        4. Se repite k-1 veces; el grupo final es el remanente.

        Los cortes intermedios usan la función submodular heredada de QNodes,
        reutilizando la memoización de EMDs individuales entre cortes.

        Args:
            vertices: lista de vértices del subsistema.
            k: número de grupos deseado (k >= 2).

        Returns:
            Lista de k grupos, donde cada grupo es una lista de vértices.
        """
        n_vertices = len(vertices)
        k_efectivo = min(k, n_vertices)

        # Verificar presupuesto S(n, k)
        s_nk = _stirling2(n_vertices, k_efectivo)
        if s_nk > self.presupuesto:
            self.logger.critic(
                f"S({n_vertices},{k_efectivo})={s_nk} > presupuesto. "
                "Modo heurístico: un solo barrido Queyranne."
            )

        grupos: list[list] = []
        vertices_restantes = list(vertices)

        for corte in range(k_efectivo - 1):
            if len(vertices_restantes) < 2:
                break

            # Limpiar memoización de grupo candidato (no de deltas: se reusan)
            self.memoria_grupo_candidato = {}
            self.clave_submodular = [], []

            mip_corte = self.algorithm(vertices_restantes)

            # Separar el grupo candidato del resto
            grupo_candidato = list(mip_corte)
            vertices_restantes = [
                v for v in vertices_restantes
                if v not in grupo_candidato
                and (not isinstance(v, list) or v not in grupo_candidato)
            ]

            # Registrar EMD de este corte
            if mip_corte in self.memoria_grupo_candidato:
                emd_corte, dist_corte = self.memoria_grupo_candidato[mip_corte]
            else:
                # Calcular EMD del grupo candidato contra el subsistema completo
                emd_corte, dist_corte = self._evaluar_grupo(grupo_candidato)

            clave = tuple(sorted(grupo_candidato))
            self.memoria_k_particiones[clave] = (emd_corte, dist_corte)
            grupos.append(grupo_candidato)

        # Último grupo: todo lo que queda
        if vertices_restantes:
            emd_resto, dist_resto = self._evaluar_grupo(vertices_restantes)
            clave_resto = tuple(sorted(vertices_restantes))
            self.memoria_k_particiones[clave_resto] = (emd_resto, dist_resto)
            grupos.append(vertices_restantes)

        return grupos if grupos else [vertices]

    def _evaluar_grupo(self, grupo: list) -> tuple[float, np.ndarray]:
        """
        Evalúa la EMD de un grupo de vértices biparticionando el subsistema.

        Args:
            grupo: lista de vértices (tiempo, índice).

        Returns:
            (emd, distribucion_marginal) del grupo.
        """
        futuros: list[int] = []
        presentes: list[int] = []

        for elemento in grupo:
            if isinstance(elemento, tuple) and len(elemento) == 2:
                tiempo, idx = elemento
                (futuros if tiempo else presentes).append(idx)
            elif isinstance(elemento, list):
                for tiempo, idx in elemento:
                    (futuros if tiempo else presentes).append(idx)

        futuros_arr = np.array(futuros, dtype=np.int8)
        presentes_arr = np.array(presentes, dtype=np.int8)

        try:
            particion = self.sia_subsistema.bipartir(futuros_arr, presentes_arr)
            dist = particion.distribucion_marginal()
            emd = emd_efecto(dist, self.sia_dists_marginales)
            return emd, dist
        except Exception as exc:
            self.logger.debug(f"Error evaluando grupo: {exc}")
            return float("inf"), self.sia_dists_marginales
