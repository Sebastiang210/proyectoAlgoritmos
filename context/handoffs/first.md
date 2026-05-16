# Handoff — Sesión de onboarding completo

> Última actualización: sesión 1 — lectura total del codebase

---

## 1. Qué es este proyecto

**K-QGMIP** (Universidad de Caldas, 2026-1 — Análisis y Diseño de Algoritmos).

Objetivo: extender dos heurísticas de búsqueda de **MIP** (Minimal Information Partition, IIT 4.0) de **bi-particiones → k-particiones**:

| Estrategia base | Clase nueva | Archivo nuevo |
|---|---|---|
| `GeometricSIA` | `KGeoMIP` | `source/GeoMIP/src/Method2_.../src/controllers/strategies/kgeomip.py` |
| `QNodes` (GeoMIP side) | `KGeoMIP` hereda también QNodes | idem |
| `QNodes` (independiente) | `KQNodes` | `source/QNodes/src/strategies/kqnodes.py` |

Entregable académico: Manual Técnico en LaTeX (`document/tecnico.tex`, secciones 2.1–2.9).

---

## 2. Mapa del repositorio

```
proyectoAlgoritmos/
├── context/
│   ├── sdd-3/           ← constitución: main.md, architecture.md, planning.md, testing.md
│   ├── handoffs/        ← ESTE archivo
│   └── lineamiento.md   ← spec del entregable académico
├── document/
│   └── tecnico.tex      ← LaTeX del manual técnico
└── source/
    ├── pyproject.toml   ← workspace uv (Python ≥ 3.13)
    ├── GeoMIP/
    │   ├── data/samples/          ← TPMs en CSV: N{n}{pagina}.csv  (ej: N4A.csv)
    │   ├── results/
    │   │   ├── Pruebas_Metodo2.xlsx      ← FUENTE DE LA VERDAD de pruebas
    │   │   └── resultados_Geometric.xlsx ← salida ya generada por GeoMIP
    │   └── src/Method2_Dynamic_Programming_Reformulation/
    │       ├── exec.py            ← punto de entrada GeoMIP
    │       └── src/
    │           ├── main.py                 ← ejecutar_desde_excel() aquí
    │           ├── controllers/
    │           │   ├── manager.py          ← Manager(estado_inicial)
    │           │   └── strategies/
    │           │       ├── geometric.py    ← GeometricSIA   ← BASE
    │           │       └── q_nodes.py      ← QNodes (copia dentro de GeoMIP)
    │           ├── models/
    │           │   ├── base/sia.py         ← SIA abstracta
    │           │   └── core/
    │           │       ├── system.py       ← System (condicionar, substraer, bipartir)
    │           │       ├── ncube.py        ← NCube (marginalizar, condicionar)
    │           │       └── solution.py     ← Solution (presentación resultado)
    │           └── funcs/base.py           ← emd_efecto(), ABECEDARY
    ├── QNodes/
    │   ├── exec.py                 ← punto de entrada QNodes
    │   └── src/
    │       ├── main.py             ← solo usa BruteForce por ahora (NO usa Excel)
    │       └── strategies/
    │           ├── q_nodes.py      ← QNodes independiente    ← BASE KQNodes
    │           └── force.py
    └── Analysis/
        └── main.py                 ← vacío (solo print Hello) — aquí va el comparador
```

---

## 3. Flujo de ejecución actual (GeoMIP)

```
exec.py
  └─ iniciar()  [main.py]
       └─ ejecutar_desde_excel(Pruebas_Metodo2.xlsx, resultados_Geometric.xlsx)
            ├─ Lee sheet_name=8, col B, skiprows=3  → lista de subsistemas "Alc|Mec"
            ├─ Convierte letras→binario con convertir_a_binario()
            ├─ Manager(estado_inicial)  → resuelve ruta TPM automáticamente
            ├─ Por cada fila: proceso hijo con timeout 3600s
            │    └─ GeometricSIA(manager).aplicar_estrategia(cond, alc, mec, tpm)
            │         ├─ sia_preparar_subsistema()   [SIA]
            │         │    ├─ System(tpm, estado_inicial)   → ncubos
            │         │    ├─ condicionar(dims_zero_en_condicion)
            │         │    └─ substraer(dims_zero_alc, dims_zero_mec)
            │         └─ find_mip()
            │              ├─ calcular_costos_nivel() por cada nivel Hamming
            │              ├─ identificar_particiones_optimas()
            │              └─ bipartir() + emd_efecto() por cada candidato
            └─ Guarda DataFrame → resultados_Geometric.xlsx
```

**QNodes** (en `QNodes/`) solo tiene `BruteForce` activo. Su `q_nodes.py` existe pero `main.py` no lo llama; necesita integración similar al Excel (Fase 0).

---

## 4. Diferencia entre los dos QNodes

| | `GeoMIP/src/.../strategies/q_nodes.py` | `QNodes/src/strategies/q_nodes.py` |
|---|---|---|
| Hereda de | `SIA` (GeoMIP's) | `SIA` (QNodes's) |
| `aplicar_estrategia` recibe | `(condicion, alcance, mecanismo)` — sin tpm | igual |
| TPM | la carga SIA internamente | igual |
| Propósito | copia del algoritmo dentro del repo GeoMIP | implementación independiente |

`KQNodes` hereda de la versión en `QNodes/`.

---

## 5. Clases clave — firma y responsabilidad

### `SIA` (abstracta)
```python
sia_preparar_subsistema(condicion, alcance, mecanismo, tpm)
# → sets: self.sia_subsistema (System), self.sia_dists_marginales, self.sia_tiempo_inicio
aplicar_estrategia()   # abstracto
```

### `GeometricSIA(SIA)`
```python
aplicar_estrategia(condicion, alcance, mecanismo, tpm) -> Solution
find_mip() -> tuple   # clave mip mínima de self.memoria_particiones
calcular_costos_nivel(estado_final, nivel)
calcular_costo(estado_inicial, estado_final, ncubos)
identificar_particiones_optimas() -> list[[presentes, futuros]]
nodes_complement(nodes) -> list
hamming(a, b) -> int
```

### `QNodes(SIA)`
```python
aplicar_estrategia(condicion, alcance, mecanismo) -> Solution  # sin tpm
algorithm(vertices) -> tuple   # clave mip mínima
funcion_submodular(deltas, omegas) -> (emd_union, emd_delta, dist_delta)
nodes_complement(nodes) -> list
```

### `System`
```python
condicionar(indices) -> System        # background conditions
substraer(alcance_dims, mec_dims) -> System   # genera subsistema
bipartir(alcance, mecanismo) -> System        # genera partición
distribucion_marginal() -> ndarray    # vector de probabilidades por nodo
indices_ncubos  # property: array índices de ncubos presentes
dims_ncubos     # property: dims del primer ncubo (todas iguales antes de bipartir)
```

### `Manager`
```python
Manager(estado_inicial: str)
# Resuelve TPM en: src/.samples/N{n}{pagina}.csv  o  data/samples/N{n}{pagina}.csv
# pagina viene de aplicacion.pagina_sample_network (default "A")
tpm_filename    # Path al CSV
output_dir      # Path para logs/profiling
```

### `Solution`
```python
Solution(estrategia, perdida, distribucion_subsistema, distribucion_particion,
         tiempo_total, particion)
# Atributos: .perdida, .particion, .tiempo_ejecucion, .distribucion_*
```

---

## 6. Estado actual por fase

| Fase | Estado |
|------|--------|
| 0 — Baseline GeoMIP desde Excel | ✅ **EXISTE** (`main.py` + `resultados_Geometric.xlsx` ya generado) |
| 0 — Baseline QNodes desde Excel | ❌ **FALTA** — `QNodes/src/main.py` no tiene `ejecutar_desde_excel` |
| 0 — CSV comparativo | ❌ **FALTA** — `Analysis/main.py` está vacío |
| 1 — `KGeoMIP` | ❌ **FALTA** |
| 2 — `KQNodes` | ❌ **FALTA** |
| 3 — Experimentos k>2 | ❌ **FALTA** |
| 4 — `tecnico.tex` | ❌ **FALTA** |

---

## 7. Comandos útiles de desarrollo

### Entorno y ejecución

```bash
# Desde la raíz del proyecto (proyectoAlgoritmos/)
# El workspace uv agrupa source/ y sus subproyectos

# --- GeoMIP ---
cd source/GeoMIP/src/Method2_Dynamic_Programming_Reformulation
uv run exec.py
# Variables de entorno para rutas:
GEOMIP_INPUT_XLSX="ruta/Pruebas_Metodo2.xlsx" uv run exec.py
GEOMIP_OUTPUT_XLSX="ruta/salida.xlsx" uv run exec.py
GEOMIP_SAMPLES_DIR="ruta/samples" uv run exec.py

# --- QNodes ---
cd source/QNodes
uv run exec.py

# --- Analysis ---
cd source
uv run Analysis/main.py
```

### Instalar dependencias

```bash
# En source/ (workspace raíz)
uv sync

# En un subproyecto independiente (QNodes tiene su propio pyproject)
cd source/QNodes
uv sync
```

### Python versions

- `source/` workspace: Python ≥ 3.13
- `source/QNodes/`: Python ≥ 3.11 (numpy 1.26.4, scipy 1.17.0)
- Archivo `.python-version` en `source/` controla la versión por defecto

### Estructura de pruebas Excel

```
Pruebas_Metodo2.xlsx
  sheet_name = 8  (índice 0-based → hoja 9)
  col B, skiprows=3
  Formato celda: "ABC|abc"  → alcance|mecanismo en letras
  convertir_a_binario("ABC", n_bits=N) → "111000...0"
```

### Agregar nueva estrategia (patrón del proyecto)

```python
# 1. Crear archivo en strategies/
# 2. Heredar de la clase base correspondiente
class KGeoMIP(GeometricSIA):
    def __init__(self, gestor: Manager, k: int):
        super().__init__(gestor)
        self.k = k

    def aplicar_estrategia(self, condicion, alcance, mecanismo, tpm, k=None):
        ...
        return Solution(...)

# 3. Importar en main.py y agregar al ejecutar_desde_excel
```

### Logging

```python
from src.middlewares.slogger import SafeLogger
self.logger = SafeLogger("MI_TAG")
self.logger.critic("mensaje importante")
self.logger.debug("detalle")
# Nunca: print() en producción
```

---

## 8. Convenciones del proyecto

- **Idioma:** español para dominio IIT (alcance, mecanismo, perdida, bipartir...) — inglés solo en libs
- **Líneas por archivo:** máx 300
- **Redes en ejecución directa:** máx 10 nodos; mayores → indicar al humano
- **Tolerancia numérica:** `1e-4` para comparar pérdidas entre estrategias; `1e-6` para k=2 vs baseline
- **Formato partición:** `fmt_biparte_q(list_mip, complement)` → string Unicode con fracciones

---

## 9. Próximos pasos (en orden)

1. **Fase 0-QNodes:** Crear `ejecutar_desde_excel` en `QNodes/src/main.py` análogo al de GeoMIP y generar `resultados_QNodes.xlsx`
2. **Fase 0-Analysis:** Implementar `Analysis/main.py` que lea ambos xlsx y genere CSV comparativo
3. **Fase 1:** Crear `KGeoMIP` heredando `GeometricSIA`, implementar `find_kmip()` y `generar_k_particiones_candidatas()`
4. **Fase 2:** Crear `KQNodes` heredando `QNodes` independiente
5. Validar TV-01, TV-02, TV-03 (pytest)
