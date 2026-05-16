## Objetivos de validación

### TV-01 — Consistencia baseline biparticiones

**Precondición:** GeoMIP y QNodes ejecutados sobre el mismo subsistema.

- [ ] **Criterio:** `|perdida_geo - perdida_q| < 1e-4` para cada fila del Excel.
      **Herramienta:** pytest + pandas.

```python
def test_consistencia_baseline(resultados_geo, resultados_q):
    for i, (pG, pQ) in enumerate(zip(resultados_geo["Pérdida"], resultados_q["Pérdida"])):
        assert abs(float(pG) - float(pQ)) < 1e-4, f"Fila {i}: geo={pG} vs q={pQ}"
```

### TV-02 — KGeoMIP == GeoMIP cuando k=2

- [ ] **Criterio:** La pérdida de `KGeoMIP(k=2)` debe ser igual a la de `GeometricSIA` dentro de tolerancia `1e-6`.

```python
def test_kgeomip_k2_igual_geomip(sistema_pequeno):
    condicion, alcance, mecanismo, tpm = sistema_pequeno
    manager = Manager("100")
    geo = GeometricSIA(manager).aplicar_estrategia(condicion, alcance, mecanismo, tpm)
    kgeo = KGeoMIP(manager, k=2).aplicar_estrategia(condicion, alcance, mecanismo, tpm)
    assert abs(geo.perdida - kgeo.perdida) < 1e-6
```

### TV-03 — KQNodes == QNodes cuando k=2

- [ ] **Criterio:** Análogo al TV-02 para la estrategia QNodes.

```python
def test_kqnodes_k2_igual_qnodes(sistema_pequeno):
    condicion, alcance, mecanismo = sistema_pequeno
    manager = Manager("100")
    q = QNodes(manager).aplicar_estrategia(condicion, alcance, mecanismo)
    kq = KQNodes(manager, k=2).aplicar_estrategia(condicion, alcance, mecanismo)
    assert abs(q.perdida - kq.perdida) < 1e-6
```

### TV-04 — Pérdida k-MIP <= pérdida 2-MIP

- [ ] **Criterio:** Al aumentar k, la pérdida no puede crecer (más libertad de partición implica pérdida menor o igual).

```python
def test_perdida_decrece_con_k(sistema_pequeno):
    tpm, condicion, alcance, mecanismo = sistema_pequeno
    manager = Manager("1000")
    perdidas = []
    for k in range(2, 5):
        sol = KGeoMIP(manager, k=k).aplicar_estrategia(condicion, alcance, mecanismo, tpm)
        perdidas.append(sol.perdida)
    for i in range(len(perdidas) - 1):
        assert perdidas[i] >= perdidas[i+1] - 1e-6, f"Pérdida subió en k={i+3}"
```

### TV-05 — NCube: marginalizar es conmutativo

- [ ] **Criterio:** `ncubo.marginalizar([a,b]) == ncubo.marginalizar([a]).marginalizar([b])`.

```python
def test_marginalizar_conmutativo(ncubo_3d):
    resultado_conjunto = ncubo_3d.marginalizar(np.array([0, 1], dtype=np.int8))
    resultado_secuencial = (
        ncubo_3d
        .marginalizar(np.array([0], dtype=np.int8))
        .marginalizar(np.array([1], dtype=np.int8))
    )
    np.testing.assert_allclose(resultado_conjunto.data, resultado_secuencial.data, atol=1e-6)
```

### TV-06 — System.bipartir conserva distribución marginal sin corte real

- [ ] **Criterio:** Si todos los nodos quedan en el mismo grupo, la distribución marginal de la bipartición debe ser idéntica a la del subsistema original.

```python
def test_bipartir_sin_corte(subsistema_n3):
    todos_futuros = subsistema_n3.indices_ncubos
    todas_dims = subsistema_n3.dims_ncubos
    biparticion = subsistema_n3.bipartir(todos_futuros, todas_dims)
    np.testing.assert_allclose(
        biparticion.distribucion_marginal(),
        subsistema_n3.distribucion_marginal(),
        atol=1e-6,
    )
```

### TV-07 — Generación de k-particiones cubre todos los casos n=3, k=3

- [ ] **Criterio:** Para n=3 variables y k=3 la función `generar_k_particiones_candidatas` debe retornar exactamente S(3,3)=1 partición = `{{a},{b},{c}}`.

```python
def test_numero_particiones_n3_k3(kgeomip_n3):
    particiones = kgeomip_n3.generar_k_particiones_candidatas(k=3)
    # S(3,3) = 1
    assert len(particiones) == 1
```

### TV-08 — Tiempo de ejecución registrado en Solution

- [ ] **Criterio:** `solution.tiempo_ejecucion > 0` en toda ejecución.

```python
def test_tiempo_positivo(solucion_geo):
    assert solucion_geo.tiempo_ejecucion > 0
```

## Fixtures sugeridas

```python
# conftest.py
import numpy as np
import pytest
from src.controllers.manager import Manager
from src.models.core.ncube import NCube
from src.models.core.system import System

@pytest.fixture
def sistema_pequeno():
    """Sistema determinista N=3, estado inicial 100."""
    tpm = np.array([
        [0,0,1],[1,0,0],[0,1,0],[0,0,1],
        [1,1,0],[0,1,1],[1,0,0],[0,1,0]
    ], dtype=float)
    return tpm, "111", "111", "111"

@pytest.fixture
def ncubo_3d():
    data = np.random.rand(2, 2, 2)
    return NCube(indice=0, dims=np.array([0, 1, 2], dtype=np.int8), data=data)

@pytest.fixture
def subsistema_n3(sistema_pequeno):
    tpm, condicion, alcance, mecanismo = sistema_pequeno
    manager = Manager("100")
    from src.controllers.strategies.geometric import GeometricSIA
    geo = GeometricSIA(manager)
    geo.sia_preparar_subsistema(condicion, alcance, mecanismo, tpm)
    return geo.sia_subsistema
```
