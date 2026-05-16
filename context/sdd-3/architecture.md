
<!-- Desde arquitectura actual del sistema, diagramas mencionados, optimalidad del sistema -->

## Arquitectura actual del sistema

El sistema sigue un patrón **Template Method** combinado con **Strategy**:

- `SIA` (clase abstracta) define el flujo de preparación del subsistema en `sia_preparar_subsistema` y declara el contrato `aplicar_estrategia`.
- `GeometricSIA` y `QNodes` concretan `aplicar_estrategia` con sus respectivos algoritmos.
- `System` encapsula todas las operaciones algebraicas sobre la TPM (condicionar, substraer, bipartir, distribucion_marginal).
- `NCube` representa cada nodo como un hipercubo n-dimensional con operaciones de marginalización y condicionamiento.
- `Manager` resuelve la ruta de la TPM y expone el directorio de salida.
- `Solution` formatea y presenta el resultado (incluyendo síntesis de voz opcional).

### Diagrama de clases (Mermaid)

```mermaid
classDiagram
    class SIA {
        <<abstract>>
        +sia_gestor: Manager
        +sia_subsistema: System
        +sia_dists_marginales: ndarray
        +sia_tiempo_inicio: float
        +sia_preparar_subsistema(condicion, alcance, mecanismo, tpm)
        +aplicar_estrategia()*
        +chequear_parametros(candidato, futuro, presente) bool
        +sia_cargar_tpm() ndarray
    }

    class GeometricSIA {
        +etiquetas: list
        +tabla_transiciones: dict
        +vertices: set
        +tabla: dict
        +memoria_particiones: dict
        +aplicar_estrategia(condicion, alcance, mecanismo, tpm) Solution
        +find_mip() tuple
        +calcular_costos_nivel(estado_final, nivel)
        +calcular_costo(estado_inicial, estado_final, ncubos)
        +identificar_particiones_optimas() list
        +hamming(a, b) int
        +nodes_complement(nodes) list
    }

    class QNodes {
        +m: int
        +n: int
        +vertices: set
        +memoria_omega: dict
        +memoria_particiones: dict
        +aplicar_estrategia(condicion, alcance, mecanismo) Solution
        +algorithm(vertices) tuple
        +funcion_submodular(deltas, omegas) tuple
        +nodes_complement(nodes) list
    }

    class KGeoMIP {
        +k: int
        +aplicar_estrategia(condicion, alcance, mecanismo, tpm, k) Solution
        +find_kmip() tuple
        +generar_k_particiones_candidatas() list
    }

    class KQNodes {
        +k: int
        +aplicar_estrategia(condicion, alcance, mecanismo, k) Solution
        +algorithm_k(vertices, k) tuple
    }

    class Manager {
        +estado_inicial: str
        +ruta_base: Path
        +pagina: str
        +tpm_filename: Path
        +output_dir: Path
        +generar_red(dimensiones, datos_discretos) str
    }

    class System {
        +estado_inicial: ndarray
        +ncubos: tuple~NCube~
        +indices_ncubos: ndarray
        +dims_ncubos: ndarray
        +condicionar(indices) System
        +substraer(alcance_dims, mecanismo_dims) System
        +bipartir(alcance, mecanismo) System
        +distribucion_marginal() ndarray
    }

    class NCube {
        +indice: int
        +dims: ndarray
        +data: ndarray
        +condicionar(indices_condicionados, estado_inicial) NCube
        +marginalizar(ejes) NCube
    }

    class Solution {
        +estrategia: str
        +perdida: float
        +distribucion_subsistema: ndarray
        +distribucion_particion: ndarray
        +particion: str
        +tiempo_ejecucion: float
    }

    SIA <|-- GeometricSIA
    SIA <|-- QNodes
    GeometricSIA <|-- KGeoMIP
    QNodes <|-- KQNodes
    SIA --> Manager
    SIA --> System
    System --> NCube
    GeometricSIA --> Solution
    QNodes --> Solution
    KGeoMIP --> Solution
    KQNodes --> Solution
```

### Diagrama de paquetes (Mermaid)

```mermaid
graph TD
    subgraph GeoMIP["source/GeoMIP/src/Method2_Dynamic_Programming_Reformulation"]
        subgraph src_geo["src/"]
            main_geo["main.py"]
            subgraph controllers_geo["controllers/"]
                manager_geo["manager.py"]
                subgraph strategies_geo["strategies/"]
                    force_geo["force.py"]
                    geometric["geometric.py - GeometricSIA"]
                    qnodes_geo["q_nodes.py - QNodes"]
                    kgeomip["KGeoMIP.py  NEW"]
                end
            end
            subgraph models_geo["models/"]
                subgraph base_geo["base/"]
                    sia["sia.py - SIA"]
                    app["application.py"]
                end
                subgraph core_geo["core/"]
                    system["system.py - System"]
                    ncube["ncube.py - NCube"]
                    solution["solution.py - Solution"]
                end
            end
            subgraph funcs_geo["funcs/"]
                base_f["base.py (emd_efecto, ABECEDARY)"]
                format_f["format.py (fmt_biparte_q)"]
            end
            subgraph middlewares_geo["middlewares/"]
                slogger["slogger.py - SafeLogger"]
                profiler["profile.py"]
            end
        end
    end

    subgraph QNodes_pkg["source/QNodes"]
        exec_q["exec.py"]
        subgraph src_q["src/"]
            subgraph strategies_q["strategies/"]
                qnodes_q["q_nodes.py - QNodes independiente"]
                kqnodes["KQNodes.py  NEW"]
            end
        end
    end

    main_geo --> manager_geo
    main_geo --> geometric
    main_geo --> qnodes_geo
    geometric --> sia
    qnodes_geo --> sia
    kgeomip --> geometric
    sia --> system
    system --> ncube
    geometric --> solution
    qnodes_geo --> solution
    kgeomip --> solution
    kqnodes --> qnodes_q
```

### Diagrama de secuencia — Búsqueda de MIP (GeoMIP actual)

```mermaid
sequenceDiagram
    participant Main
    participant Manager
    participant GeometricSIA
    participant System
    participant NCube

    Main->>Manager: Manager(estado_inicial)
    Main->>GeometricSIA: GeometricSIA(manager)
    Main->>GeometricSIA: aplicar_estrategia(condicion, alcance, mecanismo, tpm)
    GeometricSIA->>GeometricSIA: sia_preparar_subsistema(...)
    GeometricSIA->>System: System(tpm, estado_inicial)
    System->>NCube: NCube(indice, dims, data) x n_nodos
    GeometricSIA->>System: condicionar(dims_condicionadas)
    GeometricSIA->>System: substraer(dims_alcance, dims_mecanismo)
    GeometricSIA->>GeometricSIA: find_mip()
    loop Por cada nivel de Hamming
        GeometricSIA->>GeometricSIA: calcular_costos_nivel(estado_final, nivel)
        GeometricSIA->>GeometricSIA: calcular_costo(estado_ini, estado_fin, ncubos)
    end
    GeometricSIA->>GeometricSIA: identificar_particiones_optimas()
    loop Por cada candidato
        GeometricSIA->>System: bipartir(futuros, presentes)
        System-->>GeometricSIA: distribucion_marginal()
        GeometricSIA->>GeometricSIA: emd_efecto(dist, sia_dists_marginales)
    end
    GeometricSIA-->>Main: Solution(perdida, particion, ...)
```

### Diagrama de secuencia — Extensión a k-particiones (KGeoMIP propuesto)

```mermaid
sequenceDiagram
    participant Main
    participant Manager
    participant KGeoMIP
    participant System

    Main->>KGeoMIP: KGeoMIP(manager, k)
    Main->>KGeoMIP: aplicar_estrategia(condicion, alcance, mecanismo, tpm, k)
    KGeoMIP->>KGeoMIP: sia_preparar_subsistema(...)
    KGeoMIP->>KGeoMIP: find_kmip()
    KGeoMIP->>KGeoMIP: generar_k_particiones_candidatas()
    note over KGeoMIP: Genera particiones del espacio de vertices en k grupos
    loop Por cada k-particion candidata
        KGeoMIP->>System: bipartir_k(grupos_futuros, grupos_presentes)
        System-->>KGeoMIP: distribucion_marginal()
        KGeoMIP->>KGeoMIP: emd_efecto(dist, sia_dists_marginales)
        KGeoMIP->>KGeoMIP: registrar si es minima
    end
    KGeoMIP-->>Main: Solution(perdida_minima, k_particion, ...)
```

## Optimalidad del sistema

### GeoMIP

- Explora el hipercubo de estados entre `estado_inicial` y `estado_final` por niveles de distancia Hamming, calculando el costo de transición `tx(i,j) = (1/2^dh) * (|X[i]-X[j]| + sum(tx(k,j)))`.
- Identifica candidatos en cada nivel y evalúa la EMD sólo para los más prometedores.
- **Fortaleza:** evita exploración combinatoria completa al guiarse por la topología del hipercubo.
- **Limitación actual:** genera únicamente biparticiones (k=2).

### QNodes

- Aplica el algoritmo de Queyranne adaptado: construye incrementalmente un conjunto `omega` eligiendo en cada paso el `delta` que minimiza la diferencia `EMD(omega ∪ delta) - EMD(delta)`.
- Usa memoización de EMDs individuales (`memoria_delta`) para evitar recálculos.
- **Fortaleza:** garantías teóricas de submodularidad para biparticiones.
- **Limitación actual:** ídem, sólo biparticiones.
