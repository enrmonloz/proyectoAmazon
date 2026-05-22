# data

Carpeta con datos tabulares de entrada para el proyecto. Incluye población, coordenadas, restricciones, distancias, tiempos de ruta y costes de vehículos.

## Contenido

| Archivo | Formato | Tamaño/estructura | Uso recomendado |
| --- | --- | --- | --- |
| `poblacion.csv` | CSV con separador `;` | 123 líneas, cabeceras: `Municipio`, `Población`, `Latitud (Y)`, `Longitud (X)`, `Restringe camion` | Fuente de municipios, población, coordenadas y restricciones de camión. Útil para análisis de localización, demanda y cobertura territorial. |
| `rutasDistTiempo_v2.csv` | CSV con separador `,` | Matriz larga OD de trabajo, cabeceras: `origen_id`, `destino_id`, `distancia_km`, `tiempo_min` | Matriz actual para rutas. Incluye centros candidatos de salida como nodos OD. |
| `rutasDistTiempo.csv` | CSV con separador `,` | 14.885 líneas, cabeceras: `origen_id`, `destino_id`, `distancia_km`, `tiempo_min` | Matriz histórica de distancias y tiempos entre los nodos originales. |
| `distanciasReales.xlsx` | Excel | Hoja `Matriz_Distancias`, rango aproximado `A1:DR122` | Matriz de distancias reales en formato ancho. Útil si se necesita una matriz completa para cálculo matricial o comprobación frente al CSV de rutas. |
| `Costes_Vehiculos_UNIFICAR_SVQ1.xlsx` | Excel | Hoja `CON REFORMA`, rango aproximado `A1:AA45` | Costes asociados a vehículos/furgonetas en el escenario con reforma o unificación SVQ1. Útil para costes logísticos y análisis económico. |

## Relación entre archivos

- `poblacion.csv` parece definir el universo de nodos o municipios, incluyendo centros como `SVQ1` y `DQA4`.
- `rutasDistTiempo_v2.csv` es la matriz de trabajo actual para rutas. Añade dos centros candidatos con población cero respecto a `poblacion.csv`; la app los alinea al cargar.
- `rutasDistTiempo.csv` usa identificadores numéricos (`origen_id`, `destino_id`) que corresponden al orden histórico de filas de `poblacion.csv`.
- `distanciasReales.xlsx` contiene una matriz de distancias en formato ancho; puede servir como fuente original o alternativa a `rutasDistTiempo.csv`.
- `Costes_Vehiculos_UNIFICAR_SVQ1.xlsx` está orientado a costes de flota y no a geolocalización.
- La app aplica un filtro lógico de área de servicio sobre los nodos agregados
  `Cádiz`, `Huelva`, `Málaga`, `Granada` y `Córdoba`. Por defecto, `Cádiz` y
  `Huelva` están activas; `Málaga`, `Granada` y `Córdoba` permanecen en los
  datos, pero se cargan con población filtrada 0 para no generar demanda.

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
2. Si se necesitan distancias o tiempos para rutas, usar `rutasDistTiempo_v2.csv` porque es la matriz OD de trabajo actual.
3. Si se necesita verificar una matriz completa de distancias, consultar `distanciasReales.xlsx`.
4. Si se necesita alimentar análisis económico de transporte, consultar `Costes_Vehiculos_UNIFICAR_SVQ1.xlsx`.
5. Antes de cruzar rutas con municipios, confirmar si se usa la matriz histórica
   o la v2; la v2 añade centros candidatos que la app alinea como demanda cero.

## Precauciones

- `poblacion.csv` incluye una marca BOM al inicio del archivo; al leerlo en Python puede convenir usar `encoding="utf-8-sig"`.
- Los CSV usan separadores distintos: `poblacion.csv` usa punto y coma; las
  matrices `rutasDistTiempo*.csv` usan coma.
- `rutasDistTiempo_v2.csv` contiene centros candidatos de rutas que no aparecen como filas físicas en `poblacion.csv`; la app los trata como nodos de demanda cero.
- El filtro de provincias agregadas no borra filas de `poblacion.csv`, no
  reordena nodos y no reconstruye `rutasDistTiempo_v2.csv`; solo cambia la
  población efectiva de los nodos agregados no seleccionados.
- El filtro actúa sobre esos nodos agregados, no sobre municipios detallados ni
  sobre una columna `Provincia`.
- Las coordenadas están en columnas llamadas `Latitud (Y)` y `Longitud (X)`.
- `Restringe camion` parece una variable binaria; validar su significado antes de usarla como restricción dura.
- Los Excel pueden contener formato y celdas vacías; al extraerlos automáticamente conviene inspeccionar cabeceras reales y rangos antes de convertirlos.
