## Pasos de implementación

### Fase 0 — Fuente de la verdad y baseline

1. **Coordinar la fuente de la verdad:** Unificar la lectura del archivo Excel de pruebas (`Pruebas_Metodo2.xlsx`) para ambas estrategias con la misma función `ejecutar_desde_excel`.
2. **Ejecutar GeoMIP con biparticiones** sobre todas las filas del Excel y guardar `resultados_Geometric.xlsx`.
3. **Ejecutar QNodes con biparticiones** sobre las mismas filas y guardar `resultados_QNodes.xlsx`.
4. **Verificar consistencia:** la pérdida (`phi`) de ambas estrategias debe coincidir (las particiones pueden diferir).
5. **Generar CSVs comparativos** con columnas: `Iteración, Alcance, Mecanismo, Pérdida_Geo, Pérdida_Q, Tiempo_Geo, Tiempo_Q`. Se compila mediante [main.py](/source/Analysis/main.py).

### Fase 1 — Extensión KGeoMIP

6. Crear `source/GeoMIP/src/Method2.../src/controllers/strategies/kgeomip.py` con clase `KGeoMIP(GeometricSIA)`.
7. Agregar parámetro `k: int` en `aplicar_estrategia`.
8. Implementar `generar_k_particiones_candidatas()`: dado el conjunto de vértices `V`, generar particiones de `V` en exactamente `k` partes no vacías guiadas por la heurística geométrica (números de Stirling de segundo tipo como cota del espacio de búsqueda).
9. Adaptar `find_kmip()` para iterar sobre `k` grupos en lugar de dos.
10. Validar que para `k=2` el resultado coincide con `GeometricSIA`.

### Fase 2 — Extensión KQNodes

11. Crear `source/QNodes/src/strategies/kqnodes.py` con clase `KQNodes(QNodes)`.
12. Extender `algorithm` para que en lugar de formar un único par candidato por fase, forme `k` grupos mediante `k-1` cortes sucesivos del proceso de Queyranne.
13. Validar para `k=2`.

### Fase 3 — Experimentación y resultados

14. Ejecutar `KGeoMIP` y `KQNodes` sobre el mismo Excel con la siguiente política de k:
    - El algoritmo recibe `k` como **parámetro libre**; no hay límite fijo codificado.
    - El experimento arranca con `k ∈ {2, 3, 4, 5}` para establecer el comportamiento base y observar el patrón de convergencia antes de ampliarlo.
    - Se incorpora un **criterio de parada temprana por estabilización:** si la mejora de pérdida entre k y k+1 es menor que `ε = 1e-4`, el barrido se detiene, reportando el `k_opt` hallado para ese subsistema.
    - El límite superior de seguridad es `k_max = min(|V|, k_tope_config)`, donde `|V|` es el número de vértices del subsistema (presentes + futuros). Para `k = |V|` la pérdida es siempre 0 (cada vértice en su propio grupo), por lo que ese extremo no aporta información discriminativa. `k_tope_config` se define en la configuración de la aplicación (por defecto 8, ajustable por variable de entorno).
    - **Criterio de parada adicional por coste combinatorio:** si `S(|V|, k)` (número de Stirling de segundo tipo) supera un presupuesto de evaluaciones configurable (por defecto 10 000), se activa modo heurístico sin exploración exhaustiva.

15. Generar tablas de tiempos y pérdidas indexadas por `(n, k)`.

16. Generar análisis y gráficas bajo `source/GeoMIP/results/analysis/` con la siguiente estructura:

    ```
    source/GeoMIP/results/analysis/
    ├── tablas/
    │   ├── comparativa_baseline.csv        # pérdida y tiempo Geo vs Q para k=2
    │   ├── perdida_por_n_k_geo.csv         # pérdida KGeoMIP para cada (n, k)
    │   └── perdida_por_n_k_q.csv           # pérdida KQNodes para cada (n, k)
    ├── graficas/
    │   ├── tiempo_vs_n_por_k.png           # escalabilidad: tiempo fijando k, variando n
    │   ├── tiempo_vs_k_por_n.png           # escalabilidad: tiempo fijando n, variando k
    │   ├── perdida_vs_k_por_n.png          # curva de convergencia de pérdida al crecer k
    │   └── k_opt_por_subsistema.png        # k donde se estabiliza la pérdida por subsistema
    └── scripts/
        └── generar_analisis.py             # script reproducible que lee los resultados y exporta todo lo anterior
    ```

    Las gráficas generadas en `graficas/` se copian automáticamente a `document/sections/tecnico/` para su inclusión directa en `document/tecnico.tex`.

### Fase 4 — Documentación

17. Completar `document/tecnico.tex` con las secciones del lineamiento (2.1–2.9).
18. Insertar gráficas generadas y diagramas Mermaid exportados como PNG/PDF.
19. Redactar análisis de complejidad formal:
    - Complejidad computacional temporal $T(n)$.
    - Complejidad computacional espacial $S(n)$.
    - Notación asintótica.

<!--
TODOS:
1. Coordinar una fuente de la verdad para ambas estrategias.
2. Que se generen los CSVs que para compararlos
3. Implementar KGeoMIP.py
4. Implementar KQNodes.py
5. Validar k=2 contra baseline
6. Ejecutar experimentos k>2
7. Completar tecnico.tex
-->
