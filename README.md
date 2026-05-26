# Amazon Sevilla SVQ1 + DQA4

Aplicación en Streamlit para analizar, de forma académica y reproducible, la
viabilidad de una posible integración operativa entre SVQ1 y DQA4 en Sevilla.
El proyecto compara demanda, localización, rutas, almacén, economía, riesgos y
escenarios. No es una previsión real de Amazon: usa el enunciado y los datos del
repositorio como fuente de verdad.

## Qué incluye

- Flujo guiado para construir una lectura presentable de demanda,
  localización, rutas, economía y conclusión condicionada.
- Análisis por módulos para revisar demanda, flota, VRP, localización, almacén,
  economía, riesgos, calendario y escenarios.
- Solver de rutas con OR-Tools, restricción dura de jornada y rango eléctrico.
- Modelos parametrizables de almacén, CAPEX/OPEX, VAN/TIR, payback, riesgos y
  transición.
- Tests de humo y coherencia sobre pipeline, rutas, economía, escenarios y
  riesgos.

## Instalación

Requisitos recomendados:

- Python 3.11 o superior.
- Git.
- En Windows, PowerShell o CMD. En Linux/macOS, una shell POSIX.

### Windows

```bat
setup.bat
run.bat
```

`setup.bat` crea el entorno virtual `.venv` e instala dependencias.
`run.bat` activa el entorno y arranca la app.

### Linux / macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
streamlit run app.py
```

La app se abrirá normalmente en `http://localhost:8501`.

## Uso

1. Ejecuta `streamlit run app.py`.
2. Usa **Flujo guiado** para una lectura ordenada y defendible del caso.
3. Usa **Análisis por módulos** para inspeccionar supuestos, sensibilidad y
   resultados técnicos.
4. Cambia parámetros solo cuando quieras explorar escenarios; los valores base
   buscan mantenerse alineados con el enunciado y la documentación interna.

## Tests

Para validar la parte Python:

```bash
python -m compileall app.py src tests
python -m pytest tests
```

Si `pytest` no está instalado en tu entorno, instálalo solo para desarrollo:

```bash
pip install pytest
```

## Estructura del repositorio

```text
.
├── app.py                 # Entrada principal de Streamlit
├── src/                   # Lógica de negocio, modelos y vistas reutilizables
├── tests/                 # Tests de pipeline, modelos y escenarios
├── data/                  # Datos tabulares necesarios para ejecutar la app
├── docs/                  # Supuestos, arquitectura, modelos y revisión
├── codes/                 # Scripts MATLAB históricos conservados como apoyo
├── requirements.txt       # Dependencias de la aplicación
├── setup.bat / run.bat    # Instalación y ejecución en Windows
└── PLANS.md               # Historial de iteraciones y decisiones pendientes
```

Las carpetas `report/` y `memoria_final/` contienen entregables, borradores,
presentaciones o salidas LaTeX. No son necesarias para ejecutar la app y quedan
ignoradas para mantener limpio el repositorio de aplicación.

## Datos y supuestos

- La demanda usa población como proxy, con calibración y estacionalidad.
- La capacidad física de furgoneta no actúa como restricción activa del solver.
- El VRP prioriza jornada laboral y rango eléctrico como restricciones duras.
- DQA4 no se modela como cerrado por completo; el análisis se centra en el
  flujo atribuible SVQ1 -> DQA4.
- Las hipótesis vivas están en `docs/assumptions.md` y el contexto del
  enunciado está resumido en `docs/sintesis_enunciado_proyecto.md`.

## Documentación útil

- `docs/Readme.md`: índice compacto de documentación.
- `docs/project_brief.md`: alcance del caso.
- `docs/architecture.md`: separación entre app, modelos, datos y tests.
- `docs/logistics_model.md`: demanda, rutas, localización y alcance logístico.
- `docs/finance_model.md`: estructura económica.
- `docs/scenario_model.md`: comparación de escenarios.
- `docs/code_review.md`: checklist antes de fusionar cambios.

## Notas de mantenimiento

- Mantener la lógica de negocio en `src/` y la interfaz en `app.py` /
  funciones de vista.
- No introducir datos externos sin documentar su origen.
- Si se retiran del índice archivos ya versionados que ahora están ignorados,
  usar `git rm --cached` para dejar los archivos locales sin publicarlos de
  nuevo.
