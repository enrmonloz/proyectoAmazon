# Improvement roadmap

## 0. Demand calibration and seasonality (done)
- Objective: Ensure demand can be calibrated and seasonality is explicit.
- Why it matters: Demand drives routes, fleet, and economics.
- Likely modules: src/demand.py, src/pipeline.py, tests.
- Priority: High (completed).
- Not yet: Do not change the VRP solver or scenario layer here.

## 1. Assumptions cleanup and validations
- Objective: Make assumptions consistent across modules and UI.
- Why it matters: Avoid silent model drift.
- Likely modules: docs/assumptions.md, src/pipeline.py, UI sections.
- Priority: High.
- Not yet: Do not add new data sources.

## 2. Candidate-oriented location
- Objective: Compare SVQ1, DQA4, and intermediate candidates explicitly.
- Why it matters: The decision is about discrete alternatives.
- Likely modules: src/location_solver.py, src/location_view.py.
- Priority: High.
- Not yet: Do not mix economics into location logic.

## 3. Structured economics by components
- Objective: Separate CAPEX, OPEX, and net savings.
- Why it matters: Scenario comparison needs consistent finance blocks.
- Likely modules: src/economics_model.py, docs/finance_model.md.
- Priority: Medium.
- Not yet: Do not implement scenario layers yet.

## 4. Human resources submodel
- Objective: Represent workforce impacts and policies explicitly.
- Why it matters: HR is a major viability driver.
- Likely modules: docs/logistics_model.md, docs/finance_model.md.
- Priority: Medium.
- Not yet: Do not replace existing economics defaults.

## 5. Risk model dependent on decisions
- Objective: Make risks vary by location and transition choices.
- Why it matters: Risk changes the recommendation.
- Likely modules: src/economics_model.py, docs/risk_model.md.
- Priority: Medium.
- Not yet: Do not rework the VRP solver.

## 6. Schedule with seasonality (done as standalone timeline)
- Objective: Align transition plans with demand seasonality.
- Why it matters: Timing affects service risk and cost.
- Implemented modules: src/timeline_model.py, src/project_sections.py, app.py.
- Priority: Medium.
- Done: Monthly transition phases, milestones, fixed seasonal profile, warnings, summary, and simple alternative start-month suggestion.
- Not yet: Do not integrate into the global ScenarioConfig/ScenarioResult layer without a separate plan.

## 7. Warehouse/layout for unified center
- Objective: Tie layout assumptions to unification options.
- Why it matters: Layout drives capacity and efficiency.
- Likely modules: src/warehouse_model.py.
- Priority: Medium.
- Not yet: Do not change MATLAB parity baselines.

## 8. Connect routes to economics
- Objective: Feed routing totals into OPEX calculations.
- Why it matters: Operational outputs must affect finance.
- Likely modules: src/pipeline.py, src/economics_model.py.
- Priority: High.
- Not yet: Do not modify routing constraints.

## 9. ScenarioConfig / ScenarioResult layer
- Objective: Centralize scenario inputs and outputs.
- Why it matters: Consistent comparison across decisions.
- Likely modules: docs/scenario_model.md, new scenario module.
- Priority: Medium.
- Not yet: Do not add a global refactor without plan.

## 10. Scenario comparator
- Objective: Rank scenarios by service, finance, and risk.
- Why it matters: Supports the final recommendation.
- Likely modules: scenario comparison utilities, UI.
- Priority: Medium.
- Not yet: Do not change test strategy yet.

## 11. Final recommendation synthesis
- Objective: Produce a defensible recommendation summary.
- Why it matters: It is the end goal of the project.
- Likely modules: UI sections, report outputs.
- Priority: Medium.
- Not yet: Do not introduce new data sources.
