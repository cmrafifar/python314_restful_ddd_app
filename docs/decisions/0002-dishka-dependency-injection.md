# 0002: Dishka dependency injection

Status: Accepted
Date: 2026-10-20

## Context

The create-book route used a custom dependency annotation alias and a request-based resolver
that retrieved its service from `app.state`. Service construction lived separately in `main.py`.
This made the service type and registration harder to discover. The project needs an ergonomic,
modular registration pattern while preserving ordinary Python constructors and hexagonal boundaries.

## Decision

Use Dishka with a synchronous container and its FastAPI integration. Keep an explicit provider
registry in `di/container.py`, with cohesive providers under `di/providers/`. Register simple
services through constructor autowiring and use provider methods for adapter construction and
resource cleanup. HTTP routers use `DishkaSyncRoute` and direct `FromDishka[ServiceType]` parameters.

Keep Dishka outside application and domain code. Keep the existing unit-of-work factory contract:
each use-case execution creates a new unit of work and session, and the use case explicitly commits.
The container owns application resources, including engine disposal on shutdown.

## Alternatives

- Retain FastAPI dependency functions and application-state service storage. This adds no package,
  but preserves the lookup plumbing and indirect registration that prompted this decision.
- Continue manual assembly with more explicit route annotations. This improves type visibility but
  requires handwritten factories as the dependency graph grows.
- Use Dependency Injector or Wireup. Both support modular assembly; Dishka was chosen for its
  external provider registration, constructor autowiring, scopes, and FastAPI integration.

## Consequences

Registration is centralized and searchable, while service constructors remain framework independent.
Provider overrides allow HTTP tests to replace services or ports without modifying application state.
Dependencies are lazy: an unused engine is never created and therefore needs no disposal.

The project gains a runtime dependency and container-specific registration conventions. Autowiring
does not select adapter implementations or transaction boundaries; providers must define those
bindings explicitly. Application-scoped services must not retain request state or active sessions.

## Verification

API tests cover service replacement, autowired service execution, duplicate handling, validation,
and engine disposal. Container tests cover isolation and fresh sessions per unit of work. Run
pytest, Ruff lint and format checks, and BasedPyright. Live MySQL tests remain a separate gate.

## References

- [Dependency injection rules](../architecture.md#dependency-injection)
- [Container registry](../../src/bookstore_api/di/container.py)
- [Dishka providers](https://dishka.readthedocs.io/en/stable/provider/index.html)
- [Dishka FastAPI integration](https://dishka.readthedocs.io/en/stable/integrations/fastapi.html)
