# Explicacion conceptual del proyecto SVQ1 + DQA4

## 1. Idea general del proyecto

El proyecto estudia la viabilidad de unificar dos instalaciones de Amazon en Sevilla:

- **SVQ1**, centro logistico o fulfillment center situado en Dos Hermanas.
- **DQA4**, estacion de ultima milla situada en Sevilla.

La pregunta principal no es solamente si se ahorra dinero, sino si la unificacion es defendible considerando rutas, inversion, personas, riesgos, calendario y capacidad operativa.

El proyecto debe entenderse como una **herramienta academica de analisis de viabilidad por escenarios**. No pretende predecir la operacion real de Amazon ni generar una forecast oficial. Trabaja con los datos del enunciado, los archivos del proyecto y supuestos documentados.

La idea de fondo es comparar alternativas:

- mantener la estructura actual, con SVQ1 y DQA4 separados;
- ampliar SVQ1 y hacer que asuma el flujo analizado;
- estudiar un posible centro nuevo o intermedio como referencia alternativa.

Una regla importante es que **DQA4 no se modela como cerrado por completo**. El proyecto analiza principalmente el flujo SVQ1 -> DQA4 descrito en el enunciado. DQA4 puede seguir operando otros flujos no incluidos en el modelo.

## 2. Que se quiere decidir

El objetivo final es construir una recomendacion razonada sobre la unificacion. Para que esa recomendacion sea defendible, el proyecto intenta responder preguntas como:

- cuantos paquetes se reparten y donde se concentra la demanda;
- cuantas rutas hacen falta y con que restricciones;
- que ocurre si el deposito de salida cambia de DQA4 a SVQ1 o a un punto intermedio;
- que alternativa de inversion tiene mejor equilibrio entre coste, ahorro y riesgo;
- como afecta la decision a empleados, transporte laboral y sindicatos;
- que meses son mejores o peores para ejecutar la transicion;
- que riesgos residuales quedan despues de aplicar mitigaciones;
- que escenarios resultan favorables, condicionados o debiles.

El proyecto no busca que un unico indicador decida todo automaticamente. La viabilidad se interpreta combinando resultados operativos, economicos y de riesgo.

## 3. Fuentes de datos y limites del modelo

El proyecto usa como fuentes principales:

- la sintesis del enunciado en `docs/sintesis_enunciado_proyecto.md`;
- los supuestos documentados en `docs/assumptions.md`;
- los datos tabulares de `data/`, especialmente poblacion, coordenadas, distancias, tiempos y costes de vehiculos;
- los modelos reimplementados desde MATLAB para economia y almacen.

Los datos externos no se inventan. Si el modelo necesita una magnitud que no esta en las fuentes, se documenta como supuesto interno o se mantiene fuera del alcance.

Los limites mas importantes son:

- la demanda se estima con poblacion como proxy, no con pedidos reales;
- las rutas son un modelo operativo simplificado, no una simulacion completa de Amazon;
- la capacidad fisica de las furgonetas no es una restriccion activa del solver;
- las furgonetas electricas si respetan un limite duro de autonomia;
- las ubicaciones continuas son referencias matematicas, no parcelas reales;
- los ahorros de DQA4 son parciales y atribuibles solo al flujo SVQ1 -> DQA4;
- el layout de almacen existe como bloque de apoyo, pero no decide todavia la recomendacion global.

## 4. Flujo general del analisis

El flujo conceptual del proyecto sigue esta secuencia:

1. **Carga de datos**: municipios, poblacion, coordenadas, matrices de distancia y tiempo.
2. **Estimacion de demanda**: convierte poblacion en paquetes diarios estimados.
3. **Tiempo de servicio**: transforma paquetes en minutos de servicio por nodo.
4. **Tratamiento de nodos grandes**: separa rutas dedicadas cuando un municipio concentra demasiada demanda.
5. **Optimizacion de rutas**: calcula rutas factibles con jornada laboral y autonomia electrica.
6. **Resumen operativo**: obtiene rutas totales, distancia, tiempo, flota usada y paquetes servidos.
7. **Localizacion**: compara referencias matematicas y candidatos operativos.
8. **Economia**: calcula CAPEX, OPEX, ahorros, payback, VAN, TIR y sensibilidad.
9. **Personas**: estima costes laborales, apoyos, aceptabilidad y riesgo laboral residual.
10. **Cronograma**: cruza fases e hitos con estacionalidad mensual.
11. **Riesgos**: calcula probabilidad, impacto y coste esperado residual.
12. **Escenarios**: combina decisiones de centro, inversion, personas, mitigacion y calendario.

La app permite leer estos bloques por separado o compararlos en un flujo guiado.

## 5. Demanda: que se calcula y por que

La demanda representa cuantos paquetes diarios se asignan a cada municipio o nodo. Como el proyecto no dispone de pedidos reales, utiliza la **poblacion como aproximacion de demanda**.

El calculo basico es:

```text
paquetes estimados = poblacion x penetracion de mercado
```

La penetracion de mercado es un parametro ajustable. Tambien puede calibrarse con un volumen diario objetivo. En ese caso, el modelo calcula que penetracion implicita hace falta para llegar a ese volumen total.

Despues se aplica la estacionalidad:

- enero-marzo: menor demanda;
- abril-junio: demanda base;
- julio-septiembre: demanda superior moderada;
- octubre-diciembre: demanda alta por pico de campana.

Esto importa porque la demanda alimenta casi todo lo demas: rutas, vehiculos, tiempo de servicio, riesgo operativo y lectura economica.

El deposito activo siempre tiene demanda cero. No tiene sentido que el punto de salida tenga paquetes "a entregar" como si fuera cliente.

## 6. Tiempo de servicio

Cada paquete genera tiempo operativo dentro del municipio. El modelo suma:

- un tiempo de servicio por paquete;
- un tiempo medio adicional entre paquetes dentro del mismo municipio.

La formula conceptual es:

```text
tiempo de servicio del nodo = paquetes del nodo x tiempo por paquete total
```

Este tiempo no es la distancia de carretera. Es el tiempo de reparto o manipulacion asociado al volumen de paquetes del municipio. Se suma al tiempo de viaje para saber si una ruta cabe dentro de la jornada.

## 7. Rutas y VRP

El problema de rutas se modela como un **Vehicle Routing Problem** o VRP. Es decir, se busca asignar municipios a vehiculos y ordenar visitas para servir todos los nodos respetando restricciones.

En este proyecto, la restriccion principal es la **jornada efectiva de trabajo**. Una ruta no debe superar el maximo de minutos disponibles por vehiculo.

Tambien se distingue entre vehiculos diesel y electricos:

- los diesel no tienen una restriccion de autonomia especifica en el modelo;
- los electricos tienen un limite maximo de kilometros por jornada.

La capacidad fisica de las furgonetas no actua como restriccion dura. Esto es deliberado y esta documentado: el modelo se centra en tiempo de trabajo y rango electrico.

El solver intenta usar rutas factibles. En la practica, se prioriza reducir vehiculos usados y despues mejorar distancia/tiempo segun la estrategia seleccionada.

## 8. Estrategias de solucion de rutas

La app permite elegir distintas estrategias de busqueda. No cambian el objetivo del proyecto, pero sirven para sensibilidad y comparacion tecnica.

Entre ellas aparecen:

- vecino mas cercano;
- barrido o sweep;
- savings de Clarke-Wright;
- insercion paralela;
- Christofides como referencia heuristica.

Estas tecnicas no garantizan que se este reproduciendo la operacion real exacta. Sirven para construir soluciones razonables del problema de reparto con los datos disponibles.

## 9. Split delivery y rutas dedicadas

Algunos municipios pueden concentrar tanta demanda que mezclarlos con rutas normales distorsionaria el calculo. Para esos casos se usa una logica de **rutas dedicadas**.

La idea es separar ciertos nodos grandes antes de resolver el VRP general:

- se asignan viajes especificos a esos nodos;
- el resto de la demanda queda como demanda residual;
- el VRP se ejecuta sobre la parte restante.

Esto permite que el solver no intente resolver todo como si cada municipio tuviera una escala parecida.

## 10. Trailers

Los trailers son una alternativa para nodos grandes. Si estan activados, pueden sustituir parte de las rutas dedicadas de furgoneta.

Conceptualmente, el trailer se usa cuando tiene sentido consolidar gran volumen en menos viajes. El modelo incorpora capacidad de trailer y tiempo de descarga, pero sigue manteniendo la logica general de jornada y tiempos.

Los trailers no convierten el modelo en una simulacion completa de transporte pesado. Son una capa practica para tratar municipios sobredimensionados.

## 11. Localizacion del centro

El bloque de localizacion intenta responder donde tendria sentido situar un centro desde un punto de vista logistico.

Usa varias tecnicas:

- **centro de gravedad ponderado**: calcula una posicion media usando poblacion como peso;
- **minimizacion de distancia total**: busca el punto que reduce la suma ponderada de distancias;
- **minimax**: busca reducir la peor distancia ponderada;
- **k-mediana**: agrupa nodos y obtiene referencias tipo mediana;
- **centro geografico**: referencia espacial simple.

Estas tecnicas producen puntos matematicos. No significan automaticamente que exista una parcela disponible ni que construir alli sea viable.

Por eso el proyecto distingue entre:

- referencias matematicas continuas;
- candidatos existentes como SVQ1;
- DQA4 como referencia operativa actual de ultima milla;
- un centro nuevo o intermedio como alternativa de comparacion.

## 12. Comparacion de candidatos de ubicacion

La decision de ubicacion no se toma solo por el punto matematico. El modelo compara candidatos con metricas homogeneas:

- distancia media ponderada;
- distancia total ponderada;
- distancia maxima;
- tiempo medio si hay matriz de tiempos disponible;
- tiempo maximo si aplica.

La alternativa "nuevo centro/intermedio" se selecciona automaticamente comparando metodos de localizacion, SVQ1, DQA4 y el punto medio SVQ1-DQA4. El criterio actual principal es la menor distancia media ponderada.

Si el candidato elegido es un nodo existente, se usa su fila en las matrices de distancia y tiempo. Si es un punto continuo, se crea un **deposito virtual**:

- las distancias depot-nodo se estiman con distancia recta tipo Haversine;
- los tiempos se estiman usando el ratio interno minutos/km de la matriz existente;
- las distancias entre municipios ya existentes no se modifican.

Esto permite explorar una ubicacion intermedia sin introducir datos externos de carreteras.

## 13. Interpretacion de DQA4

DQA4 es una pieza delicada del proyecto. En la situacion actual, funciona como centro de ultima milla para el flujo analizado.

Pero el modelo no debe interpretar que DQA4 desaparece totalmente. El enunciado habla del flujo SVQ1 -> DQA4, no de todos los flujos que pueda manejar DQA4.

Por eso:

- la estructura actual mantiene DQA4 como salida de ultima milla;
- SVQ1 ampliado evalua que pasaria si el flujo analizado saliera desde SVQ1;
- el centro intermedio evalua una alternativa de salida distinta;
- los ahorros ligados a DQA4 son parciales, atribuibles o liberables, no cierre total.

El parametro conservador de actividad atribuible de DQA4 parte del 10% en el modelo avanzado.

## 14. Economia: que se calcula

El bloque economico traduce las alternativas a magnitudes financieras.

Calcula, entre otros conceptos:

- coste actual anual;
- coste de transferencias SVQ1-DQA4;
- CAPEX base de inversion;
- CAPEX de transicion;
- CAPEX total;
- ahorro bruto anual;
- nuevo OPEX anual;
- ahorro neto anual;
- payback;
- VAN;
- TIR;
- resultados pesimistas.

El objetivo no es solo decir "cuanto cuesta", sino separar componentes para entender de donde sale la viabilidad.

## 15. CAPEX, OPEX y ahorro neto

**CAPEX** es inversion inicial: ampliacion, tecnologia, sistemas, formacion o mitigaciones que se pagan como esfuerzo de implantacion.

**OPEX** es coste recurrente anual: seguros, apoyo al transporte, incentivos recurrentes, costes de operacion o gastos anuales.

El ahorro bruto representa lo que la alternativa podria ahorrar antes de incorporar nuevos costes recurrentes. El ahorro neto descuenta esos OPEX nuevos.

Conceptualmente:

```text
ahorro neto anual = ahorro bruto anual - nuevo OPEX anual
```

Esta separacion es importante porque una alternativa puede parecer atractiva por ahorro bruto, pero perder fuerza si exige demasiado coste recurrente.

## 16. Payback, VAN y TIR

El **payback** mide cuantos anos hacen falta para recuperar la inversion con el ahorro neto anual.

El **VAN** o valor actual neto descuenta los flujos futuros a una tasa de descuento. Sirve para comparar si el proyecto crea valor bajo un horizonte temporal.

La **TIR** es la tasa interna de retorno aproximada. Ayuda a leer la rentabilidad relativa de la inversion.

El proyecto tambien calcula un escenario pesimista:

- aumenta el CAPEX con un multiplicador de sobrecoste;
- reduce los ahorros con un multiplicador conservador.

Asi se evita defender una alternativa solo por su caso optimista.

## 17. Puente entre rutas y economia

El modelo economico base viene del enunciado y de los parametros financieros. Ademas, el proyecto incorpora un puente operativo-economico.

Ese puente toma resultados agregados de rutas:

- numero total de rutas;
- rutas VRP;
- rutas dedicadas;
- rutas con trailer;
- distancia total;
- tiempo total;
- vehiculos diesel y electricos;
- paquetes servidos.

Luego los interpreta segun la alternativa:

- estructura actual;
- SVQ1 ampliado;
- centro nuevo/intermedio.

El puente no cambia el solver ni sus restricciones. Solo traduce resultados logisticos a una lectura economica complementaria: ahorro por transferencia eliminada o reducida, posible coste liberable parcial de DQA4 y advertencias de interpretacion.

## 18. Costes laborales y recursos humanos

La unificacion afecta a personas, especialmente a empleados vinculados a DQA4. El modelo laboral separa:

- costes puntuales de transicion;
- costes anuales recurrentes;
- riesgos laborales esperados;
- aceptabilidad de la politica laboral.

Ejemplos de medidas:

- formacion;
- incentivos;
- transporte corporativo;
- subsidio de transporte publico;
- compensacion unica;
- inclusion o no de costes regulatorios como incrementales.

La aceptabilidad laboral se clasifica de forma simple segun el coste de primer ano mas el riesgo residual. No es una encuesta real ni una prediccion social, sino una forma trazable de comparar politicas.

## 19. Riesgo laboral residual

Los riesgos laborales principales proceden del enunciado:

- renuncias;
- resistencia al cambio;
- conflictos sindicales.

Cada riesgo tiene:

```text
coste esperado = probabilidad x impacto
```

Las medidas de apoyo reducen probabilidades de forma documentada. Por ejemplo, transporte, incentivos o formacion pueden reducir parte del riesgo residual.

El resultado no elimina el riesgo. Lo convierte en una magnitud comparable entre escenarios.

## 20. Cronograma y estacionalidad

El cronograma modela la transicion por meses. No trabaja con fechas reales ni dias exactos, sino con un calendario discreto.

Las fases base son:

- preparacion;
- construccion;
- migracion;
- finalizacion.

Tambien se controlan hitos criticos:

- acuerdo con sindicatos;
- construccion terminada;
- sistemas funcionando;
- migracion completa.

Cada mes tiene un multiplicador estacional. Los meses de octubre, noviembre y diciembre son especialmente sensibles porque coinciden con el pico de demanda.

El cronograma genera advertencias cuando fases o hitos criticos caen en meses de alto riesgo. Estas advertencias son informativas: no deciden por si solas la viabilidad, pero alimentan la lectura de riesgo.

## 21. Riesgos generales del proyecto

El modelo de riesgos agrupa categorias:

- operativo;
- tecnologico;
- laboral;
- financiero;
- cronograma;
- legal/sindical.

Cada riesgo parte de una probabilidad base y un impacto base. Despues se aplican modificadores segun decisiones del escenario.

Por ejemplo:

- muchas rutas aumentan riesgo operativo;
- temporada alta aumenta riesgo operativo;
- inversion basica puede aumentar riesgo tecnologico;
- sistemas de respaldo reducen riesgo tecnologico;
- ausencia de apoyo laboral aumenta riesgo laboral;
- centro nuevo/intermedio puede aumentar riesgo financiero;
- hitos en octubre-diciembre aumentan riesgo de cronograma;
- transicion por fases reduce parte del riesgo.

La salida principal es el coste esperado residual:

```text
riesgo residual = probabilidad residual x impacto residual
```

Esto permite comparar escenarios no solo por ahorro, sino tambien por exposicion.

## 22. Escenarios

El proyecto integra los bloques anteriores mediante escenarios.

Un escenario combina decisiones como:

- centro operativo elegido;
- opcion de inversion;
- apoyo laboral;
- uso de formacion;
- uso de incentivos;
- implantacion por fases;
- sistemas de respaldo;
- mes de inicio;
- porcentaje atribuible de DQA4.

El resultado de un escenario agrupa:

- resultado economico;
- resumen operativo si hay rutas calculadas;
- resultado laboral;
- cronograma;
- riesgos;
- advertencias;
- interpretacion breve.

La comparacion guiada genera escenarios predefinidos o combinaciones por ejes. La viabilidad preliminar se etiqueta de forma transparente como favorable, condicionada o debil, pero no pretende ser una recomendacion automatica definitiva.

## 23. Almacen y layout ABC

El proyecto tambien contiene un bloque de almacen, reimplementado desde los scripts MATLAB.

Este bloque calcula:

- area total;
- area robotizada;
- area util;
- numero de estanterias;
- huecos por estanteria;
- capacidad teorica y real;
- reparto ABC;
- coste logistico de layout.

El sistema ABC clasifica productos o ubicaciones segun importancia de movimiento:

- A: pocos productos o zonas con muchos movimientos;
- B: importancia intermedia;
- C: muchos productos o zonas con menos movimiento.

El layout usa un indice de distancia o coste desde puertas de entrada/salida. En tres plantas incorpora penalizacion vertical, porque mover productos entre plantas no cuesta lo mismo que moverse en una planta.

El bloque permite comparar ABC por planta frente a ABC global optimizado. Aun asi, en la hoja de ruta actual el layout funciona como justificacion posterior o comparacion visual, no como condicion principal para decidir los escenarios.

## 24. Que calcula ya el proyecto

Actualmente el proyecto calcula o muestra:

- demanda por municipio a partir de poblacion;
- calibracion de demanda con volumen diario objetivo;
- efecto de estacionalidad;
- tiempos de servicio por nodo;
- rutas dedicadas y rutas VRP;
- uso de vehiculos diesel y electricos;
- restricciones de jornada y autonomia electrica;
- horarios aproximados de ruta;
- mapas y tablas operativas;
- tecnicas de localizacion y comparacion de candidatos;
- seleccion automatica de nuevo centro/intermedio;
- economia estructurada por CAPEX, OPEX, ahorro neto, VAN y TIR;
- escenario pesimista;
- costes de flota parametrizados;
- costes y riesgos laborales;
- cronograma mensual con advertencias estacionales;
- riesgos residuales dependientes de decisiones;
- comparacion guiada de escenarios.

## 25. Que se pretende calcular o mejorar mas adelante

La hoja de ruta apunta a mejorar la sintesis final, no a cambiar la naturaleza del modelo.

Los objetivos futuros son:

- definir criterios explicitos para una recomendacion final;
- mantener separada la recomendacion de los calculos base;
- conectar mejor layout y almacen con escenarios ya elegidos;
- usar el bloque de almacen como apoyo visual o justificativo;
- hacer una simplificacion academica final para presentacion.

No esta previsto convertir el modelo en una prediccion real de Amazon ni introducir datos externos sin autorizacion.

## 26. Relacion minima con el codigo

La implementacion esta organizada en modulos, pero el significado del proyecto es conceptual:

- `src/demand.py` calcula demanda y tiempos de servicio.
- `src/pipeline.py` encadena demanda, split delivery, VRP y horarios.
- `src/vrp_solver.py`, `src/split_delivery.py`, `src/trailer.py` y `src/fleet.py` sostienen el bloque de rutas.
- `src/location_solver.py` calcula metodos de localizacion y candidatos.
- `src/economics_model.py` agrupa economia, flota, puente logistico-economico y recursos humanos.
- `src/timeline_model.py` modela el calendario mensual.
- `src/risk_model.py` calcula riesgos residuales.
- `src/scenario_model.py` y `src/scenario_comparator.py` integran escenarios.
- `src/warehouse_model.py` contiene dimensionamiento y layout ABC.
- `app.py` y `src/project_sections.py` presentan todo en Streamlit.

La separacion importante es que la logica de negocio vive en `src/` y la interfaz solo organiza, muestra y permite configurar resultados.

## 27. Lectura final del modelo

El proyecto no dice simplemente "unificar es bueno" o "unificar es malo". Construye una comparacion razonada:

- si la demanda estimada genera rutas asumibles;
- si el cambio de deposito empeora o mejora distancias y tiempos;
- si los ahorros compensan la inversion;
- si el personal afectado tiene una politica de apoyo razonable;
- si la transicion evita meses criticos;
- si los riesgos residuales son aceptables;
- si una alternativa mantiene coherencia entre operacion, economia y personas.

La decision final debe apoyarse en ese equilibrio. La unificacion puede parecer atractiva por ahorro y simplificacion, pero solo es defendible si se controlan tres factores centrales: continuidad del servicio, gestion laboral e integracion tecnologica.
