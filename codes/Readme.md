# codes

Carpeta con el código de cálculo y simulación del proyecto. Contiene principalmente scripts MATLAB para análisis económico, dimensionamiento de almacén y comparación de estrategias de distribución ABC.

## Estructura

| Ruta | Tipo | Uso recomendado |
| --- | --- | --- |
| `Economia.m` | Script MATLAB | Análisis económico del rediseño SVQ1 + DQA4. Calcula costes actuales, ahorros, CAPEX, OPEX, payback, VAN/TIR y comparación de alternativas de inversión. |
| `almacen_amazon/` | Subcarpeta MATLAB | Modelos de dimensionamiento y optimización del layout del almacén con zonas ABC. |

La lógica principal de estos scripts se ha reimplementado también en Python
(`src/warehouse_model.py`, `src/economics_model.py` y `src/project_sections.py`)
para poder analizar escenarios con parámetros ajustables desde Streamlit, sin
depender de ejecutar MATLAB durante la presentación.

## Scripts principales

### `Economia.m`

Script largo de análisis financiero del proyecto de unificación. Trabaja con datos introducidos directamente en el código y produce resultados por consola y gráficos.

Usar cuando se necesite:

- Entender la viabilidad económica de unificar SVQ1 y DQA4.
- Revisar costes actuales de centros separados.
- Comparar opciones de inversión básica, estándar y premium.
- Calcular ahorros anuales, CAPEX adicional, OPEX recurrente, payback, VAN, TIR y sensibilidad.

Evitar si solo se busca información de layout físico o distribución ABC.

Valores por defecto que reproduce la app:

- Coste actual de dos centros: 56,39 M€/año.
- Ahorro anual estimado: 6,69-9,89 M€/año.
- Opción seleccionada: Estándar.
- CAPEX estándar base: 28,50 M€.
- CAPEX estándar con transición: 34,40 M€.
- OPEX nuevo recurrente: 0,977 M€/año.
- Ahorro neto anual: 5,723 M€/año.
- VAN 10 años: 5,80 M€; TIR aproximada: 10,5%.

## Subcarpeta `almacen_amazon`

| Archivo | Tipo | Propósito |
| --- | --- | --- |
| `Almacen_dimension.m` | Script MATLAB | Calcula dimensiones base del almacén: área total, área robotizada, número de estanterías, huecos, capacidad por estantería, ocupación del 67% y reparto ABC. |
| `Almacen_1floor.m` | Script MATLAB | Diseña una única planta usando el método del índice `f`, basado en distancia Manhattan ponderada desde puertas de entrada/salida. Genera mapas ABC y mapas de calor. |
| `Almacen_3floor.m` | Script MATLAB | Extiende el método `f` a tres plantas, añadiendo penalización vertical por transporte en cinta. Genera zonificación ABC por planta y mapas de coste. |
| `Almacen_vs.m` | Script MATLAB | Compara dos estrategias: ABC individual por planta frente a ABC global optimizado en 3D. Usa pesos de movimiento tipo Pareto y estima mejora porcentual. |
| `Almacen_resultado_variable_3.m` | Script MATLAB | Realiza una búsqueda paramétrica sobre porcentajes ABC y movimientos para encontrar mejores configuraciones individuales y globales. |
| `resultadosAlmacen.txt` | Resultado/documentación | Resumen textual de los scripts de almacén, hipótesis de capacidad y conclusión de eficiencia. No es código ejecutable. |

Nota de integración Python: la app distingue presets para `Almacen_1floor.m`,
`Almacen_3floor.m` y `Almacen_vs.m`, ya que no comparten exactamente la misma
configuración de puertas. El preset de `Almacen_3floor.m` mantiene la tercera
puerta en la columna 50 y muestra explícitamente la penalización vertical
creciente por planta (12, 24 y 36 celdas con los parámetros base).

Valores por defecto que reproduce la app:

- Edificio de 300 x 150 m y Robotics Area de 20.000 m² por planta.
- 5.000 estanterías por planta y 15.000 estanterías totales.
- 56 huecos por estantería y 12 paquetes por hueco.
- Ocupación real asumida del 67%.
- Capacidad total de 6.753.600 paquetes en tres plantas.
- Reparto ABC: A 15%, B 15%, C 70%; movimientos A 80%, B 15%, C 5%.
- La estrategia ABC global 3D mejora un 9,70% el coste logístico diario frente
  al ABC independiente por planta.

## Relación con datos de vehículos

El Excel `../data/Costes_Vehiculos_UNIFICAR_SVQ1.xlsx` no alimenta directamente
los scripts MATLAB, pero sí complementa el análisis económico en la app Python.
La hoja `CON REFORMA` se ha traducido a un modelo parametrizable de costes de
flota: se pueden cambiar vehículos y costes unitarios, manteniendo estos valores
por defecto:

- Furgonetas propias: 6,874 M€/año.
- Furgonetas subcontratadas: 2,295 M€/año.
- Total furgonetas: 9,169 M€/año.
- Trailers: 0,994 M€/año.
- Total rutas con SVQ1 unificado: 10,162 M€/año.
- Sobrecoste anual frente al escenario sin unificar: 0,122 M€/año.

## Dependencias y ejecución

- Lenguaje principal: MATLAB/Octave.
- Los scripts son independientes entre sí y usan variables definidas dentro de cada archivo.
- Los scripts de layout generan figuras con `figure`, `imagesc`, `bar`, `colormap` y `colorbar`.
- No se observa lectura directa de `data/` en estos scripts; muchos datos están codificados como constantes.

## Guía rápida para una IA

1. Para entender capacidades físicas, leer primero `almacen_amazon/Almacen_dimension.m`.
2. Para entender la lógica de zonificación en una planta, leer `almacen_amazon/Almacen_1floor.m`.
3. Para entender el modelo con tres plantas y penalización vertical, leer `almacen_amazon/Almacen_3floor.m`.
4. Para justificar qué estrategia es mejor, leer `almacen_amazon/Almacen_vs.m` y después `almacen_amazon/resultadosAlmacen.txt`.
5. Para explorar sensibilidad de porcentajes ABC/movimientos, leer `almacen_amazon/Almacen_resultado_variable_3.m`.
6. Para análisis financiero, leer `Economia.m`; no mezclarlo con los scripts de almacén salvo que se busque una visión integral del proyecto.

## Qué evitar

- No usar `resultadosAlmacen.txt` como fuente primaria si se necesita reproducibilidad: preferir los `.m`.
- No asumir que los Excel/CSV de `data/` alimentan automáticamente estos scripts; revisar manualmente antes de conectar datos externos.
- No ejecutar todos los scripts a ciegas si solo se necesita una cifra concreta, porque varios abren figuras y repiten cálculos similares.
