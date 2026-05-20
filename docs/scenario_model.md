# Scenario model (future design)

## Purpose
Define a top-layer scenario structure that coordinates demand, location, routing,
finance, risks, schedule, and layout without changing the current modules yet.
The scenario layer must compare project alternatives without treating DQA4 as a
center that fully disappears.

## ScenarioConfig (concept)
- id and name
- scenario_type (current structure, SVQ1 expansion, new joint/intermediate center)
- location_choice (current DQA4 last-mile structure, SVQ1, intermediate)
- investment_option
- demand_profile (target volume and seasonality)
- transition_plan (phasing, start month)
- labor_policy
- mitigations
- risk_profile
- dqa4_attributable_liberable_share (future concept only, not implemented yet)

## ScenarioResult (concept)
- operational metrics (routes, time, distance)
- finance metrics (CAPEX, OPEX, net savings, payback, VAN)
- labor metrics (direct cost, residual labor risk, acceptability)
- risk metrics (expected cost, residual risk)
- service metrics and notes
- transition timeline metrics (monthly phases, milestones, seasonal warnings)
- layout justification metrics or visuals (later, after scenarios are defined)

## Dimensions (future)
Ubicacion, tipo de escenario, inversion, demanda, transicion, politica laboral,
mitigaciones, mes de inicio, riesgo, porcentaje DQA4 atribuible/liberable.

## Scenario alternatives (future)
- Maintain current structure: SVQ1 remains fulfillment, DQA4 remains the last-mile center, and the current transfer flow stays as the comparison baseline.
- Expand SVQ1: absorb or release the SVQ1 -> DQA4 activity while DQA4 remains operational for other flows.
- New joint or intermediate center: compare a new/shared location against SVQ1 expansion.
- DQA4 is not a separate main scenario; it is represented inside the current structure.

## Module inputs (future)
- Demand: demand_profile, seasonality
- Location: location_choice or candidate set
- Routes: demand outputs and fleet policy
- Economics: CAPEX/OPEX, route totals, labor policy, DQA4 attributable/liberable share
- Risk: risk_profile and mitigations
- Transition timeline: start month, phase durations, milestones, and seasonality
- Layout: unified center assumptions, added later as scenario justification

## Current reusable pieces
- `src/timeline_model.py` already produces a standalone `TimelineResult` with monthly phases, critical milestones, warnings, summary, score, and suggested alternative start month.
- The timeline output is designed to be reusable by a future `ScenarioResult`, but it is not integrated into the global scenario layer yet.
- `src/economics_model.py` now exposes a first operational bridge with
  `OperationalSummary`, `LogisticsEconomicsBridge`, and
  `OperationalEconomicResult`. It connects aggregate route metrics to transfer
  saving, partial DQA4 saving, and route cost interpretation without creating a
  full ScenarioConfig/ScenarioResult.
- `src/risk_model.py` now exposes a decision-dependent residual-risk block with
  `RiskDecisionInputs`, `RiskResult`, and `RiskAssessment`. It consumes aggregate
  decisions and metrics but deliberately remains below the future global
  scenario layer.

## Comparison criteria (future)
CAPEX, OPEX, net savings, payback, VAN, expected risk, service level,
operational viability, labor impact.

## Non-goals now
The global `ScenarioConfig` / `ScenarioResult` layer remains conceptual. The
standalone timeline module, risk module, and UI sections do not rank full
scenarios or decide project viability by themselves.
Do not promote the DQA4 attributable/liberable percentage into a global scenario
input yet. It exists only inside the route-to-economics bridge and remains an
advanced, conservative assumption.
Do not make warehouse/layout a prerequisite for the first scenario layer.
Do not treat the new risk tab as Monte Carlo, simulation, or a full scenario
comparison engine.
