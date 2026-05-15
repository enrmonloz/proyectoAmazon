---
name: logistics-review
description: Use this skill when reviewing changes to demand, routing, fleet, location, warehouse/layout, or logistics assumptions in the Amazon Sevilla SVQ1+DQA4 project.
---

# Logistics review skill

- Read docs/logistics_model.md and docs/assumptions.md first.
- Verify the change respects demand and routing assumptions.
- Check for mixing decisions across routing, location, and economics.
- Do not propose van physical capacity as an active solver constraint unless explicitly requested.
- Flag any change that alters workday time or electric range constraints.
