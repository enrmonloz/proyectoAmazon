Perfecto. Entonces fijamos esta idea:

> De momento no vamos a tocar capacidad física de vehículos ni métricas técnicas adicionales. Vamos a construir una hoja de ruta de mejoras del código orientada al objetivo final: comparar escenarios de viabilidad de unificación.

El proyecto ya tiene cuatro grandes bloques funcionales: rutas, localización, almacén y economía . La mejora no consiste en hacer cada pestaña más compleja por separado, sino en preparar cada bloque para que, al final, pueda alimentar una comparación común de escenarios.

El documento del caso marca como objetivo decidir si conviene unificar SVQ1 y DQA4, con qué inversión, ubicación, medidas laborales, riesgos y cronograma. 

---

# Índice maestro de mejoras del código

## 0. Base ya iniciada: demanda

**Estado:** ya mejorada.

Se ha avanzado en el módulo de demanda: ahora se puede trabajar con penetración, volumen objetivo y estacionalidad. Esto encaja bien porque el README ya refleja que los paquetes por nodo se calculan desde población, con opción de calibración por volumen diario y multiplicador estacional .

**No seguiría refinando esto ahora**, salvo pequeñas limpiezas.

---

# 1. Limpieza de arquitectura y separación de responsabilidades

## Objetivo

Asegurar que cada módulo tenga una responsabilidad clara y que la UI no concentre lógica de negocio.

## Qué mejorar

```text
app.py
→ debería encargarse de mostrar y recoger inputs.

src/*.py
→ deberían contener la lógica real del modelo.

pipeline.py
→ debería coordinar cálculos operativos, no resolver decisiones globales.
```

## Por qué importa

Antes de crear escenarios globales, necesitamos que los bloques sean reutilizables. Si la lógica está mezclada en Streamlit, luego será difícil comparar escenarios automáticamente.

## Prioridad

Alta, pero progresiva. No hace falta una gran reestructuración.

---

# 2. Validaciones y supuestos del modelo

## Objetivo

Crear una capa clara de supuestos y validaciones para que el modelo sea defendible.

## Qué mejorar

```text
- Validaciones de inputs.
- Mensajes de error claros.
- Supuestos documentados.
- Defaults coherentes.
- Separar dato real / supuesto / parámetro editable.
```

## Ejemplos

```text
Demanda:
- población como proxy de paquetes.

Rutas:
- el cuello de botella es tiempo de jornada, no volumen físico.

Flota:
- rango eléctrico como restricción dura.
- capacidad física no activa como restricción.

Economía:
- distinguir ahorro bruto, ahorro neto, CAPEX, OPEX y riesgo.
```

## Por qué importa

Esto evita que el código parezca “más exacto” de lo que realmente es. Para una memoria técnica, es mejor un supuesto claro que una falsa precisión.

---

# 3. Mejorar el bloque de localización

## Objetivo

Pasar de una localización teórica a una comparación útil para la decisión SVQ1 vs ubicación intermedia.

## Problema actual

El módulo de localización sirve para comparar técnicas matemáticas, pero el problema real no es solo encontrar un centro geométrico óptimo.

La decisión del caso es más concreta:

```text
- Expandir SVQ1.
- Crear ubicación intermedia.
```

## Qué mejorar

```text
1. Comparar ubicaciones candidatas.
2. Usar demanda estimada, no solo población.
3. Evaluar impacto en distancia/tiempo de reparto.
4. Mostrar trade-off:
   menor distancia a clientes vs mayor inversión/plazo.
```

## Resultado esperado

Una tabla tipo:

```text
Ubicación candidata | Distancia media | Tiempo medio | Coste estimado | Ventaja | Riesgo
```

## Prioridad

Muy alta. Es uno de los ejes de la decisión final.

---

# 4. Mejorar el bloque de economía

## Objetivo

Hacer que economía sea menos una calculadora aislada y más una base para escenarios.

## Problema actual

Economía usa valores parametrizados, lo cual está bien, pero todavía no depende mucho de decisiones operativas.

## Qué mejorar

```text
1. Separar claramente:
   - CAPEX.
   - OPEX.
   - costes de transición.
   - costes recurrentes.
   - ahorros brutos.
   - ahorros netos.
   - riesgos esperados.

2. Preparar economía para recibir:
   - opción de inversión.
   - ubicación.
   - estrategia de transición.
   - medidas laborales.
   - mitigaciones de riesgo.

3. Evitar que los ahorros sean una única cifra fija.
```

## Resultado esperado

Una función o modelo económico capaz de responder:

```text
Para este escenario concreto:
- inversión total
- ahorro neto anual
- payback
- VAN
- riesgo esperado
- coste en escenario pesimista
```

## Prioridad

Alta, pero después de ordenar localización y supuestos.

---

# 5. Mejorar recursos humanos como módulo propio o submodelo económico

## Objetivo

No tratar el impacto laboral como un texto suelto, sino como una parte cuantificable del escenario.

## Por qué importa

El documento insiste en que el éxito depende mucho de personas, continuidad del servicio e integración tecnológica. 

## Qué mejorar

```text
1. Modelar medidas laborales:
   - transporte corporativo.
   - subsidio transporte público.
   - compensación única.
   - incentivos.

2. Modelar costes:
   - formación.
   - regulación laboral.
   - rotación.
   - conflictos.

3. Asociar cada medida a:
   - coste.
   - efecto sobre riesgo.
   - efecto sobre aceptación.
```

## Resultado esperado

```text
LaborPolicyResult:
- coste anual
- coste único
- riesgo laboral residual
- comentario interpretativo
```

## Prioridad

Media-alta. Importante para el escenario final, pero se puede construir después de economía.

---

# 6. Mejorar riesgos

## Objetivo

Pasar de riesgos estáticos a riesgos dependientes del escenario.

## Problema actual

Tener una tabla de riesgos está bien, pero la probabilidad e impacto deberían cambiar según lo que se decida.

## Qué mejorar

```text
Riesgo de interrupción:
- baja si hay implementación por fases.
- sube si se migra en temporada alta.

Riesgo laboral:
- baja si hay incentivos/apoyo.
- sube si se cierra DQA4 rápido.

Riesgo tecnológico:
- baja con sistemas de respaldo.
- sube con inversión básica.

Riesgo financiero:
- sube con Premium o ubicación nueva.
```

## Resultado esperado

```text
RiskResult:
- probabilidad base
- impacto base
- mitigación aplicada
- coste esperado
- riesgo residual
```

## Prioridad

Alta antes del modelo global.

---

# 7. Mejorar cronograma y estacionalidad de transición

## Objetivo

Hacer que el calendario influya en la viabilidad del escenario.

## Problema actual

La estacionalidad ya afecta a la demanda, pero falta que afecte al cronograma de implantación.

## Qué mejorar

```text
1. Representar fases:
   - preparación
   - construcción
   - migración
   - finalización

2. Representar mes de inicio.

3. Detectar si hitos críticos caen en:
   - enero-marzo: favorable
   - octubre-diciembre: desfavorable

4. Penalizar escenarios con migración en Navidad.
```

## Resultado esperado

```text
TimelineResult:
- duración total
- hitos críticos
- meses de riesgo
- penalización por temporada alta
- recomendación de inicio
```

## Prioridad

Alta, porque conecta operaciones, riesgos y decisión.

---

# 8. Mejorar almacén/layout hacia centro unificado

## Objetivo

Que el módulo de almacén no sea solo almacenamiento ABC, sino que empiece a representar necesidades de un centro unificado.

## Qué mejorar

No ahora con mucho detalle, pero sí preparar el modelo para:

```text
- almacenamiento
- picking
- sortation
- staging de rutas
- muelles
- carga de furgonetas
- cargadores eléctricos
- devoluciones
- incidencias
```

## En esta fase

No haría una gran simulación de layout. Primero añadiría conceptos de capacidad por áreas o checklists de viabilidad.

## Resultado esperado

```text
WarehouseFeasibilityResult:
- capacidad almacenamiento
- capacidad operativa estimada
- necesidad de expansión
- compatibilidad con opción básica/estándar/premium
```

## Prioridad

Media. Importante, pero no lo tocaría antes de economía, localización y riesgos.

---

# 9. Conectar rutas con economía, sin cambiar el VRP

## Objetivo

Usar resultados del VRP como inputs económicos, sin añadir restricciones nuevas.

## Qué conectar

```text
Del VRP:
- número de rutas
- km totales
- tiempo total
- vehículos diésel usados
- vehículos eléctricos usados
- rutas dedicadas
- trailers

Hacia economía:
- coste de última milla
- diferencial frente al escenario actual
- sensibilidad por ubicación
```

## Qué NO hacer

No añadir capacidad física como restricción.

## Resultado esperado

```text
OperationalCostInput:
- total_distance_km
- total_time_min
- diesel_count
- electric_count
- trailer_count
- route_count
```

## Prioridad

Media-alta. Haría esto cuando economía esté más ordenada.

---

# 10. Crear estructura de escenarios

## Objetivo

Crear la pieza central que una todos los módulos.

## Esto sería el primer paso hacia el modelo global

Un escenario debería contener:

```text
ScenarioConfig:
- ubicación: SVQ1 / intermedia
- inversión: básica / estándar / premium
- demanda: baja / base / verano / pico
- transición: directa / por fases / con respaldo
- política laboral
- mitigaciones
- mes de inicio
```

Y devolver:

```text
ScenarioResult:
- resultado operativo
- resultado económico
- resultado laboral
- resultado de riesgos
- resultado de cronograma
- puntuación o recomendación
```

## Prioridad

Muy alta, pero no todavía. Antes hay que preparar los módulos para que puedan alimentar esto.

---

# 11. Comparador de escenarios

## Objetivo

Permitir comparar escenarios completos.

## Ejemplo

```text
Escenario A:
SVQ1 + estándar + fases + subsidio transporte + inicio enero

Escenario B:
SVQ1 + básica + transición rápida + sin apoyo laboral

Escenario C:
ubicación intermedia + premium + fases + incentivos
```

## Salida esperada

```text
Escenario | CAPEX | ahorro neto | payback | riesgo esperado | servicio | recomendación
```

## Prioridad

Después de `ScenarioConfig` y `ScenarioResult`.

---

# 12. Recomendación final

## Objetivo

Generar una conclusión defendible para la memoria.

No solo:

```text
El escenario con mayor VAN es X.
```

Sino:

```text
Recomendamos X porque:
1. Recupera inversión en plazo razonable.
2. Mantiene servicio dentro de un deterioro aceptable.
3. Controla los riesgos críticos de transición.
```

## Resultado esperado

```text
RecommendationResult:
- recomendar / no recomendar
- escenario elegido
- tres razones principales
- principales riesgos
- condiciones para que sea viable
```

## Prioridad

Última fase.

---

# Orden recomendado de trabajo

Yo seguiría este orden:

```text
0. Demanda calibrada y estacionalidad  [hecho]
1. Limpieza de supuestos y validaciones
2. Localización orientada a candidatos
3. Economía más estructurada por componentes
4. Recursos humanos como submodelo
5. Riesgos dependientes de decisiones
6. Cronograma con estacionalidad
7. Almacén/layout orientado a centro unificado
8. Conexión rutas → economía
9. ScenarioConfig / ScenarioResult
10. Comparador de escenarios
11. Recomendación final
```

---

# Qué haría como próxima iteración concreta

No tocaría vehículos ni métricas de ruta ahora.

La siguiente mejora más lógica sería:

## **Localización por candidatos**

Porque es independiente, útil y muy conectada al objetivo final.

Actualmente la localización existe como pestaña, pero la decisión real no es “qué técnica matemática da un punto óptimo”, sino:

```text
¿SVQ1 o ubicación intermedia?
```

Esa iteración prepararía el futuro comparador de escenarios sin tocar todavía economía global ni VRP.

La siguiente tarea podría llamarse:

```text
Mejorar localización para comparar ubicaciones candidatas orientadas a escenarios
```

Objetivo:

```text
Transformar la pestaña de localización desde una herramienta matemática descriptiva
a un módulo que ayude a decidir entre alternativas de ubicación para el centro unificado.
```

Ese sería el siguiente prompt que te generaría cuando quieras.
