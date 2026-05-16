# CONSTITUCION

<!-- Reglas que voy a manejar (Ficheros, principios de software y calidad) -->

# CLARIFICACION

<!-- Preguntas que hay acerca del proyecto y como resolverlo -->

## Contextualización

En el contexto de la IIT4.0 se trabaja el concepto de la MIP (Minimal Information Partition), esta lo que nos dice es que existe una forma de partir un sistema de forma tal que su coste asociado sea mínimo.

Este proyecto busca resolver este problema mediante dos heurísticas denominadas como:

- Queyranne: Se basa en el principio de resolver grupos optimos de biparticiones y al final tomar la mejor opcion combinada.
- Geométrica: Se basa en que la topología de la TPM puede ser expresada como un hipercubo donde el numero de variables futuras son el numero de ncubos y el número de variables presentes el numero de dimensiones que maneja cada hipercubo.

Hay implementaciones pensadas para resolver el problema a nivel de biparticiones:

- [Queyranne](/source/QNodes/exec.py)
- [Geometric](/source/GeoMIP/src/Method2_Dynamic_Programming_Reformulation/exec.py)

Al ejecutarse `uv run ../exec.py` se generan una serie de documentos .xlsx guardados en:

- [Queyranne](source/QNodes/.docs/.strategies/qnodes/EjemploQNodesV1.xlsx)
- [Geometric](por definir > por ahora ejecuta una única prueba)

## Metodológia de desarrollo

A partir de las estrategias ya existentes, se busca diseñar algoritmos similares dentro de su respectivo directorio para trabajar con k-particiones.

La forma de validar que el resultado obtenido es correcto es mediante la pérdida obtenida; cálculada mediante la distancia-métrica usada (EMD) aplicada entre la distribución de probabilidad del subsistema y el subsistema reconstruído tras ser partido, esta debe ser mínima (optimo global).

Se ejecutan las pruebas desde la fuente de la verdad y los resultados deben ser coincidentes:

- Las biparticiones pueden ser distintas
- La pérdida debe ser el mínima

## Compilación documental

A partir de la comparativa de resultados se espera analizar el algoritmo viejo que genera 2-particiones y el nuevo que trabaja k-particiones.

Se plantea analizar:

- tiempos de compilación por cada prueba
- Biparticiones obtenidas

1. Se harán gráficas comparando cada prueba realizada.
2. Se describe por medio de diagramas mermaid el funcionamiento de cada estrategia vieja y nueva.
   - Diagrama de clases
   - Diagrama de paquetes
   - Diagrama de secuencia
   - Patrones utilizados

### Compilación latex

A partir de las graficas obtenidas se adicionan al documento [técnico](/document/tecnico.tex) en su respectiva [sección](/document/sections/tecnico).

---

1. Hay que ejecutar las estrategias Q-nodes y GeoMIP con la biparticiones utilizando las pruebas del excel.

2. Una vez ejecutadas dichas pruebas hay que adaptar el proyectos para que estas estrategias funciones con K particiones

3. Una vez implementado se vuelven a ejecutar las pruebas del excel con las K particiones

4. Documentar el proceso

- Crear manual de usuario
- Crear manual Tecnico

---

- Dos paradigmas geometrico, q-nodes aplicando multriprocesing
- Pruebas a partir de los excel

# SYSTEM DESIGN

<!-- Desde arquitectura actual del sistema, diagramas mencionados, optimalidad del sistema -->

# PLANEACION

<!-- Serie de pasos especifico para la implementacion -->

<!--
TODOS:
1. Coordinar una fuente de la verdad para ambas estrategias.
2. Que se generen los CSVs que para compararlos
-->

# TDD

<!-- Serie de objetivos, validaciones, pruebas unitarias que permiten automatizar el proceso -->
