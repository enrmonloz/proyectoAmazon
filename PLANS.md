# PLANS

## Current state (snapshot)
- Streamlit UI orchestrates demand, split-delivery, VRP, location, warehouse, and economics.
- Demand supports market penetration, target volume calibration, seasonality, and validations.
- Location includes continuous methods and candidate comparison utilities (SVQ1, DQA4, intermediate).
- VRP is time-based with electric range as a hard constraint; van physical capacity is not active.
- Economics now exposes structured investment results for CAPEX/OPEX, net savings, payback, VAN/TIR and pessimistic outputs, while keeping the legacy table wrapper.
- Warehouse models are parameterized but not yet scenario-driven.
- Tests are smoke, compatibility, and economics-structure focused.

## Improvements completed
- Iteration 0: Demand calibration + seasonality + validations.
- Iteration 2: Economics structured by CAPEX/OPEX, gross/net savings, and pessimistic outputs while preserving existing UI tables.

## Improvement in progress
- Iteration 1: Location by candidates (make candidate comparison the primary decision view).

## Next candidate improvements
- Clarify and document assumptions across modules.
- Strengthen validation for inputs and assumptions in pipeline.
- Connect routes outputs to economics inputs (future step).

## Future roadmap (summary)
- ScenarioConfig/ScenarioResult layer.
- Scenario comparison and final recommendation.

## Decisions taken
- Use the enunciado as source of truth; no external data.
- Keep VRP focused on time and electric range.
- Keep UI separate from business logic.

## Decisions pending
- Final weighting for candidate comparison (distance vs time).
- Scenario dimensions and default policies.
- How to surface assumptions in UI without clutter.
