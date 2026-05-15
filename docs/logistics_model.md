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

## Warehouse/layout
- Dimensioning and ABC layout models are parameterized.

## Link to economics (future)
- Route totals and fleet mix should feed OPEX in scenario analysis.
