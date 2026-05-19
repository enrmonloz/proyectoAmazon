# PLANS

## Current state (snapshot)
- Streamlit UI orchestrates demand, split-delivery, VRP, location, warehouse, and economics.
- Demand supports market penetration, target volume calibration, seasonality, and validations.
- Location includes continuous methods and candidate comparison utilities (SVQ1, DQA4, intermediate).
- VRP is time-based with electric range as a hard constraint; van physical capacity is not active.
- Economics now exposes structured investment results for CAPEX/OPEX, net savings, payback, VAN/TIR and pessimistic outputs, while keeping the legacy table wrapper.
- The Economics UI now has a normal decision view with protected base data and an advanced sensitivity view with detailed editable parameters.
- Labor is modeled as a reusable economics submodel with one-off costs, annual costs, residual risks, and acceptability, derived from AdditionalCostParams for compatibility.
- Transition timeline is modeled as a standalone monthly block with phases, milestones, seasonal warnings, summary, and alternative start-month suggestion.
- Warehouse models are parameterized but not yet scenario-driven.
- Tests are smoke, compatibility, and economics-structure focused.

## Improvements completed
- Iteration 0: Demand calibration + seasonality + validations.
- Iteration 2: Economics structured by CAPEX/OPEX, gross/net savings, and pessimistic outputs while preserving existing UI tables.
- Iteration 3: Labor submodel for costs, policy support, residual risk, and acceptability while preserving current economics outputs.
- Iteration 4: Economics UI split into normal decision mode and advanced sensitivity mode.
- Iteration 5: Seasonal transition timeline with standalone UI and tests, without ScenarioConfig integration.

## Improvement in progress
- Iteration 1: Location by candidates (make candidate comparison the primary decision view).

## Next candidate improvements
- Clarify and document assumptions across modules.
- Strengthen validation for inputs and assumptions in pipeline.
- Connect routes outputs to economics inputs (future step).
- Connect LaborPolicyResult to the future ScenarioResult layer.
- Connect TimelineResult to the future ScenarioResult layer.

## Future roadmap (summary)
- ScenarioConfig/ScenarioResult layer.
- Scenario comparison and final recommendation.

## Decisions taken
- Use the enunciado as source of truth; no external data.
- Keep VRP focused on time and electric range.
- Keep UI separate from business logic.
- Keep the transition timeline informational; it does not decide viability by itself.

## Decisions pending
- Final weighting for candidate comparison (distance vs time).
- Scenario dimensions and default policies.
- How to surface assumptions in UI without clutter.
