# Architecture

## Entry point
- app.py: Streamlit UI entrypoint; collects inputs and renders results.

## Data layer
- src/data_loader.py: Loads CSV/Excel inputs, names, and matrices.

## Core pipeline
- src/pipeline.py: Orchestrates demand -> split delivery -> VRP -> schedules.

## Demand
- src/demand.py: Packages per node, calibration, seasonality, validation.

## Routing and fleet
- src/vrp_solver.py: OR-Tools VRP by time and electric range.
- src/fleet.py: Fleet config and vehicle types.
- src/split_delivery.py: Dedicated routes for oversized nodes.
- src/trailer.py: Trailer config for large nodes.

## Location
- src/location_solver.py: Continuous location methods and candidate comparison.
- src/location_view.py: Visualization of location results.

## Maps and UI sections
- src/map_view.py: Route visualization.
- src/project_sections.py: Streamlit sections for warehouse and economics.
- src/guided_flow.py: Non-UI helpers for the one-page academic guided flow,
  including selected scenarios and cache signatures.

## Warehouse and economics
- src/warehouse_model.py: Dimensioning and layout models.
- src/economics_model.py: Parametric finance and risk tables.

## Tests
- tests/: Smoke and compatibility tests for pipeline, location, models, and trailer.

## Separation rules
- Business logic belongs in src/* model modules.
- Streamlit views should only format and visualize outputs.
