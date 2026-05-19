# Scenario model (future design)

## Purpose
Define a top-layer scenario structure that coordinates demand, location, routing,
finance, risks, schedule, and layout without changing the current modules yet.

## ScenarioConfig (concept)
- id and name
- location_choice (SVQ1, DQA4 reference, intermediate)
- investment_option
- demand_profile (target volume and seasonality)
- transition_plan (phasing, start month)
- labor_policy
- mitigations
- risk_profile

## ScenarioResult (concept)
- operational metrics (routes, time, distance)
- finance metrics (CAPEX, OPEX, net savings, payback, VAN)
- risk metrics (expected cost, residual risk)
- service metrics and notes
- transition timeline metrics (monthly phases, milestones, seasonal warnings)

## Dimensions (future)
Ubicacion, inversion, demanda, transicion, politica laboral, mitigaciones, mes de inicio, riesgo.

## Module inputs (future)
- Demand: demand_profile, seasonality
- Location: location_choice or candidate set
- Routes: demand outputs and fleet policy
- Economics: CAPEX/OPEX, route totals, labor policy
- Risk: risk_profile and mitigations
- Transition timeline: start month, phase durations, milestones, and seasonality
- Layout: unified center assumptions

## Current reusable pieces
- `src/timeline_model.py` already produces a standalone `TimelineResult` with monthly phases, critical milestones, warnings, summary, score, and suggested alternative start month.
- The timeline output is designed to be reusable by a future `ScenarioResult`, but it is not integrated into the global scenario layer yet.

## Comparison criteria (future)
CAPEX, OPEX, net savings, payback, VAN, expected risk, service level,
operational viability, labor impact.

## Non-goals now
The global `ScenarioConfig` / `ScenarioResult` layer remains conceptual. The
standalone timeline module and UI section do not rank full scenarios or decide
project viability by themselves.
