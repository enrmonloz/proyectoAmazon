# Amazon Sevilla SVQ1 + DQA4 - Agent Instructions

## Project summary
This repository contains a Streamlit app that analyzes a logistics case in Sevilla.
The project compares scenarios for a possible unification of SVQ1 and DQA4.

## Goal
Deliver a defensible, scenario-based viability analysis (not a real Amazon forecast).

## Workflow
- Plan before Edit. Always propose a plan before changing files.
- State files you will touch and files you will not touch in every iteration.

## Golden rules
- Do not invent external data. Use docs and the enunciado as source of truth.
- Do not fix inconsistencies in the enunciado unless asked.
- Keep tests passing and do not weaken them.
- Prefer small, reversible, documented changes.
- Keep business logic in src/ and UI in Streamlit views.

## Project-specific rules
- Demand uses population as a proxy and already supports calibration and seasonality.
- Van physical capacity is NOT an active solver constraint.
- VRP focuses on workday time and electric range as hard constraints.
- Location work must evolve toward candidate comparison (SVQ1, DQA4, intermediate).
- Economics should evolve toward CAPEX/OPEX, net savings, and risk.
- The global scenario model is a future objective, not current logic.

## Required context
- Use docs/ as the primary context for assumptions and model intent.
- Check PLANS.md before proposing new iterations or larger changes.

## Change protocol
- Before editing, list the exact files to modify.
- Also list the files you will NOT touch.
- If changes affect assumptions or roadmap, update docs/ and PLANS.md.

## Review
- Use docs/code_review.md as a checklist before requesting a review.
