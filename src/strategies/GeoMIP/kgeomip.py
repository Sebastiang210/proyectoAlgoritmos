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

Loss computation: EMD(combined_dist, original_dist) donde combined_dist es
el promedio de las distribuciones marginales de cada grupo.
"""

import time
from itertools import combinations
from math import comb

import numpy as np

from src.constants.base import ACTUAL, EFECTO
from src.strategies.GeoMIP.geomip import GeoMIP
from src.funcs.format import fmt_biparte_q, fmt_kparticion_kqnodes
from src.funcs.iit import emd_efecto
from src.middlewares.slogger import SafeLogger
from src.models.core.solution import Solution

KGEOMIP_LABEL = "KGeoMIP"
KGEOMIP_TAG = f"{KGEOMIP_LABEL}_strategy"

_PRESUPUESTO_EVALUACIONES = 10_000
_K_TOPE_DEFAULT = 8


def _stirling2(n: int, k: int) -> int:
    """Número de Stirling de segundo tipo S(n, k): particiones de n en k partes."""
    if k == 0:
        return 1 if n == 0 else 0
    if k > n:
        return 0
    total = sum(((-1) ** (k - j)) * comb(k, j) * (j**n) for j in range(k + 1))
    factorial_k = 1
    for i in range(2, k + 1):
        factorial_k *= i
    return total // factorial_k


def _generar_particiones(
    vertices: list[tuple[int, int]], k: int
) -> list[list[list[tuple[int, int]]]]:
    """Genera todas las particiones de n vertices en k grupos no vacíos.

    Returns:
        Lista de k-particiones, cada partición es una lista de k grupos,
        donde cada grupo es una lista de vértices (tiempo, idx).
    """
    n = len(vertices)
    if k == 1:
        return [[list(vertices)]]
    if k == n:
        return [[[v] for v in vertices]]

    resultado = []

    def recursiva(idx: int, grupos: list[list[tuple[int, int]]]):
        if idx == n:
            if len(grupos) == k:
                resultado.append([list(g) for g in grupos])
            return
        for g_idx in range(len(grupos)):
            grupos[g_idx].append(vertices[idx])
            recursiva(idx + 1, grupos)
            grupos[g_idx].pop()
        if len(grupos) < k:
            grupos.append([vertices[idx]])
            recursiva(idx + 1, grupos)
            grupos.pop()

    recursiva(0, [])
    return resultado


class KGeoMIP(GeoMIP):
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
        gestor,
        k: int = 2,
        k_tope: int = _K_TOPE_DEFAULT,
        presupuesto: int = _PRESUPUESTO_EVALUACIONES,
    ):
        super().__init__(gestor)
        self.k = k
        self.k_tope = k_tope
        self.presupuesto = presupuesto
        self.logger = SafeLogger(KGEOMIP_TAG)
        self.memoria_kparticiones: dict[tuple, tuple[float, np.ndarray]] = {}

    def _preparar_geometria(
        self,
        condicion: str,
        alcance: str,
        mecanismo: str,
        tpm: np.ndarray,
    ) -> None:
        """Construye el subsistema y la tabla de costos geométrica."""
        if self.tpm is not None:
            self.sia_preparar_subsistema(condicion, alcance, mecanismo, tpm)
        elif not hasattr(self, 'caminos') or not self.caminos:
            raise ValueError("Geometría no preparada. Pasar TPM o llamar con geometría ya disponible.")
        futuro = tuple(
            (EFECTO, int(idx)) for idx in self.sia_subsistema.indices_ncubos
        )
        presente = tuple(
            (ACTUAL, int(dim)) for dim in self.sia_subsistema.dims_ncubos
        )
        self._flat_data = [ncubo.data.ravel() for ncubo in self.sia_subsistema.ncubos]
        self.vertices = set(presente + futuro)
        dims = self.sia_subsistema.dims_ncubos
        self.estado_inicial = self.sia_subsistema.estado_inicial[dims]
        self.estado_final = 1 - self.estado_inicial
        self.idx_ncubos = list(range(len(self.sia_subsistema.indices_ncubos)))
        self.tabla_transiciones.clear()
        self.caminos = {0: [self.estado_inicial.tolist()]}
        self.tabla_transiciones[
            tuple(self.caminos[0][0]), tuple(self.caminos[0][0])
        ] = [0.0] * len(self.sia_subsistema.indices_ncubos)
        for nivel in range(1, len(self.estado_inicial) + 1):
            self.calcular_costos_nivel(self.estado_final, nivel)

    def _setup_geometria(self) -> None:
        """Configura la geometría del hipercubo si no está ya configurada."""
        futuro = tuple(
            (EFECTO, int(idx)) for idx in self.sia_subsistema.indices_ncubos
        )
        presente = tuple(
            (ACTUAL, int(dim)) for dim in self.sia_subsistema.dims_ncubos
        )
        self._flat_data = [ncubo.data.ravel() for ncubo in self.sia_subsistema.ncubos]
        self.vertices = set(presente + futuro)
        dims = self.sia_subsistema.dims_ncubos
        self.estado_inicial = self.sia_subsistema.estado_inicial[dims]
        self.estado_final = 1 - self.estado_inicial
        self.idx_ncubos = list(range(len(self.sia_subsistema.indices_ncubos)))
        self.tabla_transiciones.clear()
        self.caminos = {0: [self.estado_inicial.tolist()]}
        self.tabla_transiciones[
            tuple(self.caminos[0][0]), tuple(self.caminos[0][0])
        ] = [0.0] * len(self.sia_subsistema.indices_ncubos)
        for nivel in range(1, len(self.estado_inicial) + 1):
            self.calcular_costos_nivel(self.estado_final, nivel)

    def ejecutar_k(self, k: int) -> Solution:
        """Corre find_kmip para k dado asumiendo geometría ya preparada."""
        self.k = k
        self.memoria_kparticiones = {}
        if not hasattr(self, 'caminos') or not self.caminos:
            self._setup_geometria()

        if k == 2:
            from src.strategies.GeoMIP.geomip import GeoMIP
            geo = GeoMIP(self.sia_subsistema)
            geo_result = geo.resolver()
            return Solution(
                estrategia=KGEOMIP_LABEL,
                perdida=geo_result.perdida,
                distribucion_subsistema=geo_result.distribucion_subsistema,
                distribucion_particion=geo_result.distribucion_particion,
                tiempo_total=time.time() - self.sia_tiempo_inicio,
                particion=geo_result.particion,
            )

        mejor_particion = self.find_kmip()
        clave = self._particion_to_key(mejor_particion)
        perdida, dist = self.memoria_kparticiones[clave]

        fmt_mip = fmt_kparticion_kqnodes(mejor_particion)

        return Solution(
            estrategia=KGEOMIP_LABEL,
            perdida=perdida,
            distribucion_subsistema=self.sia_dists_marginales,
            distribucion_particion=dist,
            tiempo_total=time.time() - self.sia_tiempo_inicio,
            particion=fmt_mip,
        )

    def aplicar_estrategia(
        self,
        condicion: str,
        alcance: str,
        mecanismo: str,
        tpm: np.ndarray,
        k: int | None = None,
    ) -> Solution:
        """Prepara la geometría y busca la k-MIP."""
        if k is not None:
            self.k = k
        self._preparar_geometria(condicion, alcance, mecanismo, tpm)
        return self.ejecutar_k(self.k)

    def find_kmip(self) -> list[list[tuple[int, int]]]:
        """
        Encuentra la k-partición del conjunto de vértices con menor EMD.

        Returns:
            La mejor k-partición (lista de k grupos, cada grupo es lista de vértices).
        """
        self.logger.critic(f"find_kmip: k={self.k}")
        candidatas = self.generar_k_particiones_candidatas(self.k)
        self.logger.critic(f"  Candidatas generadas: {len(candidatas)}")

        for particion in candidatas:
            self._evaluar_k_particion(particion)

        if not self.memoria_kparticiones:
            self.logger.critic("Sin particiones válidas, fallback a bipartición.")
            return self._biparticion_fallback()

        mejor_key = min(
            self.memoria_kparticiones,
            key=lambda k: self.memoria_kparticiones[k][0],
        )
        return self._key_to_particion(mejor_key)

    def _evaluar_k_particion(self, particion: list[list[tuple[int, int]]]) -> None:
        """
        Evalúa la EMD de una k-partición completa.

        Para k=2, usa la misma pérdida que GEO: EMD(bipartir(futuros, presentes), original).
        Para k>2, usa promedio de distribuciones marginales por grupo.
        """
        n_grupos = len(particion)

        if n_grupos == 2:
            grupo0 = particion[0]
            grupo1 = particion[1]

            futuros0 = [idx for t, idx in grupo0 if t == EFECTO]
            presentes0 = [idx for t, idx in grupo0 if t == ACTUAL]
            futuros1 = [idx for t, idx in grupo1 if t == EFECTO]
            presentes1 = [idx for t, idx in grupo1 if t == ACTUAL]

            all_futuros = set(futuros0 + futuros1)
            all_presentes = set(presentes0 + presentes1)

            if all_futuros and all_presentes:
                dist = self.sia_subsistema.bipartir(
                    np.array(list(all_futuros), dtype=np.int8),
                    np.array(list(all_presentes), dtype=np.int8)
                ).distribucion_marginal()
                emd = emd_efecto(dist, self.sia_dists_marginales)
            else:
                emd = float('inf')
                dist = np.zeros(len(self.sia_dists_marginales), dtype=np.float32)
        else:
            dists_grupo = []
            for grupo in particion:
                futuros_grupo = [idx for t, idx in grupo if t == EFECTO]
                presentes_grupo = [idx for t, idx in grupo if t == ACTUAL]

                if not futuros_grupo:
                    dists_grupo.append(np.zeros(len(self.sia_dists_marginales), dtype=np.float32))
                    continue

                try:
                    futuros_arr = np.array(futuros_grupo, dtype=np.int8)
                    presentes_arr = np.array(presentes_grupo, dtype=np.int8)
                    particion_sys = self.sia_subsistema.bipartir(futuros_arr, presentes_arr)
                    dists_grupo.append(particion_sys.distribucion_marginal())
                except Exception:
                    dists_grupo.append(np.zeros(len(self.sia_dists_marginales), dtype=np.float32))

            if not dists_grupo:
                return

            combined_dist = np.mean(dists_grupo, axis=0)
            emd = emd_efecto(combined_dist, self.sia_dists_marginales)
            dist = combined_dist

        clave = self._particion_to_key(particion)
        self.memoria_kparticiones[clave] = (emd, dist)

    def _particion_to_key(self, particion: list[list[tuple[int, int]]]) -> tuple:
        """Convierte partición a clave hashable para memoria."""
        resultado = []
        for g in particion:
            ordenado = tuple(sorted(g, key=lambda x: (x[0], x[1])))
            resultado.append(ordenado)
        return tuple(resultado)

    def _key_to_particion(self, key: tuple) -> list[list[tuple[int, int]]]:
        """Convierte clave hashable de vuelta a partición."""
        return [list(g) for g in key]

    def _biparticion_fallback(self) -> list[list[tuple[int, int]]]:
        """Fallback a bipartición cuando no hay candidatas válidas."""
        futuro = [(EFECTO, int(idx)) for idx in self.sia_subsistema.indices_ncubos]
        presente = [(ACTUAL, int(dim)) for dim in self.sia_subsistema.dims_ncubos]
        todos = futuro + presente
        mejor = None
        mejor_loss = float("inf")

        for idx in range(len(futuro)):
            sep = [futuro[idx]]
            resto = [v for v in todos if v != futuro[idx]]
            particion = [sep, resto]
            self._evaluar_k_particion(particion)
            key = self._particion_to_key(particion)
            if key in self.memoria_kparticiones:
                loss = self.memoria_kparticiones[key][0]
                if loss < mejor_loss:
                    mejor_loss = loss
                    mejor = particion

        return mejor if mejor else [presente, futuro]

    def generar_k_particiones_candidatas(
        self, k: int
    ) -> list[list[list[tuple[int, int]]]]:
        """
        Genera candidatas a k-partición del conjunto de vértices.

        Returns:
            Lista de k-particiones; cada partición es lista de k grupos,
            cada grupo es lista de vértices (tiempo, idx).
        """
        futuro = [(EFECTO, int(idx)) for idx in self.sia_subsistema.indices_ncubos]
        presente = [(ACTUAL, int(dim)) for dim in self.sia_subsistema.dims_ncubos]
        vertices = futuro + presente
        n_futuros = len(futuro)
        n_vertices = len(vertices)

        if k <= 1:
            return [[vertices]]
        if k >= n_vertices:
            return [[[v] for v in vertices]]

        s_nk = _stirling2(n_vertices, k)
        modo_heuristico = s_nk > self.presupuesto
        self.logger.critic(
            f"  S({n_vertices},{k})={s_nk} "
            f"{'[HEURÍSTICO]' if modo_heuristico else '[EXACTO]'}"
        )

        candidatas = []

        if modo_heuristico:
            candidatas = self._candidatas_heuristicas(k, futuro, presente)
        else:
            candidatas = self._candidatas_exactas(k, futuro, presente)

        if not candidatas:
            candidatas = [[vertices]]

        return candidatas

    def _candidatas_exactas(
        self, k: int, futuro: list, presente: list
    ) -> list[list[list[tuple[int, int]]]]:
        """Genera candidatas en modo exacto (exhaustivo + geométricas)."""
        futuro_completo = list(futuro)
        presente_completo = list(presente)
        vertices = futuro_completo + presente_completo
        n_futuros = len(futuro_completo)

        candidatas = []

        if k == 2:
            n_futuros = len(futuro_completo)
            for r in range(1, n_futuros // 2 + 1):
                for subset in combinations(range(n_futuros), r):
                    grupo_a = [futuro_completo[i] for i in subset] + presente_completo
                    resto = [futuro_completo[i] for i in range(n_futuros) if i not in subset]
                    grupo_b = resto + presente_completo
                    if grupo_a and grupo_b:
                        candidatas.append([grupo_a, grupo_b])
        else:
            for indices_sep in combinations(range(n_futuros), min(k - 1, n_futuros)):
                grupos_sep = [[futuro_completo[i]] for i in indices_sep]
                resto_futuros = [futuro_completo[i] for i in range(n_futuros) if i not in indices_sep]
                grupo_resto = resto_futuros + presente_completo
                grupos_sep.append(grupo_resto)
                if len(grupos_sep) == k:
                    candidatas.append(grupos_sep)

        candidatas_hamming = self._candidatas_desde_hamming(k, futuro_completo, presente_completo)
        candidatas.extend(candidatas_hamming)

        if k > 2 and _stirling2(len(vertices), k) <= self.presupuesto:
            candidatas_exhaustivas = _generar_particiones(vertices, k)
            candidatas.extend(candidatas_exhaustivas)

        return self._deduplicar_candidatas(candidatas)

    def _candidatas_heuristicas(
        self, k: int, futuro: list, presente: list
    ) -> list[list[list[tuple[int, int]]]]:
        """Genera candidatas en modo heurístico (solo geométricas)."""
        futuro_completo = list(futuro)
        presente_completo = list(presente)
        n_futuros = len(futuro_completo)

        if k == 2:
            candidatas = []
            for idx in range(n_futuros):
                grupo_sep = [futuro_completo[idx]]
                grupo_resto = [v for i, v in enumerate(futuro_completo) if i != idx] + presente_completo
                candidatas.append([grupo_sep, grupo_resto])
        else:
            candidatas = []
            for indices_sep in combinations(range(n_futuros), min(k - 1, n_futuros)):
                grupos_sep = [[futuro_completo[i]] for i in indices_sep]
                resto_futuros = [futuro_completo[i] for i in range(n_futuros) if i not in indices_sep]
                grupo_resto = resto_futuros + presente_completo
                grupos_sep.append(grupo_resto)
                if len(grupos_sep) == k:
                    candidatas.append(grupos_sep)

        candidatas_hamming = self._candidatas_desde_hamming(k, futuro_completo, presente_completo)
        candidatas.extend(candidatas_hamming)

        return self._deduplicar_candidatas(candidatas)

    def _candidatas_desde_hamming(
        self, k: int, futuro: list, presente: list
    ) -> list[list[list[tuple[int, int]]]]:
        """Genera candidatas basadas en niveles de Hamming."""
        n_futuros = len(futuro)
        candidatas = []

        niveles = list(self.caminos.keys())
        for nivel in niveles[1:]:
            if nivel >= k:
                break
            presentes_nivel = set()
            for estado in self.caminos[nivel]:
                for idx, bit in enumerate(estado):
                    if bit == self.caminos[0][0][idx]:
                        presentes_nivel.add(idx)

            futuros_en_nivel = [futuro[i] for i in range(n_futuros) if i in presentes_nivel]
            futuros_fuera = [futuro[i] for i in range(n_futuros) if i not in presentes_nivel]

            if futuros_en_nivel and futuros_fuera:
                if k == 2:
                    candidatas.append([futuros_en_nivel, futuros_fuera + presente])
                elif len(futuros_en_nivel) + 1 == k:
                    grupos = [[f] for f in futuros_en_nivel]
                    grupos.append(futuros_fuera + presente)
                    if len(grupos) == k:
                        candidatas.append(grupos)

        return candidatas

    def _deduplicar_candidatas(
        self, candidatas: list[list[list[tuple[int, int]]]]
    ) -> list[list[list[tuple[int, int]]]]:
        """Dedupes candidates while preserving tuple structure."""
        vistas: set[tuple] = set()
        resultado = []
        for candidata in candidatas:
            clave = tuple(tuple(sorted(g, key=lambda x: (x[0], x[1]))) for g in candidata)
            if clave not in vistas:
                vistas.add(clave)
                resultado.append([list(g) for g in clave])
        return resultado