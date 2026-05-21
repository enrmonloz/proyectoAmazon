# Model assumptions

## Demand
- Population is used as a proxy for demand.
- Default market penetration is 1.064%; it remains editable in the Streamlit UI
  and can still be overridden by target-volume calibration.
- Market penetration can be calibrated to a target daily volume.
- Seasonality is applied as a multiplier after base demand.
- The depot always has 0 packages and 0 service time.

## Routing and fleet
- Van physical capacity is NOT an active solver constraint.
- Workday time is the primary hard limit.
- Electric vehicles also respect a hard range limit.
- Default trailer assumptions are 4,000 packages per trip and 90 minutes of
  unloading time per trailer route; both remain editable technical parameters.
- The guided flow route comparison uses `data/rutasDistTiempo_v2.csv`, the
  current OD matrix with candidate depots represented as real OD nodes.
- Route operating costs in the guided flow use internal constants only; no
  spreadsheet or external cost file is read by the model.
- The route-cost formula is:
  `route_cost = km * variable_cost_per_km + (time_min / 60) * time_cost_per_hour`.
  This avoids adding a total per-km cost and a total per-hour cost that would
  duplicate cost components.
- Official 2026 route-cost constants used as medium reference values:
  furgoneta `variable_cost_per_km = 0.3035`, `time_cost_per_hour = 25.47`,
  `working_days_per_year = 225`; trailer/articulado
  `variable_cost_per_km = 0.6670`, `time_cost_per_hour = 43.80`,
  `working_days_per_year = 225`.
- Source for those constants: Observatorio de Costes del Transporte de
  Mercancías por Carretera, enero 2026.
- These are average operating-cost references for scenario comparison, not
  real Amazon costs or an Amazon forecast.

## Location
- Continuous location outputs are mathematical references, not real parcels.
- Location comparison uses a common geometric euclidean distance in km for all techniques and candidates.
- The OD matrix is only used explicitly for route analysis; it is not the default for location comparison.
- The new/intermediate center is chosen internally and automatically from all
  location methods plus SVQ1, DQA4, and the SVQ1-DQA4 midpoint, using weighted
  mean geometric distance as the primary criterion.
- The integrated comparison table treats the SVQ1-DQA4 midpoint as an academic contrast.
- Location does not reuse geometric distances as real route distances.
- In the guided flow, DQA4, SVQ1, the location-reference center, and the
  heuristic intermediate center are routed from OD v2 nodes. No virtual depot is
  used for those centers.
- DQA4 is part of the current structure as the last-mile center, not a separate main operational alternative.

## Scope and DQA4 partial activity
- The project analyzes the logistics and economic effect of the SVQ1 -> DQA4 flow described in the enunciado.
- The main operational comparison is: current structure with DQA4 as last-mile center, SVQ1 expansion, and a new/intermediate center.
- DQA4 is not modeled as fully closed. It remains operational for packages and flows received from other fulfillment centers.
- Reductions in DQA4 cost, labor, space, or operating activity must be interpreted as partial, attributable, or liberable for the SVQ1 -> DQA4 flow, not as automatic removal of all DQA4 costs.
- The first route-to-economics bridge introduces `dqa4_attributable_share` as
  the documented "porcentaje atribuible/liberable de DQA4 asociado al flujo
  SVQ1 -> DQA4".
- The default value is 10%, deliberately conservative, and is editable only in
  the advanced economics view.
- This percentage is not a full scenario input yet and must not be read as a
  full DQA4 shutdown assumption.

## Labor
- Labor defaults come from `docs/sintesis_enunciado_proyecto.md`: 915 total employees, 245 DQA4 employees affected, 28 extra daily km, 1.56 M€ training, 441 k€/year corporate transport, 187 k€/year public transport subsidy, 450 k€ one-off compensation, and 3.25 M€/year regulation 2025 cost.
- Training and one-off compensation are transition costs. Corporate transport, public transport subsidy, recurring incentives, and labor regulation are annual costs.
- Labor regulation is not included as incremental by default, preserving the current economic baseline.
- Labor risk defaults are resignations 35% x 1.28 M€, resistance to change 45% x 0.75 M€, and union conflicts 25% x 2.1 M€.
- Transport support reduces labor-risk probability by simple documented factors: corporate transport 25%/15%/10%, public subsidy 15%/8%/5%, one-off compensation 5%/3%/3%, and no support 0%/0%/0% for resignations/resistance/conflicts.
- Employee incentives use the 70% effectiveness stated in the enunciado as a probability-reduction factor. Training additionally reduces resistance risk by 10%, and incremental regulation compliance reduces union-conflict risk by 5%.
- Labor acceptability is classified by first-year labor cash cost plus residual expected labor risk: Alta up to 3.0 M€, Media up to 6.0 M€, Baja above 6.0 M€.

## Economics and risk
- Economics start from enunciado parameters and internal defaults.
- Gross savings should not be read as full DQA4 shutdown savings. Any DQA4-related reduction must be tied to the activity attributable/liberable from the SVQ1 -> DQA4 flow.
- Risks are initially simplified and may be static.
- The guided economics block uses the annual route-cost differential against DQA4, not the absolute route cost, to measure the penalty of changing the departure center.
- The guided economics block also shows an absolute annual-cost reading using
  current-cost data from the enunciado: SVQ1 36.2 M€/year, DQA4 18.1 M€/year,
  SVQ1-DQA4 transfers 1.99 M€/year, for a total current structure of
  56.29 M€/year.
- The current-cost breakdown from the enunciado is SVQ1: personal 20.7 M€/year,
  energy/fuel 6.2 M€/year, facilities 2.4 M€/year, other 7.0 M€/year; DQA4:
  personal 9.1 M€/year, energy/fuel 4.7 M€/year, facilities 1.5 M€/year, other
  2.8 M€/year.
- The absolute annual cost is an approximate presentation reading:
  `current_total_annual_cost - average_annual_net_saving`. It is not a real
  Amazon forecast.
- CAPEX is not added to the absolute annual cost. CAPEX remains an initial
  investment shown separately and used in VAN/payback calculations.
- The guided block summarizes annual savings with Beta-PERT: (O + 4M + P) / 6, with a 15-year horizon and 8% discount rate.
- In the guided block, personal and energy savings follow a simple learning curve of 50% / 75% / 100% in years 1, 2, and 3-15; transfer elimination and one-installation savings are full from year 1.
- The guided block keeps CAPEX and mitigation decisions separate from the advanced VAN/TIR module.

## Transition timeline
- The transition timeline is a standalone monthly model, not a real calendar forecast.
- The standard transition uses the enunciado phases: 4 months preparation, 6 construction, 4 migration, and 3 finalization.
- Critical milestones follow the enunciado months: month 2 union agreement, month 8 construction finished, month 10 systems running, and month 14 migration complete.
- The monthly seasonality profile is fixed and discrete: January-March 0.85, April-June 1.00, July-September 1.08, and October-December 1.25.
- July-December is treated as high season; October-December is treated as the critical peak to avoid for operational changes.
- Timeline warnings are informational and do not decide viability by themselves.

## Data boundaries
- No external data sources are used unless explicitly requested.
- The guided flow uses the provided OD v2 matrix for route distances and times.
- The advanced laboratory may still use a documented virtual-depot fallback for
  continuous points not represented in an OD matrix.
- `docs/sintesis_enunciado_proyecto.md` remains the base synthesis of the enunciado. This assumptions file records project interpretation where the model needs a narrower, defensible scope.

## Warehouse/layout timing
- Warehouse and ABC layout models remain available but are postponed in the roadmap.
- Layout should support the explanation of a recommended scenario or a visual comparison after scenarios are defined.
- Layout should not block route-to-economics work or the future ScenarioConfig/ScenarioResult layer.
