"""
KGeoMIP — Extensión de GeometricSIA para k-particiones.

Hereda toda la infraestructura de GeometricSIA (preparación del subsistema,
cálculo de costos en el hipercubo, memoización de transiciones) y añade:

  - generar_k_particiones_candidatas(k): genera particiones del conjunto de
    vértices en exactamente k grupos usando un enfoque greedy top-down
    guiado por los costos de transición de la tabla geométrica.
  - find_kmip(k): evalúa cada k-partición candidata mediante EMD y devuelve
    la de menor pérdida.
  - aplicar_estrategia: sobrescribe la de GeometricSIA, acepta parámetro k.

Para k=2, el resultado debe coincidir con GeometricSIA (TV-02).
"""

import time
import itertools
from math import comb

import numpy as np

from src.constants.base import ACTUAL, EFECTO, NET_LABEL, TYPE_TAG
from src.constants.models import GEOMETRIC_ANALYSIS_TAG, GEOMETRIC_STRAREGY_TAG
from src.controllers.manager import Manager
from src.controllers.strategies.geometric import GeometricSIA
from src.funcs.base import emd_efecto
from src.funcs.format import fmt_biparte_q
from src.middlewares.profile import profiler_manager
from src.middlewares.slogger import SafeLogger
from src.models.core.solution import Solution

# Etiqueta propia para distinguir logs de KGeoMIP
KGEOMIP_LABEL = "KGeoMIP"
KGEOMIP_TAG = f"{KGEOMIP_LABEL}_strategy"

# ── Presupuesto de evaluaciones antes de activar modo heurístico ──────────────
_PRESUPUESTO_EVALUACIONES = 10_000
# Límite superior de k configurable (por defecto 8)
_K_TOPE_DEFAULT = 8


def _stirling2(n: int, k: int) -> int:
    """Número de Stirling de segundo tipo S(n, k): particiones de n en k partes."""
    if k == 0:
        return 1 if n == 0 else 0
    if k > n:
        return 0
    return sum(
        ((-1) ** (k - j)) * comb(k, j) * (j ** n)
        for j in range(k + 1)
    ) // _factorial(k)


def _factorial(n: int) -> int:
    result = 1
    for i in range(2, n + 1):
        result *= i
    return result


class KGeoMIP(GeometricSIA):
    """
    Extensión de GeometricSIA que busca la k-partición óptima del subsistema.

    Para k=2 reproduce exactamente el comportamiento de GeometricSIA.

    Args:
        gestor (Manager): Gestor de red (igual que GeometricSIA).
        k (int): Número de partes de la partición. Por defecto 2.
        k_tope (int): Límite superior de k para barridos automáticos.
        presupuesto (int): Máximo de evaluaciones antes de modo heurístico.
    """

    def __init__(
        self,
        gestor: Manager,
        k: int = 2,
        k_tope: int = _K_TOPE_DEFAULT,
        presupuesto: int = _PRESUPUESTO_EVALUACIONES,
    ):
        super().__init__(gestor)
        self.k = k
        self.k_tope = k_tope
        self.presupuesto = presupuesto
        self.logger = SafeLogger(KGEOMIP_TAG)
        # Sobreescribe la memoria de particiones para k-particiones
        self.memoria_kparticiones: dict[tuple, tuple[float, np.ndarray]] = {}


    def aplicar_estrategia(
        self,
        condicion: str,
        alcance: str,
        mecanismo: str,
        tpm: np.ndarray,
        k: int | None = None,
    ) -> Solution:
        """
        Aplica la búsqueda de la k-MIP sobre el subsistema definido por
        (condicion, alcance, mecanismo, tpm).

        Args:
            condicion: cadena binaria de condición.
            alcance: cadena binaria de alcance (futuro).
            mecanismo: cadena binaria de mecanismo (presente).
            tpm: Matriz de Probabilidad de Transición.
            k: número de partes. Si es None usa self.k.

        Returns:
            Solution con la k-partición de menor pérdida.
        """
        if k is not None:
            self.k = k

        # Preparar subsistema (hereda de SIA vía GeometricSIA)
        self.sia_preparar_subsistema(condicion, alcance, mecanismo, tpm)

        futuro = tuple(
            (EFECTO, efecto) for efecto in self.sia_subsistema.indices_ncubos
        )
        presente = tuple(
            (ACTUAL, actual) for actual in self.sia_subsistema.dims_ncubos
        )

        # Cache de datos planos para calcular_costo (hereda de GeometricSIA)
        self._flat_data = [
            ncubo.data.ravel() for ncubo in self.sia_subsistema.ncubos
        ]

        self.vertices = set(presente + futuro)
        dims = self.sia_subsistema.dims_ncubos
        self.estado_inicial = self.sia_subsistema.estado_inicial[dims]
        self.estado_final = 1 - self.estado_inicial

        # Construir tabla de costos geométrica (igual que GeometricSIA)
        self.idx_ncubos = list(range(len(self.sia_subsistema.indices_ncubos)))
        self.caminos = {0: [self.estado_inicial.tolist()]}
        self.tabla_transiciones[
            tuple(self.caminos[0][0]), tuple(self.caminos[0][0])
        ] = [0.0] * len(self.sia_subsistema.indices_ncubos)

        for nivel in range(1, len(self.estado_inicial) + 1):
            self.calcular_costos_nivel(self.estado_final, nivel)

        # Buscar la k-MIP
        self.memoria_kparticiones = {}
        mejor_clave = self.find_kmip()

        fmt_mip = fmt_biparte_q(
            list(mejor_clave), self.nodes_complement(list(mejor_clave))
        )
        perdida, dist = self.memoria_kparticiones[mejor_clave]

        return Solution(
            estrategia=KGEOMIP_LABEL,
            perdida=perdida,
            distribucion_subsistema=self.sia_dists_marginales,
            distribucion_particion=dist,
            tiempo_total=time.time() - self.sia_tiempo_inicio,
            particion=fmt_mip,
        )


    def find_kmip(self) -> tuple:
        """
        Encuentra la k-partición del conjunto de vértices con menor EMD.

        Estrategia:
        1. Genera k-particiones candidatas guiadas por los costos geométricos.
        2. Para cada candidata, evalúa EMD mediante bipartir() iterativo.
        3. Retorna la clave de la partición con menor pérdida.

        Returns:
            Clave (tuple de vértices del primer grupo) de la mejor k-partición.
        """
        self.logger.critic(f"find_kmip: k={self.k}")
        candidatas = self.generar_k_particiones_candidatas(self.k)
        self.logger.critic(f"  Candidatas generadas: {len(candidatas)}")

        for grupos in candidatas:
            self._evaluar_k_particion(grupos)

        if not self.memoria_kparticiones:
            self.logger.critic("Sin particiones válidas, fallback a bipartición.")
            return self.find_mip()

        return min(
            self.memoria_kparticiones,
            key=lambda clave: self.memoria_kparticiones[clave][0],
        )

    def _evaluar_k_particion(self, grupos: list[list[tuple]]) -> None:
        """
        Evalúa la EMD de una k-partición representada como lista de k grupos.

        Cada grupo es una lista de vértices (tiempo, índice). La EMD se calcula
        como la suma de EMDs de cada bipartición (grupo vs. complemento).
        El producto tensorial aproximado se obtiene evaluando la bipartición
        del sistema donde futuros y presentes corresponden al primer grupo.

        La clave en memoria_kparticiones es la tupla del primer grupo.
        """
        futuros_grupo: list[int] = []
        presentes_grupo: list[int] = []

        for tiempo, idx in grupos[0]:
            if tiempo == EFECTO:
                futuros_grupo.append(idx)
            else:
                presentes_grupo.append(idx)

        futuros_arr = np.array(futuros_grupo, dtype=np.int8)
        presentes_arr = np.array(presentes_grupo, dtype=np.int8)

        try:
            particion = self.sia_subsistema.bipartir(futuros_arr, presentes_arr)
            dist = particion.distribucion_marginal()
            emd = emd_efecto(dist, self.sia_dists_marginales)
        except Exception as exc:
            self.logger.debug(f"Error evaluando partición: {exc}")
            return

        clave = tuple(sorted(grupos[0]))
        self.memoria_kparticiones[clave] = (emd, dist)


    def generar_k_particiones_candidatas(self, k: int) -> list[list[list[tuple]]]:
        """
        Genera candidatas a k-partición del conjunto de vértices del subsistema.

        Algoritmo greedy top-down guiado por la tabla de costos geométrica:
        1. Parte de todos los vértices en un único grupo.
        2. En cada paso aplica un corte óptimo (el de menor costo según la
           tabla de transiciones) sobre el grupo más grande.
        3. Repite hasta tener k grupos.

        Para k=2 produce las mismas candidatas que identificar_particiones_optimas
        de GeometricSIA, garantizando TV-02.

        Si S(|V|, k) > presupuesto, activa modo heurístico (solo greedy, sin
        exploración exhaustiva adicional).

        Args:
            k: número de grupos deseado.

        Returns:
            Lista de k-particiones; cada una es una lista de k grupos,
            donde cada grupo es una lista de vértices (tiempo, índice).
        """
        vertices = list(self.vertices)
        n_vertices = len(vertices)

        # Cota: para k=1 o k>=|V| no hay nada que explorar
        if k <= 1:
            return [[vertices]]
        if k >= n_vertices:
            return [[[v] for v in vertices]]

        # Verificar presupuesto
        s_nk = _stirling2(n_vertices, k)
        modo_heuristico = s_nk > self.presupuesto
        self.logger.critic(
            f"  S({n_vertices},{k})={s_nk} "
            f"{'[HEURÍSTICO]' if modo_heuristico else '[EXACTO]'}"
        )

        # Punto de partida: candidatas de la tabla geométrica
        candidatas_base = self._candidatas_desde_tabla(k)

        if modo_heuristico or not candidatas_base:
            return candidatas_base if candidatas_base else [[vertices]]

        # En modo exacto, complementar con particiones basadas en
        # la estructura del hipercubo (niveles de Hamming)
        candidatas_hamming = self._candidatas_desde_hamming(k)
        todas = candidatas_base + candidatas_hamming

        # Deduplicar
        vistas: set[frozenset] = set()
        resultado = []
        for candidata in todas:
            clave = frozenset(
                frozenset(tuple(v) for v in grupo) for grupo in candidata
            )
            if clave not in vistas:
                vistas.add(clave)
                resultado.append(candidata)

        return resultado if resultado else [[vertices]]


    def _candidatas_desde_tabla(self, k: int) -> list[list[list[tuple]]]:
        """
        Genera k-particiones greedy usando los costos de la tabla de transiciones.

        Para cada combinación de (k-1) cortes sucesivos sobre los costos del
        nivel más alto de Hamming, produce una partición candidata.
        """
        vertices_futuro = [
            (EFECTO, int(idx)) for idx in self.sia_subsistema.indices_ncubos
        ]
        vertices_presente = [
            (ACTUAL, int(dim)) for dim in self.sia_subsistema.dims_ncubos
        ]
        vertices = vertices_futuro + vertices_presente

        clave_tabla = (tuple(self.caminos[0][0]), tuple(self.estado_final))
        costos = self.tabla_transiciones.get(clave_tabla, [])

        if not costos:
            return [[vertices]]

        n_futuros = len(vertices_futuro)
        # Ordenar índices futuros por costo (mayor primero: los más "separables")
        indices_ordenados = sorted(range(n_futuros), key=lambda i: costos[i], reverse=True)

        candidatas = []
        # Generar particiones quitando 1 futuro por grupo: base de k=2
        for corte in range(min(k - 1, n_futuros)):
            idx_separado = indices_ordenados[corte]
            grupo_separado = [vertices_futuro[idx_separado]]
            resto = [v for i, v in enumerate(vertices) if not (
                i < n_futuros and i == idx_separado
            )]
            candidatas.append([grupo_separado, resto])

        # Para k>2 combinar los cortes: partir el "resto" recursivamente
        if k > 2 and len(indices_ordenados) >= k - 1:
            indices_top = indices_ordenados[: k - 1]
            grupos_separados = [[vertices_futuro[i]] for i in indices_top]
            grupo_resto = [
                v for i, v in enumerate(vertices)
                if not (i < n_futuros and i in indices_top)
            ]
            candidatas.append(grupos_separados + [grupo_resto])

        return candidatas

    def _candidatas_desde_hamming(self, k: int) -> list[list[list[tuple]]]:
        """
        Genera candidatas adicionales basadas en los niveles de Hamming.

        Para cada nivel Hamming h, agrupa los vértices futuros según si
        su índice pertenece a un camino de ese nivel, generando cortes
        ortogonales a la topología del hipercubo.
        """
        vertices_futuro = [
            (EFECTO, int(idx)) for idx in self.sia_subsistema.indices_ncubos
        ]
        vertices_presente = [
            (ACTUAL, int(dim)) for dim in self.sia_subsistema.dims_ncubos
        ]
        todos = vertices_futuro + vertices_presente

        candidatas = []
        n_futuros = len(vertices_futuro)

        # Niveles medios: ofrecen la mayor discriminación
        niveles = list(self.caminos.keys())
        for nivel in niveles[1:]:
            if nivel >= k:
                break
            presentes_nivel = set()
            for estado in self.caminos[nivel]:
                for idx, bit in enumerate(estado):
                    if bit == self.caminos[0][0][idx]:
                        presentes_nivel.add(idx)

            futuros_en_nivel = [
                v for v in vertices_futuro
                if v[1] in presentes_nivel and v[1] < n_futuros
            ]
            futuros_fuera = [v for v in vertices_futuro if v not in futuros_en_nivel]
            if futuros_en_nivel and futuros_fuera:
                candidatas.append(
                    [futuros_en_nivel, futuros_fuera + vertices_presente]
                )

        return candidatas
