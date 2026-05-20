# Scenario model

## Purpose
Define a top-layer scenario structure that coordinates existing demand/routing
outputs, finance, labor, risks, and schedule without changing the underlying
modules. The scenario layer supports a defensible viability analysis, but it is
not a real Amazon forecast and does not decide the final recommendation.

## Implemented v1
`src/scenario_model.py` now provides a first integration layer:

- `ScenarioConfig` groups the main decisions: scenario name, operational
  center option, investment option, labor support, mitigation flags, start
  month, and conservative DQA4 attributable/liberable share.
- `ScenarioResult` groups existing outputs: `EconomicResult`,
  optional `OperationalEconomicResult`, `LaborPolicyResult`,
  `TimelineResult`, `RiskAssessment`, headline savings, CAPEX, risk cost,
  warnings, and a brief interpretation.
- `build_scenario_result(...)` reuses existing functions from economics,
  labor, timeline, operational bridge, and risk modules. It does not run the
  VRP internally; if no `pipeline_result` is provided, it returns a partial
  result with a clear warning.
- `scenario_result_to_frame_row(...)` and `scenario_results_frame(...)`
  prepare simple summary rows for future tables.

## Current UI
The Streamlit app includes a simple `📊 Escenario` tab called "Escenario
actual". It shows decisions, CAPEX total, annual net savings, adjusted
operational saving, total expected residual risk cost, labor acceptability,
timeline high alerts, interpretation, and warnings.

## Current reusable pieces
- `src/timeline_model.py` produces a standalone `TimelineResult` with monthly
  phases, critical milestones, warnings, summary, score, and suggested
  alternative start month.
- `src/economics_model.py` exposes structured finance, labor policy results,
  and the route-to-economics bridge with `OperationalEconomicResult`.
- `src/risk_model.py` exposes decision-dependent residual risk through
  `RiskDecisionInputs`, `RiskResult`, and `RiskAssessment`.

## Non-goals now
- No multi-scenario comparator.
- No ranking, scoring engine, or automatic final recommendation.
- No warehouse/layout integration into `ScenarioResult` yet.
- No changes to VRP, demand, location, base finance, risk, or timeline logic.
- DQA4 is not modeled as fully closed; any DQA4 saving remains partial,
  attributable, or liberable only for the SVQ1 -> DQA4 flow.

## Future work
- Add a compact comparator that consumes multiple `ScenarioResult` objects.
- Decide the final comparison criteria and weights only after scenario outputs
  are stable.
- Use warehouse/layout later as justification for a selected scenario or visual
  comparison, not as a prerequisite for this v1 layer.
