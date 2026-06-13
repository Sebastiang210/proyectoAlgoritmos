from src.funcs.iit import ABECEDARY, LOWER_ABECEDARY
from src.constants.base import BASE_TWO, COLON_DELIM, VOID_STR
from typing import Union

'''
Métodos para formatear particiones resultantes de estrategias específicas.
Este fichero tiene el objetivo de hacer estándar y presentable la salida de resultados al hallarse una bipartición. Es importante aclarar cómo aunque cada función puede ser reutilizada para un nuevo algoritmo si se adaptan sus argumentos, es preferible crear una nueva función si se aprecia mayor dificultad en dicha adaptación.
'''

def fmt_biparticion_fuerza_bruta(
    parte_uno: list[tuple[int, ...], tuple[int, ...]],
    parte_dos: list[tuple[int, ...], tuple[int, ...]],
) -> str:
    '''
    Formatea una bipartición de una estrategia de fuerza bruta.

    Args:
        parte_uno: Mecanismo y purview de la primera parte.
    '''
    mech_p, pur_p = parte_uno
    mech_d, purv_d = parte_dos

    # Convertir índices a letras o símbolo vacío si no hay elementos
    purv_prim = COLON_DELIM.join(ABECEDARY[j] for j in pur_p) if pur_p else VOID_STR
    mech_prim = (
        COLON_DELIM.join(LOWER_ABECEDARY[i] for i in mech_p) if mech_p else VOID_STR
    )

    purv_dual = COLON_DELIM.join(ABECEDARY[i] for i in purv_d) if purv_d else VOID_STR
    mech_dual = (
        COLON_DELIM.join(LOWER_ABECEDARY[j] for j in mech_d) if mech_d else VOID_STR
    )

    width_prim = max(len(purv_prim), len(mech_prim)) + BASE_TWO
    width_dual = max(len(purv_dual), len(mech_dual)) + BASE_TWO

    return (
        f"⎛{purv_prim:^{width_prim}}⎞⎛{purv_dual:^{width_dual}}⎞\n"
        f"⎝{mech_prim:^{width_prim}}⎠⎝{mech_dual:^{width_dual}}⎠\n"
    )


def fmt_biparticion_q(
    prim: list[tuple[int, int]],
    dual: list[tuple[int, int]],
    to_sort: bool = True,
) -> str:
    top_prim, bottom_prim = fmt_parte_q(prim, to_sort)
    top_dual, bottom_dual = fmt_parte_q(dual, to_sort)

    return f"{top_prim}{top_dual}\n{bottom_prim}{bottom_dual}\n"


def fmt_parte_q(
    parte: list[tuple[int, int]], a_ordenar: bool = True
) -> tuple[str, str]:
    if a_ordenar:
        # Ordenar por índice #
        parte.sort(key=lambda x: x[1])

    purv, mech = [], []
    for time, idx in parte:
        purv.append(ABECEDARY[idx]) if time else mech.append(LOWER_ABECEDARY[idx])

    str_purv = COLON_DELIM.join(purv) if purv else VOID_STR
    str_mech = COLON_DELIM.join(mech) if mech else VOID_STR
    width = max(len(str_purv), len(str_mech)) + 2

    return f"⎛{str_purv:^{width}}⎞", f"⎝{str_mech:^{width}}⎠"


fmt_biparte_q = fmt_biparticion_q


def fmt_parts(
    parte: tuple,
    sistema: tuple,
) -> str:
    """Formatea la bipartición hallada por QNodes (oracle Zeta).

    Args:
        parte: (alcance, mecanismo) del grupo aislado (tuplas de ints).
        sistema: (indices, dims) del subsistema completo (tuplas/arrays de ints).
    """
    alcance, mecanismo = parte
    indices, dims = sistema
    alc2 = tuple(i for i in indices if i not in set(alcance))
    mec2 = tuple(d for d in dims if d not in set(mecanismo))
    return fmt_biparticion_fuerza_bruta(
        [list(mecanismo), list(alcance)],
        [list(mec2), list(alc2)],
    )


def fmt_kparticion_kqnodes(partes: list[list[tuple[int, int]]]) -> str:
    """Formatea una k-partición con boxes de box-drawing.

    Args:
        partes: Lista de k grupos, cada grupo es lista de vértices (tiempo, idx).
    """
    if not partes:
        return ""

    cajas = []
    for parte in partes:
        purv, mech = [], []
        for tiempo, idx in parte:
            if tiempo == 1:
                purv.append(ABECEDARY[idx])
            else:
                mech.append(LOWER_ABECEDARY[idx])

        str_purv = COLON_DELIM.join(purv) if purv else VOID_STR
        str_mech = COLON_DELIM.join(mech) if mech else VOID_STR
        width = max(len(str_purv), len(str_mech)) + 2

        cajas.append(f"⎛{str_purv:^{width}}⎞")
        cajas.append(f"⎝{str_mech:^{width}}⎠")

    linea_top = "".join(cajas[0::2])
    linea_bottom = "".join(cajas[1::2])

    return f"{linea_top}\n{linea_bottom}\n"
