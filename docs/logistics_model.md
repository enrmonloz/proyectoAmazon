# Logistics model

## Demand
- Population proxy -> packages per node.
- Optional calibration to target volume.
- Seasonality multiplier.
- Depot has zero demand.

## Routing and workday
- VRP minimizes vehicles with time-based constraints.
- Workday time is the primary bottleneck.
- Electric range is a hard constraint for EVs.
- Van physical capacity is NOT an active constraint (documented only).

## Split delivery and trailers
- Oversized nodes get dedicated routes.
- Trailer option can replace van dedicated routes for large nodes.

## Location
- Continuous methods are mathematical references.
- Candidate comparison is the decision-facing layer (SVQ1, DQA4, intermediate).
- DQA4 is a reference for the current last-mile operation, not a location choice that implies full closure of DQA4.

## Scope of SVQ1 -> DQA4 flow
- The logistics analysis focuses on the transfer flow from SVQ1 to DQA4.
- DQA4 also handles packages from other fulfillment centers, so it remains operational outside the modeled SVQ1 -> DQA4 flow.
- Future scenario work should separate total DQA4 activity from the part attributable or liberable because of changes to the SVQ1 -> DQA4 flow.
- The future "porcentaje atribuible/liberable de DQA4 asociado al flujo SVQ1 -> DQA4" should be defined before using DQA4 reductions in economics.

## Warehouse/layout
- Dimensioning and ABC layout models are parameterized.
- Layout is postponed until scenario alternatives are defined.
- Layout should explain or visually compare a selected scenario, not block route, economics, or scenario modeling.

## Link to economics (future)
- Route totals and fleet mix should feed OPEX in scenario analysis.
- DQA4-related operating reductions should feed economics only through partial/attributable activity, not as full DQA4 shutdown savings.
