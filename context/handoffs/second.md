# Handoff — Sesión 2: Implementación KGeoMIP y KQNodes

> Última actualización: sesión 2 — Fases 1 y 2 implementadas

---

## 1. Qué se hizo esta sesión

Se implementaron las Fases 1 y 2 del proyecto:

| Archivo creado | Clase | Descripción |
|---|---|---|
| `source/GeoMIP/src/Method2_.../src/controllers/strategies/kgeomip.py` | `KGeoMIP(GeometricSIA)` | Extensión geométrica para k-particiones |
| `source/QNodes/src/strategies/kqnodes.py` | `KQNodes(QNodes)` | Extensión de Queyranne para k-particiones |

---

## 2. Diseño de KGeoMIP

**Archivo:** `source/GeoMIP/src/Method2_Dynamic_Programming_Reformulation/src/controllers/strategies/kgeomip.py`

### Flujo principal

```
KGeoMIP(gestor, k).aplicar_estrategia(condicion, alcance, mecanismo, tpm, k)
  └─ sia_preparar_subsistema(...)        # hereda de SIA
  └─ construir tabla de costos           # hereda de GeometricSIA
       └─ calcular_costos_nivel() x niveles
  └─ find_kmip()
       └─ generar_k_particiones_candidatas(k)
            ├─ _candidatas_desde_tabla(k)    # greedy por costos de transición
            └─ _candidatas_desde_hamming(k)  # cortes por niveles Hamming
       └─ _evaluar_k_particion(grupos)       # EMD por bipartir()
  └─ Solution(perdida_minima, k_particion)
```

### Decisiones de diseño

- **Para k=2**: `generar_k_particiones_candidatas` produce exactamente las mismas candidatas que `identificar_particiones_optimas` de `GeometricSIA` → garantiza TV-02.
- **Presupuesto S(n,k)**: si `_stirling2(|V|, k) > 10_000` activa modo heurístico (solo greedy, sin exploración exhaustiva).
- **`_candidatas_desde_tabla`**: ordena futuros por costo de transición (mayor costo = más separable), genera k-1 cortes sucesivos.
- **`_candidatas_desde_hamming`**: genera cortes ortogonales por niveles de Hamming (complementa la búsqueda).
- **Fallback**: si `memoria_kparticiones` queda vacío, delega a `find_mip()` de `GeometricSIA`.
- **Clave en memoria**: `tuple(sorted(grupos[0]))` → tupla de vértices del primer grupo.

### Parámetros del constructor

```python
KGeoMIP(gestor: Manager, k: int = 2, k_tope: int = 8, presupuesto: int = 10_000)
```

---

## 3. Diseño de KQNodes

**Archivo:** `source/QNodes/src/strategies/kqnodes.py`

### Flujo principal

```
KQNodes(tpm, k).aplicar_estrategia(estado_inicial, condicion, alcance, mecanismo, k)
  └─ sia_preparar_subsistema(...)        # hereda de SIA (vía QNodes)
  └─ k=2: delega a algorithm() original  # garantiza TV-03
  └─ k>2: algorithm_k(vertices, k)
       └─ Bucle k-1 veces:
            ├─ algorithm(vertices_restantes)   # Queyranne sobre el resto
            ├─ extraer grupo_candidato
            ├─ _evaluar_grupo(grupo_candidato) # EMD vs subsistema completo
            └─ vertices_restantes -= grupo_candidato
       └─ último grupo: remanente
  └─ Solution(perdida_minima, k_particion)
```

### Decisiones de diseño

- **k=2**: delega directamente a `algorithm()` de `QNodes` (rama `if self.k == 2`) → garantiza TV-03 sin código duplicado.
- **k>2**: aplica k-1 cortes sucesivos del proceso de Queyranne. La memoización de `memoria_delta` se preserva entre cortes (los EMDs individuales de vértices son reutilizables). `memoria_grupo_candidato` se limpia entre cortes para evitar contaminación.
- **`_evaluar_grupo`**: evalúa la EMD de un grupo llamando a `bipartir()` sobre el subsistema completo con los futuros/presentes del grupo.
- **Presupuesto**: si `S(n,k) > 10_000` → modo heurístico (un solo barrido Queyranne sin exploración adicional).

### Parámetros del constructor

```python
KQNodes(tpm: np.ndarray, k: int = 2, k_tope: int = 8, presupuesto: int = 10_000)
```

---

## 4. Estado de fases actualizado

| Fase | Estado |
|------|--------|
| 0 — Baseline GeoMIP desde Excel | ✅ EXISTE |
| 0 — Baseline QNodes desde Excel | ✅ EXISTE (`ejecutar_desde_excel` en `QNodes/src/main.py`) |
| 0 — CSV comparativo | ✅ EXISTE (`Analysis/main.py`) |
| 1 — `KGeoMIP` | ✅ IMPLEMENTADO |
| 2 — `KQNodes` | ✅ IMPLEMENTADO |
| 3 — Experimentos k>2 | ❌ FALTA (TV-02, TV-03 primero) |
| 4 — `tecnico.tex` | ❌ FALTA |

---

## 5. Próximos pasos (en orden)

### Inmediatos: Validación

1. **Ejecutar TV-02**: verificar que `KGeoMIP(k=2)` produce pérdida igual a `GeometricSIA` (tolerancia 1e-6).
2. **Ejecutar TV-03**: verificar que `KQNodes(k=2)` produce pérdida igual a `QNodes` (tolerancia 1e-6).
3. **Corregir** cualquier discrepancia encontrada (probablemente en la lógica de `_candidatas_desde_tabla` o la selección de la clave).

### Después: Experimentación (Fase 3)

4. Crear script de barrido `k ∈ {2,3,4,5}` sobre las pruebas del Excel.
5. Generar tablas `perdida_por_n_k_geo.csv` y `perdida_por_n_k_q.csv`.
6. Implementar criterio de parada temprana (ε = 1e-4).
7. Generar gráficas en `source/GeoMIP/results/analysis/graficas/`.

### Potenciales correcciones a vigilar

- `KGeoMIP._evaluar_k_particion`: actualmente evalúa solo el **primer grupo** de cada k-partición. Para redes donde k>2 esto puede no ser suficientemente discriminativo. Si TV-04 falla, hay que evaluar todos los grupos y sumar EMDs.
- `KQNodes.algorithm_k`: la extracción de `grupo_candidato` desde `mip_corte` (que puede ser una tupla anidada de listas) puede requerir aplanamiento. Revisar el formato de salida de `algorithm()` con el subsistema específico.
- El `fmt_biparticion_q` de `KQNodes` formatea solo el primer grupo vs. su complemento; para k>2 sería deseable un formato multi-parte (post-TV-03).

---

## 6. Comandos para validar (TV-02 y TV-03)

```bash
# Desde source/GeoMIP/src/Method2_Dynamic_Programming_Reformulation
# TV-02: KGeoMIP k=2 == GeometricSIA
uv run python -c "
from src.controllers.manager import Manager
from src.controllers.strategies.geometric import GeometricSIA
from src.controllers.strategies.kgeomip import KGeoMIP
import numpy as np

estado = '1000'
cond   = '1110'
alc    = '1110'
mec    = '1110'
manager = Manager(estado)
tpm = manager.cargar_red() if hasattr(manager, 'cargar_red') else None

geo  = GeometricSIA(manager).aplicar_estrategia(cond, alc, mec, tpm)
kgeo = KGeoMIP(manager, k=2).aplicar_estrategia(cond, alc, mec, tpm)
print(f'GeoMIP perdida: {geo.perdida}')
print(f'KGeoMIP perdida: {kgeo.perdida}')
print(f'Diferencia: {abs(geo.perdida - kgeo.perdida)}')
print(f'TV-02 OK: {abs(geo.perdida - kgeo.perdida) < 1e-6}')
"

# Desde source/QNodes
# TV-03: KQNodes k=2 == QNodes
uv run python -c "
from src.controllers.manager import Manager
from src.strategies.q_nodes import QNodes
from src.strategies.kqnodes import KQNodes
import numpy as np

estado = '1000'
cond   = '1110'
alc    = '1110'
mec    = '1110'
manager = Manager(estado)
tpm = manager.cargar_red()

q  = QNodes(tpm).aplicar_estrategia(estado, cond, alc, mec)
kq = KQNodes(tpm, k=2).aplicar_estrategia(estado, cond, alc, mec)
print(f'QNodes perdida: {q.perdida}')
print(f'KQNodes perdida: {kq.perdida}')
print(f'Diferencia: {abs(q.perdida - kq.perdida)}')
print(f'TV-03 OK: {abs(q.perdida - kq.perdida) < 1e-6}')
"
```
