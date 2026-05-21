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
- Candidate comparison is the decision-facing layer (current structure with DQA4, SVQ1 expansion, intermediate).
- All techniques and candidates are evaluated with a common geometric euclidean distance in km.
- The OD matrix is now an explicit mode for route analysis, not the default for location comparison.
- Route usage labels: SVQ1 and DQA4 use existing OD, the midpoint requires external Excel,
  and continuous techniques are academic proxies.
- The new/intermediate center is selected automatically by comparing all
  location methods, SVQ1, DQA4, and the SVQ1-DQA4 midpoint by weighted mean
  geometric distance.
- DQA4 is the last-mile center in the current structure, not a separate main alternative and not a location choice that implies full closure of DQA4.

## Scope of SVQ1 -> DQA4 flow
- The logistics analysis focuses on the transfer flow from SVQ1 to DQA4.
- In the current structure, last-mile routes are evaluated from DQA4 and the SVQ1 -> DQA4 transfer remains in place.
- In SVQ1 expansion, last-mile routes are evaluated from SVQ1 for the analyzed flow.
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
  interpreted: current structure with DQA4 last mile, SVQ1 expansion, or
  new/intermediate center.
- The bridge does not change VRP constraints. Workday time and electric range
  remain the hard constraints, and van physical capacity remains inactive.
- New/intermediate centers can use an existing OD node when selected, or a
  virtual depot when the selected point is continuous. The virtual depot keeps
  existing OD matrices between municipalities intact and only estimates
  depot-to-node distance by straight-line coordinates and time by the internal
  median min/km ratio from the existing OD matrix.
- DQA4-related operating reductions feed economics only through partial,
  attributable activity for the SVQ1 -> DQA4 flow, not as full DQA4 shutdown
  savings.
