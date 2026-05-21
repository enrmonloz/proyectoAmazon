# Improvement roadmap

## 0. Demand calibration and seasonality (done)
- Objective: Ensure demand can be calibrated and seasonality is explicit.
- Why it matters: Demand drives routes, fleet, and economics.
- Likely modules: src/demand.py, src/pipeline.py, tests.
- Priority: High (completed).
- Not yet: Do not change the VRP solver or scenario layer here.

## 1. Candidate-oriented location (done)
- Objective: Compare SVQ1, DQA4, and intermediate candidates explicitly.
- Why it matters: The decision is about discrete alternatives.
- Implemented modules: src/location_solver.py, location UI.
- Priority: High (completed).
- Done: Candidate comparison treats SVQ1 as an existing expansion candidate, DQA4 as an operational reference, and intermediate options as decision-facing alternatives.
- Not yet: Do not mix economics into location logic.

## 2. Structured economics by components (done)
- Objective: Separate CAPEX, OPEX, and net savings.
- Why it matters: Scenario comparison needs consistent finance blocks.
- Implemented modules: src/economics_model.py, docs/finance_model.md.
- Priority: Medium (completed).
- Done: Structured EconomicResult, pessimistic outputs, and compatibility wrapper.
- Not yet: Do not implement scenario layers yet.

## 3. Human resources submodel (done)
- Objective: Represent workforce impacts and policies explicitly.
- Why it matters: HR is a major viability driver.
- Implemented modules: src/economics_model.py, docs/assumptions.md, docs/finance_model.md.
- Priority: Medium (completed).
- Done: Labor policy costs, residual labor risks, and acceptability summary.
- Not yet: Do not replace existing economics defaults.

## 4. Economics UI simplification (done)
- Objective: Separate normal decision view from advanced sensitivity.
- Why it matters: The project must be explainable in class without hiding advanced controls.
- Implemented modules: src/project_sections.py.
- Priority: Medium (completed).
- Done: Normal economics view protects base data and advanced view keeps detailed parameters.
- Not yet: Do not turn the UI into a global scenario comparator.

## 5. Schedule with seasonality (done as standalone timeline)
- Objective: Align transition plans with demand seasonality.
- Why it matters: Timing affects service risk and cost.
- Implemented modules: src/timeline_model.py, src/project_sections.py, app.py.
- Priority: Medium (completed).
- Done: Monthly transition phases, milestones, fixed seasonal profile, warnings, summary, and simple alternative start-month suggestion.
- Done now: The first ScenarioResult layer consumes TimelineResult, while the timeline remains standalone and does not decide viability by itself.

## 6. Assumptions and roadmap cleanup (done as documentation)
- Objective: Make the roadmap and assumptions consistent before adding new modules.
- Why it matters: Avoid presenting DQA4 as fully closed and avoid making layout a blocker.
- Updated modules: PLANS.md, docs/assumptions.md, docs/scenario_model.md, docs/logistics_model.md, docs/finance_model.md, docs/risk_model.md.
- Priority: High (completed).
- Done: DQA4 remains operational for other flows; only the SVQ1 -> DQA4 activity is in scope; future economics should use an attributable/liberable share of DQA4 activity.
- Done now: ScenarioConfig/ScenarioResult exist as a first integration layer; assumptions remain based on project docs and the enunciado.

## 7. Connect routes to economics (done as initial bridge)
- Objective: Feed routing totals into OPEX calculations.
- Why it matters: Operational outputs must affect finance before scenario comparison is defensible.
- Implemented modules: src/economics_model.py, src/data_loader.py, app.py, src/project_sections.py.
- Priority: High (completed as first bridge).
- Done: Aggregate route totals are summarized, operational alternatives drive the economic interpretation, transfer savings are alternative-specific, and DQA4 savings use a partial `dqa4_attributable_share`.
- Done now: The bridge is consumed by ScenarioResult when a pipeline_result is available. Do not modify routing constraints, demand, or VRP here.

## 8. Risk model dependent on decisions (done)
- Objective: Make risks vary by location, transition, labor policy, and mitigation choices.
- Why it matters: Risk changes the recommendation.
- Implemented modules: src/risk_model.py, src/project_sections.py, tests/test_risk_model.py.
- Priority: Medium (completed).
- Done: Decision-dependent residual risks consume center choice, route aggregates, investment, labor support, mitigations, seasonality, operational saving, and timeline warnings.
- Not yet: Do not rework the VRP solver or model DQA4 closure as a risk baseline.

## 9. ScenarioConfig / ScenarioResult layer (done as v1)
- Objective: Centralize scenario inputs and outputs.
- Why it matters: Consistent comparison across decisions.
- Implemented modules: src/scenario_model.py, src/project_sections.py, app.py, tests/test_scenario_model.py, docs/scenario_model.md.
- Priority: Medium (completed as first integration layer).
- Done: ScenarioConfig groups decisions and ScenarioResult groups economy, operation, labor, cronograma, risks, warnings, and interpretation. It works even without calculated routes by returning a partial result with warning.
- Not yet: Do not add multi-scenario comparison, ranking, final recommendation, or layout integration here.

## 10. Scenario comparator (done as guided flow)
- Objective: Compare scenarios by service, finance, risk, labor, and timeline
  without turning the result into an automatic final recommendation.
- Why it matters: Supports the final presentation and makes the app follow a
  decision flow instead of isolated tabs.
- Implemented modules: src/scenario_comparator.py, src/project_sections.py,
  app.py, tests/test_scenario_comparator.py.
- Priority: Medium (completed as first comparator).
- Done: The app has global `Flujo guiado` and `Análisis por módulos` views.
  The scenario comparator remains available through the advanced laboratory,
  using existing ScenarioResult outputs.
- Not yet: Do not add weighted ranking, Monte Carlo, multiobjective
  optimization, or a definitive recommendation.

## 10b. Guided flow simplification (done)
- Objective: Replace the main guided entry point with the same reasoning order
  as the academic memory: demand, location, routes, economics, conclusion.
- Why it matters: The presentation view should be understandable without the
  scenario-tree controls, sensitivity panels, risk detail, or warehouse/layout.
- Implemented modules: src/project_sections.py, app.py, PLANS.md,
  docs/scenario_model.md.
- Priority: Medium (completed as academic simplification).
- Done: `Flujo guiado` now shows a clean memory-style chain. The configurable
  scenario tree remains available as an advanced laboratory under
  `Análisis por módulos`.
- Not yet: Do not turn the conclusion into an aggressive automatic
  recommendation.

## 10c. Guided academic constructor (done)
- Objective: Make `Flujo guiado` editable without reintroducing the advanced
  scenario tree.
- Why it matters: The presentation view should let a non-technical user follow
  and adjust the memory flow step by step on a single page.
- Implemented modules: src/guided_flow.py, src/project_sections.py,
  tests/test_guided_flow.py, PLANS.md, docs/scenario_model.md.
- Done: The guided page now exposes compact controls for demand, location,
  routes, economics, and conclusion; long technical tables stay in expanders.
  Route runs are explicit and cached so economic edits reuse route outputs.
- Not yet: Do not move combinatorial axes, weighted ranking, or final automatic
  recommendation into the guided page.

## 11. Final recommendation synthesis
- Objective: Produce a defensible recommendation summary.
- Why it matters: It is the end goal of the project.
- Likely modules: UI sections, report outputs.
- Priority: Medium.
- Not yet: Do not introduce new data sources.

## 12. Warehouse/layout justification (postponed)
- Objective: Use layout to explain the recommended scenario or compare SVQ1 expansion vs a new center visually.
- Why it matters: Layout supports the final story once scenario comparison exists, but should not decide scenarios first.
- Likely modules: src/warehouse_model.py, docs/logistics_model.md.
- Priority: Later.
- Not yet: Do not change MATLAB parity baselines or block ScenarioConfig/ScenarioResult design on layout.
