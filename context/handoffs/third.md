# Handoff — Sesión 3: Pipeline CSV para comparativa k-particiones

> Última actualización: sesión 3 — Fase 3 lista para ejecutar

---

## 1. Qué se hizo esta sesión

- **TV-03 y TV-04 validadas (k=2, k=3)** sobre N=8 con los 10 casos de prueba.
  - KQNodes k=2 coincide con QNodes baseline (Δ < 1e-6) en todos los casos.
  - La pérdida no crece al pasar de k=2 a k=3 en ningún caso.
  - k=4 excluido del barrido (tiempo de cómputo excesivo para N=8).
- **`Analysis/main.py`** recibió su bloque `__main__` al final del archivo,
  cerrando el pipeline de 3 pasos.

---

## 2. Estado de fases actualizado

| Fase | Estado |
|------|--------|
| 0 — Baseline GeoMIP / QNodes desde Excel | ✅ EXISTE |
| 1 — `KGeoMIP` | ✅ IMPLEMENTADO |
| 2 — `KQNodes` | ✅ IMPLEMENTADO |
| 3 — TV-02 (KGeoMIP k=2 == GeoMIP) | ⚠️ PENDIENTE ejecutar |
| 3 — TV-03 (KQNodes k=2 == QNodes) | ✅ VALIDADO (todos los casos N=8) |
| 3 — TV-04 monotonía k=2→k=3 | ✅ VALIDADO (todos los casos N=8) |
| 3 — CSV comparativo k={2,3} | ⏳ LISTO PARA EJECUTAR |
| 4 — `tecnico.tex` | ❌ FALTA |

---

## 3. Pipeline de ejecución (Fase 3)

Los batch runners ya tienen `K_VALS = [2, 3]`. Ejecutar en este orden:

```bash
# Paso 1 — KGeoMIP batch
cd source\GeoMIP\src\Method2_Dynamic_Programming_Reformulation
uv run python run_kgeomip_batch.py
# Genera: source/GeoMIP/results/resultados_kgeomip_n8.csv

# Paso 2 — KQNodes batch
cd ..\..\..\..\..\QNodes
uv run python run_kqnodes_batch.py
# Genera: source/QNodes/results/resultados_kqnodes_n8.csv

# Paso 3 — Combinar y calcular métricas
cd ..\Analysis
uv run python main.py
# Genera: source/Analysis/resultados_k_comparacion.csv
```

---

## 4. Estructura del CSV de salida (`resultados_k_comparacion.csv`)

| Columna | Descripción |
|---|---|
| `caso_id` | C01 … C10 |
| `descripcion` | Nombre del caso |
| `alcance` / `mecanismo` | Bits N=8 |
| `geo_perdida` / `geo_tiempo` | GeometricSIA baseline |
| `kgeo_k2_perdida` / `kgeo_k2_tiempo` | KGeoMIP k=2 |
| `kgeo_k3_perdida` / `kgeo_k3_tiempo` | KGeoMIP k=3 |
| `q_perdida` / `q_tiempo` | QNodes baseline |
| `kq_k2_perdida` / `kq_k2_tiempo` | KQNodes k=2 |
| `kq_k3_perdida` / `kq_k3_tiempo` | KQNodes k=3 |
| `mejora_geo_k3_vs_k2` | kgeo_k2 − kgeo_k3 (>0 = mejora) |
| `mejora_q_k3_vs_k2` | kq_k2 − kq_k3 |
| `diff_geo_vs_q_base` | \|geo − q\| baseline |
| `diff_geo_vs_q_k2` | \|kgeo_k2 − kq_k2\| |
| `diff_geo_vs_q_k3` | \|kgeo_k3 − kq_k3\| |
| `tv03_geo_ok` / `tv03_q_ok` | Validación TV-03 (bool) |
| `tv04_geo_ok` / `tv04_q_ok` | Validación TV-04 (bool) |

---

## 5. Próximos pasos

### Inmediatos (Fase 3 completa)
1. Ejecutar el pipeline de 3 pasos anterior.
2. Revisar el CSV resultante: columnas `tv03_geo_ok` y `tv04_geo_ok` deben ser `True` en todos los casos (TV-02 de GeoMIP aún pendiente de validación formal).
3. Si algún caso falla TV-03/TV-04 en GeoMIP, revisar `KGeoMIP._evaluar_k_particion`.

### Fase 4 — Documentación
4. Con el CSV en mano, comenzar las gráficas comparativas:
   - Pérdida por caso: barras agrupadas (geo k=2, geo k=3, q k=2, q k=3).
   - Tiempo por caso: ídem.
   - Mejora relativa k=3 vs k=2 por estrategia.
5. Añadir gráficas al documento `document/tecnico.tex`.
6. Diagramas Mermaid (clases, paquetes, secuencia) para KGeoMIP y KQNodes.

---

## 6. Archivos clave modificados esta sesión
  
| Archivo | Cambio |
|---|---|
| `source/Analysis/main.py` | Añadido `__main__` al final (Modo 2 por defecto: k-CSV) |

## 7. Archivos a consultar para continuar

| Propósito | Archivo |
|---|---|
| Batch KQNodes | `source/QNodes/run_kqnodes_batch.py` |
| Batch KGeoMIP | `source/GeoMIP/.../run_kgeomip_batch.py` |
| Combinar CSVs | `source/Analysis/main.py` (modo k, por defecto) |
| CSV de salida | `source/Analysis/resultados_k_comparacion.csv` |
