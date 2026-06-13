from abc import ABC
import time

import numpy as np
import numpy.typing as NDArray

from src.constants.models import SIA_PREPARATION_TAG
from src.middlewares.slogger import SafeLogger
from src.models.core.system import System

from src.constants.base import (
    COLS_IDX,
    FLOAT_ZERO,
    STR_ZERO,
)
from src.constants.error import (
    ERROR_ESPACIOS_INCOMPATIBLES,
)


class SIA(ABC):
    """Base para todas las estrategias IIT.

    Acepta dos modos de construcción:
    - Nuevo (estrategias optimizadas): SIA(subsistema: System) — subsistema ya
      preparado; expone self.sistema y self.distribucion.
    - Clásico (estrategias legacy): SIA(tpm: np.ndarray) — TPM cruda; usa
      sia_preparar_subsistema() para construir el subsistema.

    Las subclases pueden declarar metadatos como class-keywords:
        class MiEstrategia(SIA, nombre="mi", necesita_mpt=False): ...
    """

    def __init_subclass__(cls, nombre=None, necesita_mpt=False, **kwargs):
        super().__init_subclass__(**kwargs)
        if nombre is not None:
            cls.nombre = nombre
        cls.necesita_mpt = necesita_mpt

    def __init__(self, subsistema_o_tpm) -> None:
        if isinstance(subsistema_o_tpm, System):
            self.sia_subsistema = subsistema_o_tpm
            self.sistema = subsistema_o_tpm
            self.tpm = None
            self.sia_dists_marginales = subsistema_o_tpm.distribucion_marginal()
            self.distribucion = self.sia_dists_marginales
            self.sia_logger = SafeLogger(SIA_PREPARATION_TAG)
            self.sia_tiempo_inicio: float = FLOAT_ZERO
        else:
            self.tpm = subsistema_o_tpm
            self.sia_logger = SafeLogger(SIA_PREPARATION_TAG)
            self.sia_subsistema: System
            self.sia_dists_marginales: NDArray[np.float32]
            self.sia_tiempo_inicio: float = FLOAT_ZERO

    def aplicar_estrategia(self):
        """Implementar en subclases legacy (interface clásica)."""
        raise NotImplementedError

    def resolver(self):
        """Implementar en subclases nuevas (interface optimizada)."""
        raise NotImplementedError

    def sia_preparar_subsistema(
        self,
        estado_inicial: str,
        condicion: str,
        alcance: str,
        mecanismo: str,
    ):
        """Es en este método donde dada la entrada del usuario, vamos a generar un sistema completo, aplicamos condiciones de fondo (background conditions), loe substraemos partes para dejar un subsistema y es este el que retornamos pues este es el mínimo "sistema" útil para poder encontrar la bipartición que le genere la menor pérdida.

        Args:
            - `condicion` (str): Cadena de bits donde los bits en cero serán las dimensiones a condicionar.
            - `alcance` (str): Cadena de bits donde los bits en cero serán las dimensiones a substraer del alcance .
            - `mecanismo` (str): Cadena de bits donde los bits en cero serán las dimensiones a substraer del mecanismo.

        Raises:
            - `Exception:` Es crucial que todos tengan el mismo tamaño del estado inicial para correctamente identificar los índices y valor de cada variable rápidamente.
        """
        if self.chequear_parametros(estado_inicial, condicion, alcance, mecanismo):
            raise Exception(ERROR_ESPACIOS_INCOMPATIBLES)

        dims_condicionadas = np.array(
            [ind for ind, bit in enumerate(condicion) if bit == STR_ZERO], dtype=np.int8
        )
        dims_alcance = np.array(
            [ind for ind, bit in enumerate(alcance) if bit == STR_ZERO], dtype=np.int8
        )
        dims_mecanismo = np.array(
            [ind for ind, bit in enumerate(mecanismo) if bit == STR_ZERO], dtype=np.int8
        )
        dims_estado_inicial = np.array(
            [int(ind) for ind in estado_inicial],
            dtype=np.int8,
        )

        completo = System(self.tpm, dims_estado_inicial)
        # self.sia_logger.critic("Original creado.")
        # self.sia_logger.info(completo)
        # self.sia_logger.critic("Original:")
        # self.sia_logger.info(completo)

        candidato = completo.condicionar(dims_condicionadas)
        self.sia_logger.critic("Sisema Candidato creado.")
        # self.sia_logger.warn(f"{dims_condicionadas}")
        # self.sia_logger.debug(candidato)

        subsistema = candidato.substraer(dims_alcance, dims_mecanismo)
        self.sia_logger.critic("Subsistema creado.")
        # self.sia_logger.debug(f"{dims_alcance, dims_mecanismo=}")
        # self.sia_logger.debug(subsistema)

        self.sia_subsistema = subsistema
        self.sia_dists_marginales = subsistema.distribucion_marginal()
        self.sia_tiempo_inicio = time.time()

    def chequear_parametros(
        self, estado_inicial: str, candidato: str, futuro: str, presente: str
    ):
        """Valida que los datos enviados por el usuario sean correctos, donde no hay problema si tienen la misma longitud puesto se están asignando los valores correspondientes a cada variable.

        Args:
            `candidato` (str): Cadena de texto que representa la presencia o ausencia de un conjunto de variables que serán enviadas para condicionar el sistema original dejándolo como un Sistema candidato, si su bit asociado equivale a 0 se condiciona la variable, si equivale a 1 esta variable se mantendrá en el sistema durante toda la ejecución (hasta que un subsistema la marginalice).
            `futuro` (str): Cadena de texto que representa la presencia o ausencia de un conjunto de variables que serán enviadas para substraer en el alcance del Sistema candidato dejándo un Subsistema, si su bit asociado equivale a 0 la variable será marginalizada, si equivale a 1 la variable se mantendrá en el Sistema candidato durante toda la ejecución (hasta que una partición la marginalice).
            `presente` (str): Cadena de texto que representa la presencia o ausencia de un conjunto de variables que serán enviadas para substraer en el mecanismo del Sistema candidato dejándolo como un Subsistema, si su bit asociado equivale a 0 la variable será marginalizada, si equivale a 1 la variable se mantendrá en el Sistema candidato durante toda la ejecución (hasta que una partición la marginalice).

        Returns:
            bool: True si las dimensiones son diferentes, de otra forma los parámetros enviados son válidos (y depende si existe la red asociada).
        """
        return not (
            len(self.tpm[COLS_IDX])
            == len(estado_inicial)
            == len(candidato)
            == len(futuro)
            == len(presente)
        )
