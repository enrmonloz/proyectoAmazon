# Finance model evolution

## Current baseline
- economics_model.py reproduces enunciado parameters and investment options.
- Fleet costs are parameterized from the provided Excel inputs.
- Investment options now produce a structured EconomicResult before being
  converted to the legacy DataFrame used by the UI.
- The Streamlit economics tab separates a normal decision view from an advanced
  sensitivity view. The normal view keeps base case data read-only and exposes
  only key decisions, while the advanced view keeps detailed editable parameters.
- DQA4 costs shown in the baseline describe the current case, but the project
  interpretation does not assume that all DQA4 costs disappear.

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

## DQA4 partial savings interpretation
- DQA4 remains operational for flows outside SVQ1 -> DQA4.
- Any DQA4-related saving should be interpreted as partial, attributable, or
  liberable for the SVQ1 -> DQA4 flow, not as a full shutdown saving.
- A future route-to-economics iteration should define a "porcentaje
  atribuible/liberable de DQA4 asociado al flujo SVQ1 -> DQA4" before applying
  DQA4 cost reductions to structured finance outputs.
- This percentage is not implemented in economics_model.py yet; current defaults
  preserve the existing economic behavior and should be explained with this
  limitation when used in presentation.

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
- Connect DQA4 attributable/liberable activity to finance inputs without assuming total DQA4 closure.

## Metrics
- Payback, VAN/NPV, and IRR/TIR where applicable.
- Connect operational outputs (routes, fleet, labor) to finance inputs.
