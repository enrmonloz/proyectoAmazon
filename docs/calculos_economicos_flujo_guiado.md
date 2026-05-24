# Calculos economicos del Flujo guiado

Este documento explica el bloque **Flujo guiado / Analisis economico**. Es una
lectura academica de viabilidad, no una prevision real de Amazon.

## 1. Referencia actual

La situacion actual se mantiene como fila de referencia:

| Bloque actual | Coste anual |
| --- | ---: |
| SVQ1 | 36,20 M€ |
| DQA4 | 18,10 M€ |
| Transferencia SVQ1-DQA4 | 1,99 M€ |
| **Total actual** | **56,29 M€** |

DQA4 no se interpreta como cierre total. Sigue siendo la referencia de ultima
milla del flujo analizado y puede seguir operando para otros flujos.

## 2. Opciones de inversion

El FG compara siempre las tres opciones del enunciado:

| Opcion | Coste inicial base | Ahorro anual base |
| --- | ---: | ---: |
| Basica | 18,30 M€ | 4,70 M€/ano |
| Estandar | 28,50 M€ | 6,70 M€/ano |
| Premium | 42,70 M€ | 8,90 M€/ano |

El ahorro anual base ya incluye transferencia, personal, energia e
instalaciones segun el enunciado. Por tanto, **no se suma aparte** la
transferencia de 1,99 M€/ano dentro de los flujos de inversion. La transferencia
se muestra solo como dato explicativo de la referencia actual.

## 3. Rutas

Las rutas entran solo como diferencial contra DQA4:

```text
diferencial_rutas =
    coste_anual_rutas(alternativa) - coste_anual_rutas(DQA4)
```

Si el diferencial es positivo, reduce el ahorro operativo anual. Si es
negativo, mejora el flujo. El modelo no usa la penalizacion fija del script
MATLAB ni lee costes de rutas desde Excel; reutiliza los resultados calculados
por `src/route_costs.py`.

## 4. Costes iniciales y recurrentes

El coste inicial total es:

```text
coste_inicial_total = CAPEX_base + costes_iniciales_transicion
```

Costes iniciales de transicion:

| Concepto | Importe |
| --- | ---: |
| Formacion | 1,56 M€ |
| Perdida valor DQA4 | 0,523 M€ |
| Compensacion unica empleados | 0,45 M€ |
| Implementacion por fases | 2,20 M€ |
| Sistemas de respaldo | 1,80 M€ |
| Seguros especiales | 0,45 M€ |
| Incentivos empleados | 0,68 M€ |

El OPEX anual recurrente del FG incluye solo:

| Concepto | Importe |
| --- | ---: |
| Subsidio transporte publico | 187.000 €/ano |
| Transporte corporativo | 441.000 €/ano |
| Diferencial anual de rutas | Calculado por la app |

Seguros, incentivos, formacion, compensacion y perdida de valor de DQA4 se
cargan como coste inicial cuando estan activados, no como OPEX anual.

## 5. Escenarios O/P/P

Para cada opcion de inversion se calculan tres escenarios:

| Escenario | Ahorro | Curva | Riesgos |
| --- | ---: | --- | --- |
| Optimista | ahorro base x 1,20 | 100% desde ano 1 | sin golpe |
| Probable | ahorro base | 75% ano 1, 100% despues | sin golpe fuerte |
| Pesimista | ahorro base x 0,80 | 50% ano 1, 75% ano 2, 100% despues | riesgos residuales |

Todos los escenarios restan el OPEX anual recurrente y el diferencial de rutas.

## 6. Riesgos residuales

El FG muestra el riesgo esperado base y el residual tras mitigaciones:

| Riesgo | Base | Mitigacion |
| --- | ---: | --- |
| Interrupcion servicio | 30% x 8,5 M€ | fases reducen 75% |
| Empleados | 45% x 2,1 M€ | incentivos reducen 70% |
| Construccion | 35% x 30% del CAPEX base | sin mitigacion directa |
| Tecnologia | 30% x 3,2 M€ | respaldo reduce 85% |
| Legal | 15% x 3,0 M€ | seguros reducen 60% |

Los riesgos no se cargan al escenario probable para evitar doble conteo. Solo
golpean el pesimista:

- construccion residual en el ano 0;
- riesgos operativos residuales en el ano 1.

El PERT incorpora parte de ese golpe al combinar los flujos.

## 7. Flujo PERT e indicadores

El flujo PERT se calcula ano a ano:

```text
flujo_PERT[t] =
    (flujo_optimista[t] + 4 * flujo_probable[t] + flujo_pesimista[t]) / 6
```

Sobre ese flujo se calculan:

- VAN PERT;
- TIR PERT, si existe y converge;
- payback PERT simple acumulado;
- VAN pesimista.

Si la TIR no tiene cambio de signo o no converge, la app muestra `—`. Si el
payback no recupera la inversion, tambien se muestra `—`.

## 8. Coste anual estimado

El coste anual estimado no incluye CAPEX ni costes iniciales:

```text
coste_anual_estimado_PERT =
    coste_actual_total - ahorro_operativo_anual_PERT_medio
```

El ahorro operativo anual PERT medio se calcula con los flujos anuales PERT,
excluyendo el ano 0.

## 9. Matriz de decision

Para cada alternativa logistica distinta de DQA4, el FG compara Basica,
Estandar y Premium con una matriz simple:

- mayor VAN PERT;
- menor payback PERT;
- mayor VAN pesimista;
- menor coste inicial total.

La opcion con mas criterios ganados se muestra como mejor opcion de inversion.
No se fuerza que gane una opcion concreta.
