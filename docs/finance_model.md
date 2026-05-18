# Finance model evolution

## Current baseline
- economics_model.py reproduces enunciado parameters and investment options.
- Fleet costs are parameterized from the provided Excel inputs.
- Investment options now produce a structured EconomicResult before being
  converted to the legacy DataFrame used by the UI.

## Structured investment output
- EconomicResult separates base CAPEX, transition CAPEX, total CAPEX, gross
  annual savings, new annual OPEX, net annual savings, payback, VAN/NPV and TIR.
- PessimisticResult keeps the existing pessimistic logic explicit: total CAPEX
  is multiplied by the pessimistic CAPEX factor and net annual savings by the
  pessimistic savings factor.
- capex_infra, capex_tech and capex_it remain informational fields from the
  investment option. They are not automatically summed into CAPEX total in this
  iteration, preserving the previous model behavior.
- analyze_options remains the compatibility wrapper and returns the same
  columns as before.

## Labor block
- economics_model.py now exposes a reusable labor submodel with LaborBaselineParams,
  LaborPolicyParams, LaborPolicyResult, LaborImpactSummary, and labor risk results.
- The labor block separates one-off transition costs from annual recurring costs:
  training, initial incentives, and one-off compensation are one-off costs;
  transport support, retention incentives, and optional labor regulation are
  annual recurring costs.
- AdditionalCostParams remains the source used by the current economic calculation.
  labor_policy_from_additional and labor_policy_result_from_additional derive a
  labor view from those parameters without changing compute_economic_result or
  analyze_options outputs.
- The Streamlit economic tab only displays the labor result as an optional summary.
  It does not add mandatory inputs or change default financial results.

## Target structure (future)
- Connect structured finance outputs to ScenarioResult.
- Add expected risk cost and scenario sensitivity.
- Connect route, fleet and labor outputs to finance inputs.

## Metrics
- Payback, VAN/NPV, and IRR/TIR where applicable.
- Connect operational outputs (routes, fleet, labor) to finance inputs.
