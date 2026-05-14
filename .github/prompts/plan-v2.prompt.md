## Plan: Demand calibration and seasonality (SVQ1 + DQA4)

Short TL;DR: Expand demand model to support target-volume calibration and a seasonality multiplier while preserving the current penetration-based behavior; add validations and tests; expose minimal UI inputs; keep the pipeline compatible.

## Task Classification
- Category: Local module improvement; validation improvement; test coverage improvement; scenario-model preparation.
- Scope level: Demand + pipeline wiring + minimal UI + tests.
- Expected risk: Low.
- Main module(s): [src/demand.py](src/demand.py), [src/pipeline.py](src/pipeline.py), [app.py](app.py), [tests/test_pipeline.py](tests/test_pipeline.py).

## Objective
Improve demand so it is clearer, calibrable to a known daily volume, and seasonally adjustable, without changing the global model or VRP flow. This keeps assumptions traceable and prepares future scenario work.

## Current State
- Enunciado: [docs/sintesis_enunciado_proyecto.md](docs/sintesis_enunciado_proyecto.md) provides daily volume (38,900 packages/day for DQA4), seasonal bands (low -15%, summer +8%, peak +25%), and the unification context.
- Demand model: `DemandConfig`, `compute_packages`, and `compute_node_service_time` live in [src/demand.py](src/demand.py). Packages are computed as `round(population * market_penetration)` and depot packages are forced to 0; service time is packages times per-package minutes.
- Pipeline integration: [src/pipeline.py](src/pipeline.py) creates `DemandConfig` via `PipelineConfig.to_demand_config()` and `run_pipeline()` uses `compute_packages` and `compute_node_service_time` before split-delivery and VRP.
- Data loading: [src/data_loader.py](src/data_loader.py) loads [data/poblacion.csv](data/poblacion.csv), sets `depot_index` from `DEPOT_NAME`, and supplies `dataset.poblacion`.
- UI entry: demand inputs are in `render_config_panel()` and wired in `build_pipeline_config()` in [app.py](app.py) (penetration %, service time, inter-package time).
- Tests: [tests/test_pipeline.py](tests/test_pipeline.py) validates demand basics and split-delivery; [tests/test_project_models.py](tests/test_project_models.py) covers other models and should remain unaffected.

## Conceptual Issue
Demand is currently a single-parameter penetration model with no explicit calibration to a known daily volume and no seasonality multiplier. This limits alignment with the academic case and reduces traceability for future scenario comparison.

## Scope

### In scope
- Extend `DemandConfig` to carry optional target-volume calibration and a seasonality multiplier, with defaults that preserve current behavior.
- Add helper functions in [src/demand.py](src/demand.py) to compute implied penetration from a target volume and to apply seasonality after base demand is computed.
- Add validations for penetration bounds, positive target volume, positive seasonality multiplier, non-negative packages, depot packages = 0, and positive total demand when inputs imply demand.
- Update `PipelineConfig` and `build_pipeline_config()` to pass new demand fields with defaults.
- Add demand-focused tests to [tests/test_pipeline.py](tests/test_pipeline.py) to cover fixed penetration, calibration, seasonality, depot handling, and validations.

### Out of scope
- No scenario model or `ScenarioConfig`.
- No changes to VRP solver, split-delivery logic, fleet, economics, warehouse, or location modules.
- No external data or dependency additions.
- No UI redesign beyond minimal new inputs if needed to expose the new demand options.

## Proposed Design
- `DemandConfig` additions in [src/demand.py](src/demand.py):
  - `seasonality_multiplier: float = 1.0` (applied after base demand).
  - `target_daily_volume: float | None = None` (when set, compute implied penetration).
- New helper functions in [src/demand.py](src/demand.py):
  - `calibrate_market_penetration(poblacion, depot_index, target_daily_volume) -> float` to compute $target / sum(population_excluding_depot)$ with validation and bounds.
  - `apply_seasonality(packages, seasonality_multiplier) -> np.ndarray` to scale the base package vector and round to integers.
- `compute_packages` behavior:
  - Validate config first.
  - If `target_daily_volume` is set, compute implied penetration and use it; otherwise use `market_penetration`.
  - Compute base packages as today, then apply `seasonality_multiplier` to the base package vector (not to population).
  - Enforce non-negative packages and force depot to 0 after scaling.
  - If penetration or target volume implies demand, raise if total packages are not positive.
- `compute_node_service_time` remains unchanged and continues to scale with packages.
- Pipeline compatibility:
  - Add optional fields to `PipelineConfig` with defaults, pass them into `DemandConfig` in `to_demand_config()`.
  - `run_pipeline()` call sites and return types remain unchanged.
- UI (minimal exposure) in [app.py](app.py):
  - Add a seasonality selector with presets (Base 1.00, Low 0.85, Summer 1.08, Peak 1.25).
  - Add an optional checkbox and numeric input for target daily volume; when unchecked, keep current behavior.
  - Defaults keep identical output to today (Base seasonality, no target volume).
- Documentation (optional, small):
  - Add a short note in [src/demand.py](src/demand.py) docstring or in [README.md](README.md) clarifying population as a proxy and the new calibration option.

## Relevant Files
- [src/demand.py](src/demand.py) - add config fields, calibration and seasonality helpers, extend validation, update `compute_packages`, keep `compute_node_service_time` compatible.
- [src/pipeline.py](src/pipeline.py) - extend `PipelineConfig` with optional demand fields and pass them through `to_demand_config()`.
- [app.py](app.py) - add minimal demand inputs (seasonality preset, optional target volume), pass to `build_pipeline_config()`.
- [tests/test_pipeline.py](tests/test_pipeline.py) - add unit-style demand tests and validation coverage; keep existing smoke checks.
- [README.md](README.md) - optional short note about demand assumptions and calibration.

## Implementation Steps
1. Demand model: update `DemandConfig`, add validation rules, and add `calibrate_market_penetration` and `apply_seasonality` in [src/demand.py](src/demand.py).
2. Demand computation: update `compute_packages` to use target-volume calibration when present, apply seasonality after base packages, and enforce depot zero and non-negative packages.
3. Pipeline wiring: extend `PipelineConfig` and `to_demand_config()` in [src/pipeline.py](src/pipeline.py) to pass new fields with defaults.
4. UI wiring: add seasonality presets and optional target volume inputs in `render_config_panel()` and pass them in `build_pipeline_config()` in [app.py](app.py).
5. Tests: extend [tests/test_pipeline.py](tests/test_pipeline.py) with demand-focused tests and validation checks.
6. Verification pass: run the tests and confirm defaults preserve current outputs.

## Verification
- Run `python3 tests/test_pipeline.py` to cover new and existing demand checks.
- Run `python3 tests/test_project_models.py` to confirm unrelated model tests still pass.
- Manually verify the Streamlit default run (Base seasonality, no target volume) produces the same totals as before.

## Tests to Add or Update
- Fixed penetration: small synthetic population vector, verify packages and depot 0.
- Target calibration: `calibrate_market_penetration` returns expected value and `compute_packages` produces the expected total (allowing rounding).
- Seasonality: multiplier scales base packages after estimation and keeps depot at 0.
- Validations: penetration outside [0,1], target volume <= 0, seasonality <= 0, and target volume implying penetration > 1 should raise.
- Compatibility: default `DemandConfig` path still passes the existing smoke test in [tests/test_pipeline.py](tests/test_pipeline.py).

## Assumptions and Decisions
- Population is a proxy for demand; target volume refers to daily packages across non-depot nodes.
- Seasonality is applied after base packages are estimated, then rounded.
- If `target_daily_volume` is provided it overrides `market_penetration` for package calculation; `market_penetration` remains a fallback.
- Default behavior stays unchanged when `target_daily_volume` is None and `seasonality_multiplier` is 1.0.

## Risks and Mitigations
- Risk: stricter validation could break flows if defaults are wrong. Mitigation: keep defaults that preserve current behavior and add regression checks.
- Risk: target volume could imply penetration > 1 or yield zero packages after rounding. Mitigation: validate bounds, document approximate nature, and raise on impossible targets.
- Risk: UI changes could confuse users. Mitigation: keep optional controls off by default with short help text.

## Acceptance Criteria
- `compute_packages` returns identical results to the current implementation when `target_daily_volume` is None and `seasonality_multiplier` is 1.0.
- Calibration and seasonality functions pass their unit tests.
- Depot packages remain 0 and service time at depot remains 0.
- All existing tests pass and new demand tests cover the requested cases.
- `run_pipeline()` works with current UI defaults and no VRP changes.

## Summary for Edit Mode
- Update [src/demand.py](src/demand.py) with new config fields, validation, calibration helper, seasonality application, and adjusted `compute_packages`.
- Wire demand fields through [src/pipeline.py](src/pipeline.py) and [app.py](app.py) with defaults that preserve existing behavior.
- Add demand tests to [tests/test_pipeline.py](tests/test_pipeline.py) for fixed penetration, target calibration, seasonality, depot zero, and validation errors.
- Run smoke tests and confirm default outputs unchanged.
