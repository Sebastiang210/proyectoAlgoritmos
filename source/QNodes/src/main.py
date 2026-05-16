import multiprocessing
import os
import re
from pathlib import Path

import numpy as np
import pandas as pd

from src.controllers.manager import Manager
from src.strategies.q_nodes import QNodes

# parents[0] = src/, parents[1] = QNodes/
QNODES_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = Path(__file__).resolve().parent

# Mapa: n_nodos -> índice de hoja en Pruebas_Metodo2.xlsx
# 0=3el, 1=4el, 2=5el, 3=6el, 4=8el, 5=10el, 6=12el, 7=15el, 8=20el
_SHEET_POR_NODOS: dict[int, int] = {
    3: 0, 4: 1, 5: 2, 6: 3, 8: 4, 10: 5, 12: 6, 15: 7, 20: 8
}

# Extrae solo letras A-T de cada lado del pipe, ignorando sufijos como _{t+1}
_RE_LETRAS = re.compile(r"[A-T]+")


def convertir_a_binario(texto: str, n_bits: int = 20) -> str:
    """Convierte letras (ej: 'ABC') a cadena binaria de n_bits (ej: '11100...')."""
    posiciones = "ABCDEFGHIJKLMNOPQRST"[:n_bits]
    binario = ["0"] * n_bits
    for letra in texto:
        if letra in posiciones:
            binario[posiciones.index(letra)] = "1"
    return "".join(binario)


def parsear_subsistema(fila: str, n_bits: int) -> tuple[str, str] | None:
    """
    Parsea una celda con formato 'ALCANCE_{t+1}|MECANISMO_{t}' (o 'Alc|Mec').
    Extrae solo las letras A-T de cada lado y las convierte a binario.
    Devuelve (alcance_bin, mecanismo_bin) o None si el formato no es válido.
    """
    partes = str(fila).split("|")
    if len(partes) != 2:
        return None
    letras_alc = "".join(_RE_LETRAS.findall(partes[0]))
    letras_mec = "".join(_RE_LETRAS.findall(partes[1]))
    if not letras_alc or not letras_mec:
        return None
    return (
        convertir_a_binario(letras_alc, n_bits),
        convertir_a_binario(letras_mec, n_bits),
    )


def resolver_tpm_path(estado_inicio: str) -> Path:
    """Busca el archivo TPM correspondiente al tamaño del estado inicial."""
    sample_name = f"N{len(estado_inicio)}A.csv"
    candidates = (
        SRC_ROOT / ".samples" / sample_name,
        QNODES_ROOT / "data" / "samples" / sample_name,
    )
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise FileNotFoundError(
        f"No se encontró la TPM '{sample_name}'. "
        f"Busqué en: {', '.join(str(c) for c in candidates)}"
    )


def inferir_estado_inicial() -> str:
    """Infiere el estado inicial a partir de los CSVs disponibles en .samples/."""
    sample_dir = SRC_ROOT / ".samples"
    pattern = re.compile(r"N(\d+)[A-Z]\.csv$")
    available_sizes = []

    if sample_dir.exists():
        for sample_file in sample_dir.glob("N*.csv"):
            match = pattern.match(sample_file.name)
            if match:
                available_sizes.append(int(match.group(1)))

    if not available_sizes:
        raise FileNotFoundError("No hay archivos TPM disponibles en src/.samples/")

    n_bits = max(available_sizes)
    return "1" + ("0" * (n_bits - 1))


def _ejecutar_qnodes_proceso(
    estado_inicio: str,
    condiciones: str,
    alcance: str,
    mecanismo: str,
    tpm: np.ndarray,
    resultado_queue: multiprocessing.Queue,
) -> None:
    """Función target para proceso hijo: ejecuta QNodes y deposita resultado."""
    try:
        analizador = QNodes(tpm)
        solucion = analizador.aplicar_estrategia(
            estado_inicio, condiciones, alcance, mecanismo
        )
        resultado_queue.put({
            "particion": solucion.particion,
            "perdida": str(solucion.perdida).replace(".", ","),
            "tiempo": str(solucion.tiempo_ejecucion).replace(".", ","),
        })
    except Exception as exc:
        resultado_queue.put({
            "particion": None,
            "perdida": None,
            "tiempo": None,
            "error": str(exc),
        })


def ejecutar_desde_excel(
    ruta_excel: Path,
    ruta_salida: Path,
    inicio: int = 0,
    cantidad: int = 50,
    estado_inicio: str | None = None,
    condiciones: str | None = None,
    timeout: int = 3600,
    sheet_name: int | None = None,
) -> None:
    """
    Análogo a GeoMIP: lee Pruebas_Metodo2.xlsx, ejecuta QNodes por cada
    subsistema y guarda resultados en Excel.

    sheet_name: índice de hoja (0-based). Si es None, se infiere a partir
    del tamaño del estado inicial usando _SHEET_POR_NODOS.
    """
    estado_inicio = estado_inicio or inferir_estado_inicial()
    condiciones   = condiciones or ("1" * len(estado_inicio))
    n_bits = len(estado_inicio)

    if sheet_name is None:
        if n_bits not in _SHEET_POR_NODOS:
            raise ValueError(
                f"No hay hoja definida para N={n_bits} nodos. "
                f"Hojas disponibles: {sorted(_SHEET_POR_NODOS)}"
            )
        sheet_name = _SHEET_POR_NODOS[n_bits]

    df = pd.read_excel(
        ruta_excel, sheet_name=sheet_name, usecols="B", skiprows=3,
        names=["Subsistema"]
    )
    filas = df["Subsistema"].dropna().tolist()
    filas = filas[inicio: inicio + cantidad]

    tpm_path = resolver_tpm_path(estado_inicio)
    tpm = np.genfromtxt(tpm_path, delimiter=",")
    print(f"TPM: {tpm_path}  |  N={n_bits} nodos  |  hoja={sheet_name}  |  filas={len(filas)}")

    resultados = []

    for i, fila in enumerate(filas, start=inicio + 1):
        parsed = parsear_subsistema(fila, n_bits)
        if parsed is None:
            print(f"Iteración {i} - Formato inválido, saltando: {fila!r}")
            continue

        alcance, mecanismo = parsed
        print(f"Iteración {i} - Alcance: {alcance}, Mecanismo: {mecanismo}")

        resultado_queue: multiprocessing.Queue = multiprocessing.Queue()
        proceso = multiprocessing.Process(
            target=_ejecutar_qnodes_proceso,
            args=(estado_inicio, condiciones, alcance, mecanismo, tpm, resultado_queue),
        )

        proceso.start()
        proceso.join(timeout=timeout)

        if proceso.is_alive():
            print(f"Iteración {i} - Tiempo límite alcanzado, terminando proceso...")
            proceso.terminate()
            proceso.join()
            resultado = {"perdida": None, "tiempo": None, "particion": None}
        else:
            resultado = (
                resultado_queue.get()
                if not resultado_queue.empty()
                else {"perdida": None, "tiempo": None, "particion": None}
            )

        resultados.append({
            "Iteración": i,
            "Alcance": alcance,
            "Mecanismo": mecanismo,
            "Partición": resultado.get("particion"),
            "Pérdida": resultado.get("perdida"),
            "Tiempo de ejecución (s)": resultado.get("tiempo"),
        })

    df_resultados = pd.DataFrame(resultados)
    ruta_salida.parent.mkdir(parents=True, exist_ok=True)
    df_resultados.to_excel(ruta_salida, index=False)
    print(f"Resultados guardados en {ruta_salida}")


def iniciar() -> None:
    """Punto de entrada: modo directo (un solo subsistema hardcodeado)."""
    estado_inicial = "1000"
    condiciones =    "1110"
    alcance =        "1110"
    mecanismo =      "1110"

    gestor_redes = Manager(estado_inicial)
    tpm = gestor_redes.cargar_red()

    analizador_q = QNodes(tpm)
    solucion = analizador_q.aplicar_estrategia(
        estado_inicial,
        condiciones,
        alcance,
        mecanismo,
    )
    print(solucion)


def iniciar_desde_excel() -> None:
    """Punto de entrada: modo batch desde Excel (análogo a GeoMIP)."""
    ruta_entrada = Path(
        os.getenv(
            "QNODES_INPUT_XLSX",
            # Por defecto reutiliza el xlsx compartido de GeoMIP
            str(QNODES_ROOT.parent / "GeoMIP" / "results" / "Pruebas_Metodo2.xlsx"),
        )
    )
    ruta_salida = Path(
        os.getenv(
            "QNODES_OUTPUT_XLSX",
            str(QNODES_ROOT / "results" / "resultados_QNodes.xlsx"),
        )
    )
    ejecutar_desde_excel(ruta_entrada, ruta_salida)
