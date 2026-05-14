# data

Carpeta con datos tabulares de entrada para el proyecto. Incluye población, coordenadas, restricciones, distancias, tiempos de ruta y costes de vehículos.

## Contenido

| Archivo | Formato | Tamaño/estructura | Uso recomendado |
| --- | --- | --- | --- |
| `poblacion.csv` | CSV con separador `;` | 123 líneas, cabeceras: `Municipio`, `Población`, `Latitud (Y)`, `Longitud (X)`, `Restringe camion` | Fuente de municipios, población, coordenadas y restricciones de camión. Útil para análisis de localización, demanda y cobertura territorial. |
| `rutasDistTiempo.csv` | CSV con separador `,` | 14.885 líneas, cabeceras: `origen_id`, `destino_id`, `distancia_km`, `tiempo_min` | Matriz larga de distancias y tiempos entre orígenes/destinos identificados por índice. Útil para optimización de rutas, asignación y análisis de distancia mínima. |
| `distanciasReales.xlsx` | Excel | Hoja `Matriz_Distancias`, rango aproximado `A1:DR122` | Matriz de distancias reales en formato ancho. Útil si se necesita una matriz completa para cálculo matricial o comprobación frente al CSV de rutas. |
| `Costes_Vehiculos_UNIFICAR_SVQ1.xlsx` | Excel | Hoja `CON REFORMA`, rango aproximado `A1:AA45` | Costes asociados a vehículos/furgonetas en el escenario con reforma o unificación SVQ1. Útil para costes logísticos y análisis económico. |

## Relación entre archivos

- `poblacion.csv` parece definir el universo de nodos o municipios, incluyendo centros como `SVQ1` y `DQA4`.
- `rutasDistTiempo.csv` usa identificadores numéricos (`origen_id`, `destino_id`) que probablemente corresponden al orden de filas de `poblacion.csv`.
- `distanciasReales.xlsx` contiene una matriz de distancias en formato ancho; puede servir como fuente original o alternativa a `rutasDistTiempo.csv`.
- `Costes_Vehiculos_UNIFICAR_SVQ1.xlsx` está orientado a costes de flota y no a geolocalización.

## Resumen del Excel de costes

La app Python no ejecuta las fórmulas del Excel en tiempo real. En su lugar,
replica su estructura principal como modelo parametrizable de costes de flota,
con estas cifras como valores por defecto:

| Concepto | Valor |
| --- | ---: |
| Total furgonetas propias | 6,874 M€/año |
| Total furgonetas subcontratadas | 2,295 M€/año |
| Total furgonetas | 9,169 M€/año |
| Total trailers | 0,994 M€/año |
| Total rutas con SVQ1 unificado | 10,162 M€/año |
| Sobrecoste anual vs. sin unificar | 0,122 M€/año |

## Guía rápida para una IA

1. Si se necesita geografía o demanda, empezar por `poblacion.csv`.
2. Si se necesitan distancias o tiempos para algoritmos, usar `rutasDistTiempo.csv` porque está en formato largo y es más fácil de procesar automáticamente.
3. Si se necesita verificar una matriz completa de distancias, consultar `distanciasReales.xlsx`.
4. Si se necesita alimentar análisis económico de transporte, consultar `Costes_Vehiculos_UNIFICAR_SVQ1.xlsx`.
5. Antes de cruzar rutas con municipios, confirmar que los IDs de `rutasDistTiempo.csv` coinciden con el índice de filas de `poblacion.csv`.

## Precauciones

- `poblacion.csv` incluye una marca BOM al inicio del archivo; al leerlo en Python puede convenir usar `encoding="utf-8-sig"`.
- Los CSV usan separadores distintos: `poblacion.csv` usa punto y coma; `rutasDistTiempo.csv` usa coma.
- Las coordenadas están en columnas llamadas `Latitud (Y)` y `Longitud (X)`.
- `Restringe camion` parece una variable binaria; validar su significado antes de usarla como restricción dura.
- Los Excel pueden contener formato y celdas vacías; al extraerlos automáticamente conviene inspeccionar cabeceras reales y rangos antes de convertirlos.
