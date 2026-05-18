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
- Risks are initially simplified and may be static.

## Data boundaries
- No external data sources are used unless explicitly requested.
