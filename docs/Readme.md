# Documentación

Esta carpeta contiene la documentación viva del proyecto. Su función es dejar
claros los supuestos, el diseño de los modelos y las decisiones de iteración que
acompañan a la app Streamlit.

## Lectura recomendada

| Archivo | Uso |
| --- | --- |
| `project_brief.md` | Resumen del caso, alcance y foco de decisión. |
| `sintesis_enunciado_proyecto.md` | Síntesis del enunciado usada como contexto de verdad. |
| `assumptions.md` | Supuestos activos que no deben cambiarse sin documentarlo. |
| `architecture.md` | Separación entre app, datos, modelos, vistas y tests. |
| `logistics_model.md` | Demanda, VRP, flota, localización y alcance SVQ1 -> DQA4. |
| `finance_model.md` | CAPEX/OPEX, ahorros, VAN/TIR, payback y evolución económica. |
| `scenario_model.md` | Capa de escenarios, comparador y flujo guiado. |
| `risk_model.md` | Riesgos base, mitigaciones y modificadores por decisión. |
| `improvement_roadmap.md` | Roadmap técnico de mejoras ya hechas y pendientes. |
| `code_review.md` | Checklist rápido antes de revisar o fusionar cambios. |

## Apoyo y trazabilidad

| Archivo | Uso |
| --- | --- |
| `fulfillment.txt` | Notas conceptuales sobre fulfillment, layout y operación híbrida. |
| `calculos_economicos_flujo_guiado.md` | Trazabilidad de cálculos económicos del flujo guiado. |
| `planVersionesFuturas.md` | Nota histórica breve; el roadmap principal está en `PLANS.md` e `improvement_roadmap.md`. |

## Qué no es documentación principal

- Los PDF, presentaciones, borradores de memoria y salidas LaTeX son
  entregables o artefactos generados. No son necesarios para ejecutar la app.
- `report/`, `memoria_final/` y `docs/memorias/` quedan fuera del flujo normal
  del repositorio de aplicación.
- Si un dato o supuesto aparece solo en un entregable pesado, debe resumirse en
  Markdown antes de usarlo como referencia del modelo.

## Reglas de mantenimiento

- No inventar datos externos: usar el enunciado, `data/` y esta carpeta como
  fuentes trazables.
- Mantener cálculos reproducibles en `src/` y explicación de supuestos en
  Markdown.
- Actualizar `PLANS.md` cuando una iteración cambie alcance, roadmap o
  supuestos de modelo.
- Evitar duplicar documentos largos: preferir índices compactos y referencias
  a los archivos fuente.
