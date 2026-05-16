import sys
from src.models.base.application import aplicacion
from src.main import iniciar, iniciar_desde_excel


def main():
    """
    Inicialización del aplicativo QNodes.

    Modos de uso:
      uv run exec.py            → modo directo (un subsistema hardcodeado)
      uv run exec.py --excel    → modo batch desde Pruebas_Metodo2.xlsx
    """
    aplicacion.activar_profiling()
    aplicacion.set_pagina_red_muestra("A")

    if "--excel" in sys.argv:
        iniciar_desde_excel()
    else:
        iniciar()


if __name__ == "__main__":
    main()
