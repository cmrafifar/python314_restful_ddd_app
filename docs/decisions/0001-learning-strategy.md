# 0001: Learning strategy and catalog scope

Status: Accepted
Date: 2026-10-19

## Context

The developer is a senior backend engineer experienced with PHP 8.4 and Laravel 12. The project exists to learn Python 3.14+ and its frameworks and libraries through a familiar DDD and hexagonal architecture.

There is no external business stakeholder or fixed product requirement. The developer has delegated contrived business requirements to the AI collaborator. This decision records the direction chosen now, without asserting historical reasons for existing code.

## Decision

Use a small bookstore catalog as the teaching domain. A Book represents one edition in one format, with a UUID identifying its catalog record and one catalog record per ISBN. Keep inventory, orders, lending, and pricing outside the initial scope.

Preserve domain/application independence, explicit ports, adapter boundaries, and transaction ownership. Use idiomatic Python within those boundaries rather than translating Laravel patterns literally.

Professional quality will be demonstrated through correctness, clear responsibilities, useful typing, deliberate error handling, and meaningful verification. Additional architecture needs a concrete requirement or an explicit learning objective.

The next planned slice is HTTP creation and retrieval backed by MySQL, including validation, duplicate handling, and transaction evidence. This decision does not claim that slice has been implemented.

## Alternatives

- Let each feature invent its own business meaning. This makes examples inconsistent and obscures domain modeling lessons.
- Reproduce Laravel conventions directly. This preserves familiarity but misses Python's structural typing, functions, dataclasses, and resource-management idioms.
- Use framework models throughout the system. This reduces initial mapping but conflicts with the chosen independent domain and application boundaries.
- Begin with inventory and ordering. This adds business complexity before the existing create-book flow is exposed and verified end to end.

## Consequences

The domain stays small enough to make Python and persistence behavior visible. Some explicit mapping and wiring remain intentional costs of the chosen boundaries.

Teaching should focus on differences that matter to an experienced backend engineer: protocols, dataclasses, boundary validation, SQLAlchemy sessions, dependency wiring, pytest fixtures, and sync/async tradeoffs.

The AI collaborator may choose requirements for this exercise and must explain consequential decisions. Unimplemented choices remain labeled as plans or required rules rather than described as current behavior.

## Verification

Review changes against the dependency rules in the architecture document. Prove new behavior at its owning layer, use MySQL integration tests for database semantics, and verify new HTTP contracts through route tests.

No runtime behavior changes with this documentation decision. The existing limitations remain documented until implementation and verification address them.

## References

- [Learning goals](../../README.md#learning-goals-and-working-approach)
- [Architecture](../architecture.md)
- [Python coding guidance](../coding-guidelines.md#python-idioms-within-familiar-boundaries)
- [Books domain](../domain/books.md)
- [Testing](../testing.md)
