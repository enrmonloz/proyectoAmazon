# Proyecto Amazon SVQ1 + DQA4

App en Streamlit para estudiar el rediseño operativo de Amazon en Sevilla:
asignación de rutas desde SVQ1/DQA4, localización de centro, dimensionamiento
del almacén y síntesis económica de la unificación.

El núcleo operativo está implementado en Python con OR-Tools, pandas, SciPy,
folium, Plotly y Streamlit. Los scripts MATLAB de `codes/` se conservan como
referencia, pero su lógica principal de almacén, layout y economía está
reimplementada en Python con parámetros ajustables.

---

## Estructura del proyecto

```text
PROYECTO/
├── app.py                       # Entrypoint Streamlit
├── requirements.txt
├── setup.bat / run.bat          # Scripts Windows para venv y arranque
├── data/
│   ├── poblacion.csv            # Nodos, población, coordenadas y restricciones
│   ├── rutasDistTiempo.csv      # Matriz OD larga de km y minutos
│   ├── distanciasReales.xlsx    # Matriz de distancias reales
│   └── Costes_Vehiculos_UNIFICAR_SVQ1.xlsx
├── src/
│   ├── data_loader.py           # Carga y validación de datos
│   ├── demand.py                # Cálculo de paquetes y tiempos de servicio
│   ├── split_delivery.py        # Rutas dedicadas para nodos sobredimensionados
│   ├── fleet.py                 # Configuración de flota diésel/eléctrica
│   ├── trailer.py               # Configuración de trailers para nodos grandes
│   ├── vrp_solver.py            # Solver OR-Tools por tiempo y distancia
│   ├── location_solver.py       # Métodos de localización
│   ├── map_view.py              # Mapa folium de rutas
│   ├── location_view.py         # Visualización de localización
│   ├── warehouse_model.py       # Modelos paramétricos equivalentes a almacén MATLAB
│   ├── economics_model.py       # Modelo económico y flota parametrizable
│   ├── project_sections.py      # Vistas Streamlit de almacén y economía
│   └── pipeline.py              # Orquestación del cálculo VRP
├── codes/
│   ├── Economia.m               # Análisis financiero base
│   └── almacen_amazon/          # Scripts MATLAB de dimensionamiento/layout
├── docs/
│   └── fulfillment.txt          # Notas conceptuales del proyecto
└── tests/
    ├── test_pipeline.py
    └── test_strategies_trailer.py
```

---

## Instalación

### Windows

```bat
setup.bat
run.bat
```

`setup.bat` crea el entorno virtual e instala dependencias. `run.bat` activa el
entorno y arranca Streamlit.

### Linux / macOS

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

---

## Uso de la app

La app contiene cuatro pestañas principales:

- **Asignación de Rutas (VRP)**: calcula demanda, aplica split-delivery,
  asigna rutas con OR-Tools y permite exportar CSV/JSON.
- **Localización de Centro**: compara técnicas de localización usando población
  y coordenadas, y contrasta candidatos concretos como SVQ1, DQA4, un punto
  intermedio heurístico y el óptimo continuo como referencia matemática.
- **Almacén**: resuelve dimensionamiento, zonificación ABC, layout 1 planta/3D,
  comparación de estrategias y sensibilidad de porcentajes/movimientos.
- **Economía**: calcula costes actuales, CAPEX/OPEX, VAN/TIR, escenarios
  pesimistas, riesgos y costes de vehículos con parámetros editables.

---

## Supuestos operativos principales

- **Paquetes por nodo**: por defecto `paquetes = round(poblacion * penetracion)`.
  Opcionalmente se calibra la penetración con un volumen diario objetivo y se
  aplica un multiplicador estacional antes del redondeo. El depósito activo
  tiene 0 paquetes.
- **Tiempo nodal de servicio**: `paquetes * (servicio_por_paquete +
  tiempo_entre_paquetes)`.
- **Flota por defecto**: 75 furgonetas diésel + 45 eléctricas. Las eléctricas
  tienen rango máximo por jornada como restricción dura.
- **Trailers**: pueden sustituir furgonetas dedicadas en nodos grandes
  configurados en `src/trailer.py`.
- **Solver**: minimiza principalmente vehículos usados mediante coste fijo y,
  de forma secundaria, tiempo/distancia.

---

## Apartado de almacén

La pestaña **Almacén** traduce a Python lo que hacen los scripts de
`codes/almacen_amazon`:

- `Almacen_dimension.m`: área útil, número de estanterías, huecos, ocupación y
  capacidad.
- `Almacen_1floor.m`: cálculo del índice `f` y asignación ABC en una planta.
- `Almacen_3floor.m`: extensión 3D con penalización vertical por cinta.
- `Almacen_vs.m`: comparación ABC por planta frente a ABC global.
- `Almacen_resultado_variable_3.m`: barrido de porcentajes ABC y movimientos.

La pestaña de layout incluye presets separados para esos scripts, porque no
usan exactamente las mismas puertas ni pesos. En particular,
`Almacen_3floor.m` usa la tercera puerta en la columna 50 y añade un coste
vertical creciente por planta; con los parámetros base la penalización es
12, 24 y 36 celdas para las plantas 1, 2 y 3.

Los valores por defecto reproducen el caso base:

- Edificio: 300 x 150 m, 45.000 m².
- Robotics Area: 20.000 m² por planta.
- Estanterías: 5.000 por planta, 15.000 en tres plantas.
- Huecos por estantería: 56; capacidad teórica: 672 paquetes.
- Ocupación real asumida: 67%, equivalente a 450,24 paquetes por estantería.
- Capacidad total: 6.753.600 paquetes.
- Reparto ABC: A 15%, B 15%, C 70%; movimientos 80%, 15%, 5%.
- Estrategia recomendada: ABC global optimizado en 3D, con mejora estimada del
  9,70% frente al ABC independiente por planta.

---

## Apartado económico

La pestaña **Economía** reimplementa la lógica de `codes/Economia.m` como
modelo parametrizable:

- Costes actuales SVQ1/DQA4 y coste unitario de transferencia.
- Opciones de inversión básica, estándar y premium.
- Costes adicionales: formación, mitigación, seguros, incentivos y apoyo a
  empleados DQA4.
- Horizonte, tasa de descuento, escenario pesimista y ranking multicriterio.
- Riesgos con probabilidad, impacto y valor esperado.
- Costes de flota derivados del Excel, con número de vehículos y costes
  unitarios editables.

Los valores por defecto reproducen el caso base:

- Coste actual: 56,39 M€/año.
- Transferencias redundantes SVQ1-DQA4: 1,99 M€/año.
- Ahorro anual estimado: 6,69-9,89 M€/año.
- Opción recomendada: **Estándar**.
- CAPEX estándar: 28,50 M€ base + 5,90 M€ de transición = 34,40 M€.
- OPEX nuevo recurrente: 0,977 M€/año.
- Ahorro neto: 5,723 M€/año.
- VAN a 10 años: 5,80 M€; TIR aproximada: 10,5%.

El Excel `data/Costes_Vehiculos_UNIFICAR_SVQ1.xlsx` se usa como fuente estática
para los costes de flota:

- Furgonetas propias: 6,874 M€/año.
- Furgonetas subcontratadas: 2,295 M€/año.
- Total furgonetas: 9,169 M€/año.
- Trailers: 0,994 M€/año.
- Total rutas con SVQ1 unificado: 10,162 M€/año.
- Sobrecoste anual frente al escenario sin unificar: 0,122 M€/año.

---

## Tests rápidos

```bash
python3 tests/test_pipeline.py
python3 tests/test_location_solver.py
python3 tests/test_strategies_trailer.py
python3 tests/test_project_models.py
python3 -m compileall app.py src tests
```

Los tests comprueban carga de datos, cálculo de demanda, split-delivery,
estrategias del solver y uso de trailers.
