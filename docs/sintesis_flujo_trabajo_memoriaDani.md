# Síntesis detallada del flujo de trabajo de `memoriaDani.pdf`

Este documento explica, con un enfoque para principiantes, el flujo de trabajo seguido en la memoria del proyecto sobre la posible unificación de los centros logísticos SVQ1 y DQA4 de Amazon en Sevilla.

La idea no es repetir todas las tablas ni los resultados numéricos de la memoria. El objetivo es entender cómo se razona el proyecto: qué pregunta se formula, qué datos se preparan, qué modelos se usan, qué significa cada fase y cómo se llega a una recomendación.

## 1. Idea general del proyecto

El proyecto estudia si tiene sentido unificar dos instalaciones logísticas que cumplen funciones distintas:

- SVQ1 funciona como un gran centro de distribución.
- DQA4 funciona como estación de entrega de última milla.

En la operativa actual, una parte de los paquetes pasa primero por SVQ1 y después se traslada a DQA4 para el reparto final. Esa transferencia entre centros genera una duplicidad: se mueve mercancía entre instalaciones antes de hacer la entrega al cliente.

La pregunta de fondo es:

> Si se elimina DQA4 como punto de reparto para esa operación y se reparte directamente desde SVQ1, ¿la simplificación compensa el empeoramiento logístico que puede aparecer al alejar el depósito de la demanda?

La memoria no responde a esta pregunta con una sola cuenta. La divide en varias capas:

1. Entender dónde está la demanda.
2. Estudiar qué ubicación sería buena desde un punto de vista geométrico.
3. Simular cómo cambiarían las rutas de reparto.
4. Traducir los efectos operativos a un modelo económico.
5. Analizar riesgos y medidas de mitigación.
6. Emitir una recomendación condicionada.

Esa separación es importante porque cada fase responde una pregunta distinta. Una ubicación puede ser buena geométricamente, pero no necesariamente barata. Una ruta puede ser peor operativamente, pero aun así la fusión podría ser rentable si elimina costes estructurales. Por eso el proyecto evita sacar conclusiones precipitadas.

## 2. Escenarios comparados

El primer paso consiste en definir qué alternativas se van a comparar.

La memoria trabaja con dos escenarios principales:

- Mantener DQA4 como punto de salida del reparto.
- Fusionar la operación de reparto en SVQ1.

En el primer escenario, la estación DQA4 sigue siendo el punto desde el que salen las furgonetas de última milla. En el segundo, esa función se traslada al emplazamiento de SVQ1.

El proyecto no plantea mover SVQ1 a otra ubicación. SVQ1 se considera una infraestructura grande, ya condicionada por suelo industrial, accesos y red de transporte de larga distancia. Por eso el análisis se centra en la función de DQA4: mantenerla como estación de entrega o absorber esa actividad en SVQ1.

Para principiantes, esta distinción es clave:

- No se está buscando "dónde debería estar todo Amazon en Sevilla".
- Se está comparando "desde dónde conviene hacer el reparto final de la demanda atribuida a DQA4".

## 3. Preparación de los datos de demanda

Antes de optimizar nada, el proyecto necesita representar la demanda. Como no se dispone de datos reales de pedidos por dirección, se usa una aproximación:

> La población de cada municipio o distrito se utiliza como proxy de demanda.

Un proxy es una variable que no mide directamente lo que nos interesa, pero se usa como aproximación razonable. En este caso, se asume que las zonas con más población tenderán a generar más demanda de paquetes.

### 3.1. Puntos de demanda

El territorio se convierte en una lista de puntos. Cada punto representa un municipio o un distrito urbano. Para cada uno se recopila:

- Nombre del municipio o distrito.
- Coordenadas geográficas.
- Coordenadas proyectadas en un sistema plano.
- Población.

Las ciudades grandes se dividen en distritos para evitar un problema frecuente: si toda Sevilla capital se representara como un único punto, parecería que toda la demanda está concentrada en un solo lugar. Al desagregarla, el modelo refleja mejor la distribución real dentro del área urbana.

### 3.2. Peso de cada punto

A cada punto se le asigna un peso proporcional a su población. Ese peso no significa dinero ni paquetes exactos en la primera fase. Sirve para decirle al modelo:

> Este punto importa más porque representa más demanda potencial.

En la fase de localización, esos pesos se usan para que una zona con mucha población tenga más influencia en el cálculo del punto óptimo.

### 3.3. Paquetes asignados

Para la fase de rutas, el proyecto necesita algo más concreto que un peso abstracto. Por eso reparte el volumen diario de paquetes de forma proporcional a los pesos.

Conceptualmente, el procedimiento es:

1. Se calcula qué porcentaje del peso total corresponde a cada punto.
2. Se asigna a ese punto una parte proporcional de los paquetes.
3. Se corrigen los redondeos para que la suma final coincida con la demanda total modelada.

Esta demanda por punto será la que luego intenten cubrir las furgonetas en el problema de rutas.

## 4. Transformación de coordenadas

Las coordenadas habituales de mapas se expresan como latitud y longitud. Son útiles para localizar puntos en la Tierra, pero no son cómodas para hacer cálculos de distancia en un plano.

Por eso la memoria transforma las coordenadas a un sistema proyectado, en kilómetros. En términos sencillos:

- Latitud y longitud sirven para ubicar los puntos en un mapa.
- Las coordenadas proyectadas sirven para calcular distancias y optimizar.

El flujo seguido es:

1. Cada punto se proyecta a un sistema UTM.
2. Se toma una esquina de referencia del área de estudio.
3. Todos los puntos se expresan como distancias en kilómetros respecto a esa referencia.

Esto permite trabajar en un plano cartesiano, como si el territorio fuera una hoja de papel medida en kilómetros. Después, si hace falta dibujar mapas o consultar rutas reales por carretera, se puede volver a coordenadas geográficas.

## 5. Fase de localización

La primera fase técnica responde a esta pregunta:

> Si solo nos importara estar cerca de la demanda, ¿dónde debería estar la estación de reparto?

Para responder, la memoria usa un problema de localización conocido como problema de Weber.

### 5.1. Qué es el problema de Weber

El problema de Weber busca el punto que minimiza la suma de distancias ponderadas a todos los puntos de demanda.

Dicho sin fórmula:

> Se prueba una ubicación candidata y se calcula cuánto "cuesta" estar ahí, sumando la distancia desde esa ubicación hasta cada punto de demanda, dando más importancia a los puntos con más peso.

Si una ubicación está cerca de zonas muy pobladas, su valor será mejor. Si está lejos de zonas importantes, su valor empeorará.

La función que se minimiza puede entenderse como:

```text
coste geométrico = suma de (peso del punto * distancia al punto)
```

Es fundamental entender que este "coste" no es económico. No son euros. Tampoco son los kilómetros reales que recorrerá una flota. Es una medida geométrica de accesibilidad.

### 5.2. Por qué no basta con mirar el mapa

A simple vista, uno podría pensar que basta con elegir un punto "céntrico". Pero la demanda no está repartida de forma uniforme. Algunas zonas pesan más que otras, y las distancias se combinan con esos pesos.

El problema de Weber formaliza esa intuición. En vez de escoger visualmente una ubicación, calcula el punto que mejor equilibra todas las demandas ponderadas.

### 5.3. Optimización numérica

La memoria resuelve el problema mediante un algoritmo de optimización numérica. La idea es:

1. Se parte de una ubicación inicial razonable, cercana al centro ponderado de la demanda.
2. El algoritmo evalúa hacia dónde debe moverse para reducir la función objetivo.
3. Repite el proceso hasta que ya no encuentra una mejora significativa.

El método empleado es adecuado para funciones suaves y convexas. En este caso, la forma de la función ayuda: tiene un mínimo global bien definido, no una multitud de trampas locales.

### 5.4. Simulación Monte Carlo

Además de resolver el óptimo con un algoritmo, la memoria realiza una simulación Monte Carlo.

Monte Carlo significa que se prueban muchos puntos aleatorios dentro de la zona de estudio. Para cada punto se calcula el valor de la función de localización. Esto sirve para:

- Comprobar que el óptimo numérico tiene sentido.
- Ver la forma global de la superficie de coste.
- Entender si la zona alrededor del óptimo es plana o si alejarse penaliza mucho.

Para principiantes, se puede imaginar como dibujar un mapa de calor: las zonas mejores quedan cerca del fondo del "cuenco" y las peores aparecen más arriba.

### 5.5. Qué se concluye conceptualmente

La fase de localización no decide por sí sola si hay que fusionar los centros. Lo que hace es acotar el problema.

Si DQA4 ya está muy cerca de la ubicación geométricamente óptima, no tiene mucho sentido estudiar una tercera ubicación nueva solo por motivos de accesibilidad. Por eso la memoria arrastra a la fase siguiente los dos escenarios principales:

- Repartir desde DQA4.
- Repartir desde SVQ1.

La conclusión conceptual es:

> La ubicación geométrica ayuda a entender el equilibrio espacial de la demanda, pero la decisión real necesita analizar rutas y economía.

## 6. Fase de rutas o VRP

Una vez elegidos los depósitos candidatos, la segunda fase responde una pregunta más operativa:

> Si las furgonetas salen desde cada ubicación, ¿cómo se comporta el reparto diario?

Aquí aparece el VRP, o Vehicle Routing Problem.

### 6.1. Qué es un VRP

Un VRP es un problema de rutas de vehículos. Consiste en decidir qué vehículo visita qué puntos, en qué orden y respetando ciertas restricciones.

En un ejemplo sencillo:

- Hay un depósito.
- Hay varios clientes o puntos de entrega.
- Hay una flota de vehículos.
- Cada vehículo tiene un límite de tiempo, capacidad o ambas cosas.
- El objetivo suele ser reducir distancia, tiempo o coste, sirviendo la mayor demanda posible.

En este proyecto, el depósito cambia según el escenario: DQA4 o SVQ1.

### 6.2. Por qué la restricción principal es el tiempo

En muchos VRP clásicos, la restricción dominante es la capacidad del vehículo. Por ejemplo, un camión no puede cargar más de cierto peso.

La memoria toma otra decisión: en este caso, la restricción dura principal es el tiempo de jornada, no la capacidad física de la furgoneta.

La razón conceptual es que, en reparto de última milla con paquetes ligeros, muchas veces el cuello de botella no es el volumen del vehículo, sino el tiempo necesario para:

- Conducir hasta las zonas de reparto.
- Aparcar o aproximarse.
- Entregar paquetes.
- Volver al depósito.

Una parada con mucha demanda puede consumir mucho tiempo de servicio aunque esté relativamente cerca. Por eso el modelo se centra en si una ruta cabe dentro de la ventana horaria disponible.

### 6.3. Tiempo de viaje y tiempo de servicio

El tiempo total de una ruta se compone de dos partes:

- Tiempo de viaje: lo que tarda la furgoneta en moverse entre depósito y puntos.
- Tiempo de servicio: lo que tarda en entregar los paquetes en cada punto.

El tiempo de servicio se hace proporcional a los paquetes asignados a cada destino. Esto representa una idea sencilla: entregar más paquetes requiere más tiempo.

### 6.4. Distancias reales por carretera

En localización se usan distancias geométricas. En rutas, en cambio, se usan distancias por carretera.

Esta diferencia es muy importante:

- La distancia geométrica sirve para una primera aproximación espacial.
- La distancia por carretera refleja mejor cómo se movería realmente una furgoneta.

Para obtener esas distancias, la memoria usa OSRM, un motor de rutas basado en OpenStreetMap. Así se evita asumir que una furgoneta puede ir en línea recta entre dos municipios.

### 6.5. Dos ventanas de reparto

El día de reparto se divide en dos ventanas:

- Una ventana de mañana.
- Una ventana de tarde.

El modelo intenta servir demanda en la primera ventana y, si queda demanda pendiente, continúa en la segunda. Lo que no se pueda cubrir al final se registra como demanda no servida.

La división en ventanas permite representar mejor una jornada realista: no se trata solo de sumar horas totales, sino de respetar bloques operativos.

## 7. Heurísticas usadas para resolver las rutas

El VRP es computacionalmente difícil. Para muchos puntos de demanda, encontrar la solución exacta puede ser inviable o innecesario para un proyecto académico de viabilidad.

Por eso la memoria usa heurísticas. Una heurística es un método práctico que busca buenas soluciones sin garantizar que sean perfectas.

Se emplean dos enfoques para comprobar que la comparación entre escenarios no depende de una única forma de construir rutas.

### 7.1. Algoritmo de ahorros de Clarke-Wright

Este método parte de una solución muy simple:

> Cada punto se sirve con una ruta independiente que sale del depósito, visita ese punto y vuelve.

Luego intenta fusionar rutas. Si visitar dos puntos en una misma ruta ahorra tiempo respecto a hacer dos viajes separados, esa fusión puede ser interesante.

El algoritmo:

1. Calcula el ahorro de combinar pares de puntos.
2. Ordena las combinaciones más prometedoras.
3. Fusiona rutas si la ruta resultante sigue cumpliendo la restricción de tiempo.
4. Repite hasta que no puede mejorar más o se agotan las posibilidades factibles.

La intuición es muy clara: si dos destinos están en una dirección parecida, puede tener sentido servirlos juntos.

### 7.2. Heurística de inserción

La heurística de inserción construye rutas de manera secuencial.

El procedimiento conceptual es:

1. Se elige un punto inicial para abrir una ruta.
2. Se busca que otro punto podría insertarse en esa ruta con el menor aumento de tiempo.
3. Se inserta si la ruta sigue cabiendo en la ventana horaria.
4. Cuando ya no caben más puntos, se cierra la ruta.
5. Se abre una nueva ruta y se repite el proceso.

Esta técnica es distinta al método de ahorros. Por eso sirve como contraste: si ambos métodos muestran que un escenario tiende a exigir más recorrido o más tiempo, la conclusión operativa gana robustez.

### 7.3. Tratamiento de puntos saturados

La memoria introduce una lógica especial para puntos cuya demanda consume por sí sola buena parte de una ventana.

En esos casos, el modelo puede asignar furgonetas dedicadas a viajes directos entre depósito y punto. Esto ocurre porque no siempre tiene sentido mezclar ese destino con otros: si el tiempo de servicio ya es muy alto, la ruta apenas tiene margen para más paradas.

Esta decisión hace que el modelo sea más realista para zonas urbanas densas.

## 8. Salidas de la fase de rutas

Para cada combinación de escenario y algoritmo, el solver produce indicadores comparables.

Los más importantes son:

- Distancia total recorrida por la flota.
- Tiempo total de operación.
- Rutas generadas.
- Vehículos utilizados.
- Paquetes entregados.
- Demanda pendiente.
- Cobertura del reparto.
- Lista de puntos no abastecidos.

Lo relevante no es memorizar los números, sino entender que se comparan siempre las mismas métricas bajo los dos depósitos.

La fase de rutas transforma la pregunta espacial en una pregunta operativa:

> ¿Qué depósito obliga a la flota a trabajar más para atender la misma demanda?

## 9. Lectura conceptual de los resultados operativos

La memoria observa un patrón coherente:

- Si el depósito se aleja del centro de gravedad de la demanda, las rutas tienden a empeorar.
- Las zonas urbanas densas se comportan como destinos de alta carga de servicio.
- Los municipios remotos son más difíciles de encajar dentro de ventanas horarias.
- Algunos puntos pueden quedar sin servir si el tiempo disponible y la flota no bastan.

Esto no significa automáticamente que fusionar sea mala decisión. Significa que, desde el punto de vista puramente operativo de reparto, mover el punto de salida a SVQ1 introduce una penalización.

La decisión final exige comparar esa penalización con los ahorros estructurales de operar una sola instalación para la actividad estudiada.

## 10. Aplicación informática

La memoria explica que las fases operativas se implementan en una aplicación de escritorio.

La aplicación cumple dos funciones:

- Permite reproducir los cálculos.
- Permite visualizar los datos, mapas, rutas y comparaciones.

La arquitectura separa responsabilidades:

- Configuración: parámetros por defecto del modelo.
- Carga de datos: lectura, conversión de coordenadas, pesos y paquetes.
- Localización: problema de Weber, optimización y Monte Carlo.
- Rutas: matrices de distancia y tiempo, heurísticas y ventanas.
- Distancias por carretera: conexión con OSRM y caché.
- Interfaz: pestañas para datos, localización, rutas y comparación.

Esta separación es buena práctica porque evita mezclar cálculo y visualización. Si el modelo cambia, se puede modificar la lógica sin rehacer toda la interfaz.

## 11. Paso al análisis económico

Hasta aquí, el proyecto ha contestado preguntas operativas. Pero la decisión real es económica:

> Aunque repartir desde SVQ1 sea menos eficiente, ¿los ahorros por unificar compensan esa penalización?

Para responder, la memoria construye un modelo financiero. Este modelo toma elementos de la fase de rutas y los combina con costes, ahorros y riesgos.

La idea es convertir consecuencias operativas en flujos económicos:

- Más kilómetros de reparto implican más coste recurrente.
- Eliminar transferencias entre centros genera ahorro.
- Reducir duplicidades puede generar ahorro.
- Cambiar la estructura operativa requiere inversión.
- La transición introduce riesgos.

## 12. Costes, ahorros y riesgos

El análisis económico distingue tres bloques.

### 12.1. Inversión inicial

La inversión inicial agrupa costes que ocurren al principio del proyecto. Por ejemplo:

- Adaptaciones o ampliaciones.
- Formación.
- Riesgos de construcción o implantación.
- Pérdida de valor o reconfiguración de activos.

Estos costes se consideran en el arranque del proyecto, antes de que los ahorros futuros se materialicen.

### 12.2. Costes recurrentes

Los costes recurrentes son los que aparecen cada año si se adopta el escenario de fusión.

El más directamente conectado con la fase operativa es el sobrecoste de transporte: si las rutas salen desde una ubicación menos favorable, la flota puede recorrer más distancia o consumir más recursos.

También se consideran riesgos o necesidades operativas que pueden repetirse durante la vida del proyecto.

### 12.3. Ahorros operativos

La fusión también genera ahorros potenciales:

- Se elimina una transferencia interna entre centros para el flujo estudiado.
- Se reducen duplicidades de recursos.
- Se aprovecha una única estructura operativa.
- Se simplifican ciertos costes fijos.

Estos ahorros no se tratan como automáticos e inmediatos en todos los casos. Algunos se aplican con una curva de aprendizaje, porque una organización no suele capturar todo el ahorro desde el primer día.

## 13. Escenarios económicos

Para no depender de una única estimación, la memoria trabaja con tres casos:

- Optimista.
- Probable.
- Pesimista.

El objetivo no es elegir el caso que más guste, sino medir la sensibilidad de la decisión. Si el proyecto solo funciona en el caso optimista, es frágil. Si funciona también bajo supuestos prudentes, es más defendible.

El caso probable representa la lectura central. El pesimista introduce una visión adversa, incluyendo la posibilidad de que varios factores negativos coincidan.

## 14. Indicadores financieros

El modelo económico calcula indicadores clásicos de evaluación de inversiones.

### 14.1. VAN

El VAN, o valor actual neto, compara la inversión inicial con los flujos futuros descontados.

La idea para principiantes es:

> El dinero futuro vale menos que el dinero disponible hoy, así que los ahorros futuros se actualizan antes de compararlos con la inversión.

Si el VAN es positivo, el proyecto crea valor bajo los supuestos usados. Si es negativo, destruye valor.

### 14.2. TIR

La TIR, o tasa interna de retorno, indica la rentabilidad interna del proyecto.

Se compara con una tasa de descuento o umbral mínimo. Si la TIR queda apenas por encima del umbral, el proyecto puede ser rentable pero poco robusto.

### 14.3. Payback

El payback indica cuánto tarda el proyecto en recuperar la inversión inicial.

Es fácil de entender, pero no debe usarse solo. Un proyecto puede recuperar pronto la inversión y aun así tener riesgos importantes, o tardar más pero generar valor sostenido.

## 15. Análisis probabilístico y regla PERT

La memoria usa una aproximación tipo Beta-PERT para sintetizar la incertidumbre de los ahorros.

La idea general es:

- No se toma solo el mejor caso.
- No se toma solo el peor caso.
- Se da más peso al caso probable.
- Se obtiene una estimación promedio y una dispersión aproximada.

Esto ayuda a expresar que el ahorro esperado no es una cifra exacta, sino una variable incierta.

Para principiantes, la utilidad de PERT es que obliga a pensar en rangos y no solo en un número único. En proyectos reales, esa mentalidad es más prudente.

## 16. Estrategias de mitigación

El análisis económico inicial puede mostrar que el proyecto tiene potencial, pero también riesgo. Por eso la memoria evalúa medidas de mitigación.

Una estrategia de mitigación es una acción que cuesta dinero, pero reduce la probabilidad o impacto de un problema.

Ejemplos conceptuales:

- Sistemas de respaldo para reducir riesgos tecnológicos.
- Seguros para limitar ciertos impactos económicos.
- Incentivos para reducir problemas laborales durante la transición.
- Implantación por fases para controlar interrupciones.

Cada estrategia se evalúa preguntando:

> ¿El coste adicional de implantar esta medida se compensa con la reducción del riesgo?

No todas las mitigaciones son igual de atractivas. Una medida puede ser buena desde el punto de vista operativo o cualitativo, pero no mejorar mucho los indicadores financieros. Otra puede tener poco coste y reducir un riesgo relevante, por lo que resulta muy eficiente.

## 17. Lógica de la recomendación final

La recomendación de la memoria es matizada. No se basa en una frase simple como "fusionar siempre" o "no fusionar nunca".

El razonamiento es:

1. La fase de localización muestra que DQA4 está muy bien situada respecto a la demanda.
2. La fase de rutas muestra que repartir desde SVQ1 penaliza la operación de última milla.
3. La fase económica muestra que la fusión puede generar ahorros estructurales relevantes.
4. El caso base sin mitigación puede quedar demasiado expuesto al riesgo.
5. Con medidas de mitigación adecuadas, la decisión mejora y puede volverse defendible.

La conclusión conceptual es:

> La fusión no se justifica porque mejore las rutas. Se justifica, si se justifica, porque los ahorros estructurales y la gestión activa del riesgo compensan el empeoramiento operativo.

Esta es una lectura muy importante para defender el proyecto: las fases no se contradicen, sino que se complementan.

## 18. Qué no debe interpretarse de forma incorrecta

Hay varias precauciones metodológicas:

- El proyecto no usa demanda real de Amazon, sino población como aproximación.
- La función de localización no es un coste económico.
- Las rutas son una simulación heurística, no una optimización exacta garantizada.
- Las cifras económicas dependen de supuestos.
- La recomendación no debe presentarse como una predicción real de Amazon.
- La capacidad física de las furgonetas no es la restricción activa del modelo.
- Los resultados deben leerse como análisis de viabilidad académica, no como forecast empresarial.

Estas advertencias fortalecen el trabajo, porque muestran que el alcance está bien delimitado.

## 19. Esquema completo del flujo de trabajo

El proceso seguido puede resumirse así:

```text
Definición del problema
        |
        v
Escenarios: mantener DQA4 o fusionar en SVQ1
        |
        v
Construcción de la demanda con población como proxy
        |
        v
Transformación de coordenadas a un plano métrico
        |
        v
Fase 1: localización mediante problema de Weber
        |
        v
Validación y caracterización con Monte Carlo
        |
        v
Selección de escenarios operativos a rutear
        |
        v
Fase 2: VRP con restricción de tiempo
        |
        v
Comparación de rutas, tiempos, distancias y cobertura
        |
        v
Traducción de impactos operativos al modelo económico
        |
        v
Análisis de inversión, ahorros, riesgos y escenarios
        |
        v
Evaluación de mitigaciones
        |
        v
Recomendación final condicionada
```

## 20. Explicación sencilla de la cadena de razonamiento

La memoria sigue una lógica de embudo.

Primero abre el problema: hay dos centros y una posible duplicidad operativa. Luego convierte el territorio en datos. Después usa esos datos para comprobar si la ubicación actual de DQA4 tiene sentido desde el punto de vista espacial.

Una vez entendido eso, no se queda en el mapa. Pasa a una simulación de reparto, porque el reparto real depende de carreteras, ventanas horarias, tiempo de servicio y número de vehículos.

Cuando observa el impacto operativo, tampoco se detiene ahí. Lo lleva al terreno económico, porque una decisión logística puede ser peor en kilómetros pero mejor en estructura de costes.

Finalmente, introduce riesgo. Esta parte es esencial: una recomendación de inversión no debería basarse solo en el promedio, sino también en qué ocurre si las cosas salen peor de lo previsto y qué medidas pueden reducir ese peligro.

## 21. Cómo explicar el proyecto en una presentación

Una forma clara de presentarlo sería:

1. "No estamos prediciendo la demanda real de Amazon; usamos población como proxy para construir un caso defendible."
2. "Primero estudiamos la accesibilidad geométrica mediante un problema de localización."
3. "Después simulamos rutas reales de reparto con restricciones de tiempo."
4. "Comprobamos que mover el reparto a SVQ1 penaliza la operación de última milla."
5. "Aun así, evaluamos si los ahorros de unificar compensan esa penalización."
6. "Como el proyecto tiene incertidumbre, analizamos escenarios y mitigaciones."
7. "La recomendación final depende de acompañar la fusión con medidas de control del riesgo."

Esta explicación ayuda a que el oyente no confunda los niveles del análisis.

## 22. Glosario básico

**Última milla**: tramo final del reparto, desde una estación o depósito hasta el cliente.

**Centro de distribución**: instalación grande donde se reciben, almacenan o preparan productos.

**Estación de entrega**: instalación orientada a organizar rutas de reparto final.

**Proxy de demanda**: variable usada como aproximación cuando no se dispone de la demanda real.

**Punto de demanda**: municipio o distrito que representa una zona a atender.

**Peso poblacional**: importancia relativa de un punto en función de su población.

**Problema de Weber**: modelo que busca una ubicación minimizando distancias ponderadas a la demanda.

**Función objetivo**: magnitud que el modelo intenta minimizar o maximizar.

**Monte Carlo**: técnica que prueba muchos casos aleatorios para caracterizar un problema.

**VRP**: problema de rutas de vehículos.

**Heurística**: método práctico que busca buenas soluciones sin garantizar la solución exacta óptima.

**Clarke-Wright**: heurística de rutas basada en fusionar recorridos cuando se obtiene ahorro.

**Inserción**: heurística que construye rutas agregando puntos donde menos aumentan el tiempo.

**OSRM**: motor de rutas que calcula distancias por carretera.

**CAPEX**: inversión inicial o gasto de capital.

**OPEX**: costes operativos recurrentes.

**VAN**: valor actual neto de una inversión.

**TIR**: tasa interna de retorno.

**Payback**: tiempo necesario para recuperar la inversión.

**Mitigación**: acción que reduce la probabilidad o impacto de un riesgo.

## 23. Resumen final para principiantes

La memoria construye una decisión logística paso a paso.

Primero representa la demanda usando población. Luego calcula cuál sería una buena ubicación teórica para repartir. Después comprueba cómo cambiarían las rutas si el reparto saliera desde DQA4 o desde SVQ1. Esa comparación muestra el efecto operativo de mover el depósito.

Pero la decisión no se queda en la operación diaria. El proyecto también pregunta si los ahorros de simplificar la red compensan los costes y riesgos de la fusión. Para eso usa un modelo económico con escenarios y medidas de mitigación.

La idea central es que una fusión logística puede ser atractiva aunque empeore algunas rutas, siempre que los ahorros estructurales sean suficientes y los riesgos estén controlados. Por eso la recomendación final es condicionada: no basta con fusionar; hay que hacerlo con un paquete de medidas que reduzca la incertidumbre de la transición.
