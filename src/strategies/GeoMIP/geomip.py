import time
from typing import Dict, List

import numpy as np

from src.constants.base import ACTUAL, EFECTO, FLOAT_ZERO
from src.constants.models import GEOMETRIC_LABEL
from src.funcs.format import fmt_biparte_q, fmt_parts
from src.funcs.iit import emd_efecto
from src.models.base.sia import SIA
from src.models.core.solution import Solution


class GeoMIP(SIA, nombre="geo"):
    def __init__(self, subsistema_o_tpm):
        super().__init__(subsistema_o_tpm)
        self.tabla_transiciones: dict = {}
        self.vertices: set[tuple]
        self.memoria_particiones: dict[tuple[int, int], tuple[float, float]] = {}

    def resolver(self) -> Solution:
        t0 = time.perf_counter()
        dm_original = self.sia_dists_marginales

        indices = self.sia_subsistema.indices_ncubos
        dims = self.sia_subsistema.dims_ncubos

        if not len(indices) or not len(dims):
            return Solution(
                estrategia=GEOMETRIC_LABEL,
                perdida=FLOAT_ZERO,
                distribucion_subsistema=dm_original,
                distribucion_particion=dm_original,
                particion=fmt_parts(((), ()), ((), ())).strip(),
                tiempo_total=time.perf_counter() - t0,
                quiere_hablar=False,
            )

        futuro = tuple((EFECTO, efecto) for efecto in indices)
        presente = tuple((ACTUAL, actual) for actual in dims)

        self._flat_data = [ncubo.data.ravel() for ncubo in self.sia_subsistema.ncubos]
        self.vertices = set(presente + futuro)
        self.estado_inicial = self.sia_subsistema.estado_inicial[dims]
        self.estado_final = 1 - self.estado_inicial

        mip = self.find_mip()
        fmt_mip = fmt_biparte_q(list(mip), self.nodes_complement(mip)).strip()

        return Solution(
            estrategia=GEOMETRIC_LABEL,
            perdida=self.memoria_particiones[mip][0],
            distribucion_subsistema=dm_original,
            distribucion_particion=self.memoria_particiones[mip][1],
            particion=fmt_mip,
            tiempo_total=time.perf_counter() - t0,
            quiere_hablar=False,
        )

    def nodes_complement(self, nodes: list[tuple[int, int]]):
        return list(set(self.vertices) - set(nodes))

    def find_mip(self):
        """
        Implementa el algoritmo para encontrar la bipartición óptima
        utilizando el enfoque geométrico-topológico.
        """
        self.sia_logger.critic("empieza.")
        estado_inicial = self.estado_inicial
        estado_final = self.estado_final
        self.idx_ncubos = list(range(len(self.sia_subsistema.indices_ncubos)))
        self.caminos: Dict[int, List[List[int]]] = {0: [estado_inicial.tolist()]}
        self.tabla_transiciones[tuple(self.caminos[0][0]),tuple(self.caminos[0][0])] = [0.0 for _ in range(len(self.sia_subsistema.indices_ncubos))]
        for nivel in range(1, len(estado_inicial)+1):
            self.calcular_costos_nivel(estado_final,nivel)
        candidatos = self.identificar_particiones_optimas()
        for idx, (presentes, futuros) in enumerate(candidatos):
            presentes = self.sia_subsistema.dims_ncubos[presentes]
            futuros = self.sia_subsistema.indices_ncubos[futuros]
            dist =self.sia_subsistema.bipartir(futuros,presentes).distribucion_marginal()
            emd = emd_efecto(dist, self.sia_dists_marginales)
            key = [(0,nodo) for nodo in presentes]
            key.extend([(1,nodo) for nodo in futuros])
            # print(fmt_biparte_q(list(key), self.nodes_complement(key)))
            self.memoria_particiones[tuple(key)] = (emd, dist)
        return min(
            self.memoria_particiones, key=lambda k: self.memoria_particiones[k][0]
        )

    def calcular_costos_nivel(self,estado_final: np.ndarray, nivel):
        n = len(estado_final)
        visitados:set[tuple] = set()
        self.caminos[nivel] = []
        for estado_anterior in self.caminos[nivel - 1]:
            estado_actual = np.array(estado_anterior)
            for i in range(n):
                if estado_actual[i] != estado_final[i]:
                    nuevo_estado = estado_actual.copy()
                    nuevo_estado[i] = estado_final[i]
                    nuevo_estado_tuple = tuple(nuevo_estado)
                    if nuevo_estado_tuple not in visitados:
                        self.caminos[nivel].append(nuevo_estado.tolist())
                        self.calcular_costo(self.caminos[0][0],nuevo_estado.tolist(),self.idx_ncubos)
                        visitados.add(nuevo_estado_tuple)

    def calcular_costo(self, estado_inicial:tuple, estado_final:tuple, ncubos:list[int]):
        """
            Funcion encargada de calcular el costo de transicion de transicion del estado inicial al estado final
            para las variables futuras definidas en ncubos
            aplica la funcion de costo tx(i,j)= y(|X[i]-X[j]|+ sum(tx(k,j)))
            donde:
                - y es el factor de decrecimiento 1/2^(dh(i,j))
                - dh(i,j) es la distancia hamming entre i y j
                - X[i] es el valor de probabilida de transicion de un estado para cada variable futura
                - sum(tx(i,k)) son todos costos de transicion de los vecinos de j que estan en un
                  camino optimo desde i
        """
        key = tuple(estado_inicial), tuple(estado_final)
        if key not in self.tabla_transiciones:
            self.tabla_transiciones[key] = [None]*len(self.sia_subsistema.indices_ncubos)
        distancia_hamming = self.hamming(estado_inicial, estado_final)
        factor = 1/(2**distancia_hamming)

        estado_ini_int = int("".join(map(str, estado_inicial[::-1])), 2)
        estado_fin_int = int("".join(map(str, estado_final[::-1])), 2)

        # Con eso, cada flat_data[idx][...] ya te da directamente X[i] o X[j].
        diffs = np.abs(
            np.array([flat[estado_ini_int] for flat in self._flat_data])
        - np.array([flat[estado_fin_int] for flat in self._flat_data])
        )
        self.tabla_transiciones[key] = diffs.tolist()

        if distancia_hamming > 1:
            for i in range(len(estado_inicial)):
                if estado_inicial[i] != estado_final[i]:
                    nuevo_estado = estado_final.copy()
                    nuevo_estado[i] = estado_inicial[i]
                    nuevo_estado_tuple = tuple(nuevo_estado)
                    temp_key = tuple(estado_inicial), nuevo_estado_tuple
                    for n in ncubos:
                        self.tabla_transiciones[key][n] = self.tabla_transiciones[key][n] + self.tabla_transiciones[temp_key][n]
        tmp =[]
        for i,n in enumerate(self.tabla_transiciones[key]):
            if n is not None:
                tmp.append(factor * n)
            else:
                tmp.append(n)
        self.tabla_transiciones[key] = tmp

    def identificar_particiones_optimas(self):
        """
        Identifica las particiones óptimas basadas en los costos de transición
        y las distancias Hamming entre los estados.
        """
        key = tuple(self.caminos[0][0]), tuple(self.estado_final)
        costos: list = self.tabla_transiciones[key]
        candidatos = []
        n_vars = len(costos)
        for idx in range(n_vars):
            presentes = [i for i in range(len(self.estado_final))]
            futuros = [i for i in range(n_vars) if i != idx]
            candidatos.append([presentes, futuros])
        es_par = len(self.caminos) % 2 == 0
        if es_par:
            mitad = len(self.caminos) // 2
        else:
            mitad = (len(self.caminos) // 2) + 1
        for nivel in range(1,mitad):
            costo_candidato_nivel = 1e5
            presentes_nivel = []
            futuros_nivel = []
            for estado in self.caminos[nivel]:
                costo_candidato = 0
                presentes = []
                futuros = []
                actual = self.tabla_transiciones.get((tuple(self.caminos[0][0]), tuple(estado)), None)
                estado_complementario = (1-np.array(estado)).tolist()
                complementario = self.tabla_transiciones.get((tuple(self.caminos[0][0]), tuple(estado_complementario)), None)
                for idx,i in enumerate(estado):
                    if i == self.caminos[0][0][idx]:
                        presentes.append(idx)
                for idx,_ in enumerate(self.idx_ncubos):
                    if actual[idx] <= complementario[idx]:
                        futuros.append(idx)
                        costo_candidato += actual[idx]
                    else:
                        costo_candidato += complementario[idx]
                if costo_candidato < costo_candidato_nivel:
                    costo_candidato_nivel = costo_candidato
                    presentes_nivel = presentes
                    futuros_nivel = futuros
            candidatos.append([presentes_nivel, futuros_nivel])
        return candidatos

    def hamming(self,a: List[int], b: List[int]) -> int:
        return sum(x != y for x, y in zip(a, b))
