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

## Dimensions (future)
Ubicacion, inversion, demanda, transicion, politica laboral, mitigaciones, mes de inicio, riesgo.

## Module inputs (future)
- Demand: demand_profile, seasonality
- Location: location_choice or candidate set
- Routes: demand outputs and fleet policy
- Economics: CAPEX/OPEX, route totals, labor policy
- Risk: risk_profile and mitigations
- Schedule: start month and seasonality
- Layout: unified center assumptions

## Comparison criteria (future)
CAPEX, OPEX, net savings, payback, VAN, expected risk, service level,
operational viability, labor impact.

## Non-goals now
This is conceptual design only. No implementation or UI changes in this step.
