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

## Link to economics
- The first route-to-economics bridge uses aggregate `PipelineResult` metrics:
  total routes, VRP routes, dedicated/trailer routes, distance, time, fleet mix
  and total packages.
- The selected operational alternative determines how the route result is
  interpreted: current structure, SVQ1 expansion, new/intermediate center, or
  DQA4 operational reference.
- The bridge does not change VRP constraints. Workday time and electric range
  remain the hard constraints, and van physical capacity remains inactive.
- New/intermediate centers can be used as a real depot only when represented by
  an existing OD node. Continuous locations must not invent road times.
- DQA4-related operating reductions feed economics only through partial,
  attributable activity for the SVQ1 -> DQA4 flow, not as full DQA4 shutdown
  savings.
