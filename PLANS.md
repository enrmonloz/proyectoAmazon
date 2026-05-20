# PLANS

## Current state (snapshot)
- Streamlit UI orchestrates demand, split-delivery, VRP, location, scenario summary, warehouse, economics, and risks.
- Demand supports market penetration, target volume calibration, seasonality, and validations.
- Location includes continuous methods and candidate comparison utilities (current DQA4 last-mile structure, SVQ1, intermediate).
- VRP is time-based with electric range as a hard constraint; van physical capacity is not active.
- Economics now exposes structured investment results for CAPEX/OPEX, net savings, payback, VAN/TIR and pessimistic outputs, while keeping the legacy table wrapper.
- A first logistics-economics bridge connects aggregate route metrics to transfer saving, partial DQA4 saving, fleet cost interpretation, and alternative-specific warnings without changing the base VAN model.
- The Economics UI now has a normal decision view with protected base data and an advanced sensitivity view with detailed editable parameters.
- Labor is modeled as a reusable economics submodel with one-off costs, annual costs, residual risks, and acceptability, derived from AdditionalCostParams for compatibility.
- Transition timeline is modeled as a standalone monthly block with phases, milestones, seasonal warnings, summary, and alternative start-month suggestion.
- Decision-dependent risks are now modeled in a standalone risk module and a
  main Streamlit tab, using center choice, route aggregates, investment, labor
  policy, mitigations, seasonality, adjusted operational saving, and timeline
  warnings.
- ScenarioConfig and ScenarioResult now exist as a first integration layer in
  src/scenario_model.py. They group existing economy, operational bridge,
  labor, timeline, and risk outputs without running VRP internally or ranking
  scenarios.
- A first scenario comparator now exists in src/scenario_comparator.py. It
  builds alternatives from presets or a configurable scenario tree, resolves
  depots per scenario, runs existing routes when possible, constructs
  ScenarioResult objects, and returns a presentation-oriented comparison table
  with transparent preliminary viability.
- The Streamlit app now separates the decision flow into global views:
  `Flujo guiado` for configurable scenario-tree comparison and `Análisis por
  módulos` for the existing technical tabs.
- DQA4 is now documented as a center that remains operational for non-SVQ1 flows; the project only evaluates the activity attributable to the SVQ1 -> DQA4 flow.
- Warehouse models are parameterized but intentionally postponed until scenario comparison or recommendation is defined; layout is a later justification block, not a blocker for scenario modeling.
- Tests are smoke, compatibility, economics-structure, scenario-integration, and risk-behavior focused.

## Improvements completed
- Iteration 0: Demand calibration + seasonality + validations.
- Iteration 1: Location by candidates (SVQ1, DQA4 as current last-mile reference, and intermediate alternatives).
- Iteration 2: Economics structured by CAPEX/OPEX, gross/net savings, and pessimistic outputs while preserving existing UI tables.
- Iteration 3: Labor submodel for costs, policy support, residual risk, and acceptability while preserving current economics outputs.
- Iteration 4: Economics UI split into normal decision mode and advanced sensitivity mode.
- Iteration 5: Seasonal transition timeline with standalone UI and tests, without ScenarioConfig integration.
- Iteration 6: Roadmap and assumptions review for DQA4 partial activity and postponed layout.
- Iteration 7: Initial route/logistics -> economics bridge with operational alternatives, safe depot selection, partial DQA4 share, UI summary, and tests.
- Iteration 8: Corrected the route/logistics -> economics bridge so DQA4 is no longer a separate main alternative; current structure routes last mile from DQA4, SVQ1 expansion routes from SVQ1, and DQA4 remains operational for other flows.
- Iteration 9: Added a simple decision-dependent residual-risk model and main
  Risks UI tab without implementing ScenarioConfig/ScenarioResult.
- Iteration 10: Added ScenarioConfig/ScenarioResult as a first integration
  layer, plus a simple Scenario UI tab and minimal tests, without adding a
  comparator or automatic recommendation.
- Iteration 11: Added a guided scenario comparator and a light UI
  reorganization into global guided/module views. The comparator reuses
  ScenarioConfig/ScenarioResult, run_pipeline, and depot switching without
  changing VRP, demand, economics, risks, timeline, or warehouse/layout.
- Iteration 12: Refactored the guided comparator from fixed scenarios to a
  configurable axis-based scenario tree with quick presets, scenario review,
  exclusions, and a default 12-scenario limit.
- Iteration 13: Focused the quick presets into three presentation-ready sets:
  strategic main comparison, SVQ1 investment sensitivity, and transition-risk
  comparison.

## Improvement in progress
- None. The next iteration should start from the guided scenario comparator baseline.

## Next candidate improvements
- Decide explicit comparison criteria before adding any ranking.
- Keep final recommendation synthesis separate from the scenario data layer.
- Keep a later academic simplification pass before the presentation.

## Future roadmap (summary)
- Final recommendation synthesis, after the comparator outputs are stable.
- Warehouse/layout as a later justification block for the recommended scenario or for visual comparison of SVQ1 expansion vs a new center.

## Decisions taken
- Use the enunciado as source of truth; no external data.
- Keep VRP focused on time and electric range.
- Keep UI separate from business logic.
- Keep the transition timeline informational; it does not decide viability by itself.
- Do not model DQA4 as fully closed. DQA4 remains active for other fulfillment flows.
- Treat any DQA4 cost reduction as partial, attributable, or liberable only for the SVQ1 -> DQA4 flow.
- Use `dqa4_attributable_share` in ScenarioConfig and the operational bridge; default 10% and never as full DQA4 closure.
- Move warehouse/layout out of the main implementation path until scenario comparison is defined.

## Decisions pending
- Final weighting for candidate comparison (distance vs time).
- Whether the DQA4 attributable/liberable share should remain 10% or become scenario-specific.
- Which route totals should feed future scenario comparison beyond the current bridge.
- How to surface assumptions in UI without clutter.
