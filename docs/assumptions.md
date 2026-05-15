# Model assumptions

## Demand
- Population is used as a proxy for demand.
- Market penetration can be calibrated to a target daily volume.
- Seasonality is applied as a multiplier after base demand.
- The depot always has 0 packages and 0 service time.

## Routing and fleet
- Van physical capacity is NOT an active solver constraint.
- Workday time is the primary hard limit.
- Electric vehicles also respect a hard range limit.

## Location
- Continuous location outputs are mathematical references, not real parcels.

## Economics and risk
- Economics start from enunciado parameters and internal defaults.
- Risks are initially simplified and may be static.

## Data boundaries
- No external data sources are used unless explicitly requested.
