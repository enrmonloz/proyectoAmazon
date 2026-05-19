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
- DQA4 is now documented as a center that remains operational for non-SVQ1 flows; the project only evaluates the activity attributable to the SVQ1 -> DQA4 flow.
- Warehouse models are parameterized but intentionally postponed until scenarios are defined; layout is a later justification block, not a blocker for scenario modeling.
- Tests are smoke, compatibility, and economics-structure focused.

## Improvements completed
- Iteration 0: Demand calibration + seasonality + validations.
- Iteration 1: Location by candidates (SVQ1, DQA4 operational reference, and intermediate alternatives).
- Iteration 2: Economics structured by CAPEX/OPEX, gross/net savings, and pessimistic outputs while preserving existing UI tables.
- Iteration 3: Labor submodel for costs, policy support, residual risk, and acceptability while preserving current economics outputs.
- Iteration 4: Economics UI split into normal decision mode and advanced sensitivity mode.
- Iteration 5: Seasonal transition timeline with standalone UI and tests, without ScenarioConfig integration.
- Iteration 6: Roadmap and assumptions review for DQA4 partial activity and postponed layout.

## Improvement in progress
- None. The next iteration should start from the updated documentation baseline.

## Next candidate improvements
- Connect route/logistics outputs to economics inputs, using aggregate route totals without modifying VRP constraints.
- Make risks depend on scenario decisions after the route-to-economics link is clearer.
- Draft ScenarioConfig/ScenarioResult from the connected module outputs, without embedding scenario logic inside isolated UI tabs.
- Connect LaborPolicyResult to the future ScenarioResult layer.
- Connect TimelineResult to the future ScenarioResult layer.
- Keep a later academic simplification pass before the presentation.

## Future roadmap (summary)
- Routes/logistics -> economics connection.
- Decision-dependent risk model.
- ScenarioConfig/ScenarioResult layer.
- Scenario comparison and final recommendation.
- Warehouse/layout as a later justification block for the recommended scenario or for visual comparison of SVQ1 expansion vs a new center.

## Decisions taken
- Use the enunciado as source of truth; no external data.
- Keep VRP focused on time and electric range.
- Keep UI separate from business logic.
- Keep the transition timeline informational; it does not decide viability by itself.
- Do not model DQA4 as fully closed. DQA4 remains active for other fulfillment flows.
- Treat any DQA4 cost reduction as partial, attributable, or liberable only for the SVQ1 -> DQA4 flow.
- Keep the future "porcentaje atribuible/liberable de DQA4 asociado al flujo SVQ1 -> DQA4" as a documented concept, not a code parameter yet.
- Move warehouse/layout out of the main implementation path until scenarios are defined.

## Decisions pending
- Final weighting for candidate comparison (distance vs time).
- Scenario dimensions and default policies.
- Future method and default value for the DQA4 attributable/liberable percentage.
- Which route totals should feed OPEX first when connecting logistics to economics.
- How to surface assumptions in UI without clutter.
