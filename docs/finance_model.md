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

## Target structure (future)
- Connect structured finance outputs to ScenarioResult.
- Add expected risk cost and scenario sensitivity.
- Connect route, fleet and labor outputs to finance inputs.

## Metrics
- Payback, VAN/NPV, and IRR/TIR where applicable.
- Connect operational outputs (routes, fleet, labor) to finance inputs.
