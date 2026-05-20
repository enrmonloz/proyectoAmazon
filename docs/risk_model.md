# Risk model evolution

## Categories
Operational, technological, labor, financial, legal/union, schedule.

## Method
- Probability x impact.
- Mitigations reduce probability or impact.
- Residual risk tracked explicitly.

## Current state
- Risks are simplified and mostly static in the economic model.
- A new standalone module, `src/risk_model.py`, now calculates decision-dependent
  residual risks without changing economics, VRP, demand, location, or layout.
- The current formula is intentionally simple: base probability and base impact
  are multiplied by decision modifiers to obtain residual probability, residual
  impact, and residual expected cost.
- The implemented categories are operational, technological, labor, financial,
  schedule, and legal/union.
- The base probabilities and impacts are internal modelling defaults for this
  academic viability analysis, not external forecasts.
- Inputs are aggregate and decision-facing: selected center, route totals,
  dedicated routes, trailers, distance, time, vehicle count, investment option,
  labor support, labor acceptability, phasing, backup systems, training,
  incentives, seasonality, adjusted operational saving, start month, and
  schedule warnings.
- The Streamlit app exposes the model in a main "Riesgos" tab. If routes have
  not been calculated yet, route-dependent exposure is shown with empty route
  metrics and no adjusted operational saving.
- Labor risks now have a dedicated residual-risk calculation in economics_model.py:
  resignations, resistance to change, and union conflicts keep base probability x
  impact values from the enunciado and apply explicit mitigation factors from the
  selected labor policy.
- Labor mitigation is policy-driven: transport support, incentives, training,
  and optional labor regulation can reduce residual probability. The assumptions
  are documented in assumptions.md and remain configurable through LaborPolicyParams.
- Transition and labor risks concern the activity affected by the SVQ1 -> DQA4
  flow. They should not be read as risks from closing all DQA4 activity.
- DQA4 continues operating for other flows, so future risk scenarios should
  distinguish partial migration/release from full-site closure.
- Any economic saving associated with DQA4 remains partial/attributable. The
  risk tab does not infer full closure of DQA4.

## Decision modifiers currently used
- Operational risk increases with route volume, dedicated routes, high season,
  and approximate intermediate centers. It falls with phasing and favorable
  schedule conditions.
- Technological risk increases with basic investment and no backup systems. It
  falls with backup systems and standard/premium investment.
- Labor risk increases with no labor support and low/medium acceptability. It
  falls with transport support, incentives, and training.
- Financial risk increases with a new/intermediate center, premium investment,
  and low or negative adjusted operational saving. It falls with positive saving
  and reuse of existing infrastructure.
- Schedule risk increases when critical milestones fall in October-December or
  when the timeline has high-severity warnings. It falls with a favorable start
  month and phased transition.
- Legal/union risk increases with low labor acceptability and no phased
  transition. It falls with labor support, phases, and training.

## Target state (future)
- Risks depend on scenario decisions (location, transition plan, labor policy).
- Mitigations are represented in ScenarioConfig.
- Risk exposure should use the same DQA4 attributable/liberable share that future
  finance calculations use for the SVQ1 -> DQA4 flow.
