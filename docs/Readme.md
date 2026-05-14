# docs

Carpeta de documentación y apuntes textuales del proyecto. Está pensada para recoger contexto, decisiones de diseño y notas de trabajo que ayudan a interpretar los cálculos y el código.

## Contenido

| Archivo | Tipo | Uso recomendado |
| --- | --- | --- |
| `fulfillment.txt` | Apuntes de proyecto | Leer para entender las hipótesis pendientes y el razonamiento sobre fulfillment, última milla, integración de procesos y layout. |

## Archivo ignorado

`docs/.gitkeep` solo existe para mantener la carpeta en Git. No contiene información útil para análisis, generación de documentación ni toma de decisiones.

## Guía rápida para una IA

1. Leer `fulfillment.txt` si se necesita contexto conceptual sobre el rediseño del centro, la integración fulfillment-última milla o las hipótesis del sistema ABC.
2. Usar esta carpeta como fuente de notas cualitativas, no como fuente de datos numéricos finales.
3. Para cálculos reproducibles, ir a `codes/`.
4. Para datos tabulares de entrada, ir a `data/`.

## Observaciones

Las notas de `fulfillment.txt` incluyen ideas en estado de trabajo: huecos de reserva, ocupación del 67%, distribución ABC en tres plantas, tiempos relativos por planta y procesos que cambian al unificar última milla con fulfillment. Conviene tratarlas como contexto y no como resultados validados por sí solos.
