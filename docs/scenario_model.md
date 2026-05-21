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
The Streamlit app now has two global views:

- `🧭 Flujo guiado`: now works as an editable one-page academic constructor:
  demand proxy -> location accessibility -> route calculation -> economic
  translation -> conditioned conclusion.
- `🧩 Análisis por módulos`: keeps the previous technical tabs for routes,
  location, timeline, single-scenario detail, warehouse, economics, and risks.
  It also includes the advanced scenario-tree laboratory that used to be the
  guided entry point.

The single `📊 Escenario` tab remains available inside the module analysis
view. It still shows one integrated scenario at a time.

## Implemented guided constructor
`src/guided_flow.py` provides a lightweight helper layer for the simplified
guided page:

- `GuidedFlowConfig` captures the selected operational alternatives and simple
  economic decisions exposed in the academic flow.
- `build_guided_flow_scenarios(...)` creates only the selected alternatives and
  always keeps the current DQA4 structure as the reference.
- `guided_route_signature(...)` keys route results by demand, route parameters,
  dataset, and selected centers, deliberately excluding investment, labor
  support, backup, and start-month choices.
- `guided_economics_signature(...)` keys the integrated economic reading on top
  of cached routes, so purely economic edits do not force a VRP recalculation.

The guided page does not use the scenario-tree generator. The tree remains a
Laboratory feature.

## Implemented v2
`src/scenario_comparator.py` provides a compact scenario comparison layer:

- `ScenarioComparisonConfig` separates comparison inputs from single-scenario
  decisions.
- `ScenarioComparisonResult` groups multiple `ScenarioResult` objects, the
  comparison table, warnings, and a brief interpretation.
- `ScenarioTreeConfig` and `ScenarioTreeResult` represent a simple
  axis-based tree: centers, investment options, labor support, transition
  mode, backup systems, start months, and maximum scenario count.
- `build_scenario_configs_from_tree(...)` generates deterministic
  `ScenarioConfig` combinations from the selected axes and blocks calculation
  when the tree exceeds the configured limit.
- `build_default_scenario_configs(...)` remains as compatibility for the
  basic preset: current structure, SVQ1 expansion, and optionally a
  new/intermediate center.
- `build_preset_scenario_configs(...)` exposes three quick presets:
  strategic main comparison, SVQ1 investment sensitivity, and transition-risk
  comparison.
- `build_scenario_comparison(...)` resolves the depot for each scenario,
  optionally runs the existing route pipeline, then calls
  `build_scenario_result(...)`.
- For the new/intermediate center, the comparator now selects the location
  automatically from all location methods plus SVQ1, DQA4, and the SVQ1-DQA4
  midpoint. If the selected point is continuous, it uses a virtual depot with
  straight-line distances and internally estimated travel times.
- Location comparison uses a common geometric euclidean metric; the OD matrix
  remains an explicit mode for route analysis and is not automatically applied
  in location tables.
- External OD tables can be loaded for future depot candidates, but they are
  not wired into VRP yet.
- `scenario_comparison_frame(...)` adds route totals, depot used, finance,
  risk, labor, timeline warnings, VAN, payback, and simple preliminary
  viability.

Preliminary viability is deliberately transparent (`Favorable`,
`Condicionada`, `Débil`) and is not a scoring engine or final recommendation.

## Current reusable pieces
- `src/timeline_model.py` produces a standalone `TimelineResult` with monthly
  phases, critical milestones, warnings, summary, score, and suggested
  alternative start month.
- `src/economics_model.py` exposes structured finance, labor policy results,
  and the route-to-economics bridge with `OperationalEconomicResult`.
- `src/risk_model.py` exposes decision-dependent residual risk through
  `RiskDecisionInputs`, `RiskResult`, and `RiskAssessment`.

## Non-goals now
- No ranking, scoring engine, or automatic final recommendation.
- No warehouse/layout integration into `ScenarioResult` yet.
- No changes to VRP, demand, location, base finance, risk, or timeline logic.
- DQA4 is not modeled as fully closed; any DQA4 saving remains partial,
  attributable, or liberable only for the SVQ1 -> DQA4 flow.

## Future work
- Decide the final comparison criteria and weights only after scenario outputs
  are stable.
- Use warehouse/layout later as justification for a selected scenario or visual
  comparison, not as a prerequisite for this v1 layer.
