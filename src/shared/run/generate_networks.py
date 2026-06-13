"""
Genera redes TPM estocásticas (float 0-1) para los tamaños especificados.

Usage:
    uv run python src/shared/run/generate_networks.py
    uv run python src/shared/run/generate_networks.py --sizes 20 21 22 23
"""

import argparse
import time
import numpy as np
from pathlib import Path

import sys
import os

root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, root)

from src.models.base.application import aplicacion
from src.constants.base import ABC_START, COLON_DELIM, CSV_EXTENSION, PATH_SAMPLES


def generar_red(dimensiones: int, semilla: int) -> str | None:
    np.random.seed(semilla)

    num_estados = 1 << dimensiones
    total_size_gb = (num_estados * dimensiones) / (1024**3)

    print(f"  Tamaño estimado: {total_size_gb:.6f} GB")

    base_path = Path(PATH_SAMPLES)
    base_path.mkdir(parents=True, exist_ok=True)

    suffix = ABC_START
    while (base_path / f"N{dimensiones}{suffix}.{CSV_EXTENSION}").exists():
        suffix = chr(ord(suffix) + 1)

    filename = f"N{dimensiones}{suffix}.{CSV_EXTENSION}"
    filepath = base_path / filename

    print(f"  Generando estados...")
    start_time = time.time()
    states = np.random.random(size=(num_estados, dimensiones))
    print(f"  Generación completada en {time.time() - start_time:.2f}s")

    print(f"  Guardando en {filepath}...")
    start_time = time.time()
    np.savetxt(filepath, states, delimiter=COLON_DELIM, fmt="%.6f")

    file_size_gb = os.path.getsize(filepath) / (1024**3)
    print(f"  Guardado: {file_size_gb:.3f} GB en {time.time() - start_time:.2f}s")

    return filename


def main():
    parser = argparse.ArgumentParser(description="Genera redes TPM estocásticas")
    parser.add_argument(
        "--sizes",
        nargs="+",
        type=int,
        default=[20, 21, 22, 23],
        help="Tamaños de red a generar (default: 20 21 22 23)",
    )
    args = parser.parse_args()

    semilla = aplicacion.semilla_numpy
    print(f"Semilla numpy: {semilla}\n")

    for n in args.sizes:
        print(f"=== Generando N{n}A ===")
        generar_red(n, semilla)
        print()

    print("Redes generadas:")
    for n in args.sizes:
        path = Path(PATH_SAMPLES) / f"N{n}A.csv"
        if path.exists():
            size_mb = path.stat().st_size / (1024**2)
            print(f"  N{n}A.csv: {size_mb:.1f} MB")


if __name__ == "__main__":
    main()
