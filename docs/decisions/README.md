# Architecture Decision Records

Read when making or revisiting a significant design choice. This directory stores decisions and their rationale; [architecture](../architecture.md) describes the current system and required boundaries.

## When to record a decision

Record a choice when alternatives and consequences matter to future work: a boundary change, a new external dependency, transaction semantics, or a public contract with substantial compatibility costs.

Routine implementation details do not need a decision record. Existing code alone does not establish the historical reason it was written. No historical decision records have been reconstructed for this documentation setup.

## Records

- [0001: Learning strategy and catalog scope](0001-learning-strategy.md) — Accepted.

## Naming and lifecycle

Use sequential names such as `0001-descriptive-decision.md`. Check existing numbers before creating one.

Use `Proposed`, `Accepted`, `Rejected`, or `Superseded` as the status. A proposed record does not authorize implementation. Mark a choice accepted only when the task or review establishes it. Link a replacement when superseding an accepted record; preserve the old rationale.

## Template

```markdown
# 0001: Descriptive decision

Status: Proposed
Date: YYYY-MM-DD

## Context

What concrete problem or constraint requires a decision?

## Decision

What will we do, and where does it apply?

## Alternatives

Which realistic alternatives were considered, and why were they not chosen?

## Consequences

What benefits, costs, limitations, and compatibility effects follow?

## Verification

Which tests or checks demonstrate that the decision holds?

## References

Link relevant code, domain rules, issues, and related decisions.
```

Keep each record focused on one decision. Update the relevant topic document when an accepted decision changes a rule; link the record for rationale rather than duplicating its contents.
