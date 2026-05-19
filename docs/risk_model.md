# Risk model evolution

## Categories
Operational, technological, labor, financial, legal/union, schedule.

## Method
- Probability x impact.
- Mitigations reduce probability or impact.
- Residual risk tracked explicitly.

## Current state
- Risks are simplified and mostly static in the economic model.
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

## Target state (future)
- Risks depend on scenario decisions (location, transition plan, labor policy).
- Mitigations are represented in ScenarioConfig.
- Risk exposure should use the same DQA4 attributable/liberable share that future
  finance calculations use for the SVQ1 -> DQA4 flow.
