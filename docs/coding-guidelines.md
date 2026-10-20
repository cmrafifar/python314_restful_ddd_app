# Coding Guidelines

Read when writing or reviewing Python. These are required conventions for new and changed code; existing inconsistencies do not authorize unrelated cleanup.

## Python and tools

- Use Python 3.14+ and annotate function parameters, return values, and meaningful stored state.
- Use four spaces, UTF-8, LF endings, and a final newline. Other files use two-space indentation where applicable.
- Use `snake_case` for modules, functions, and variables; `PascalCase` for classes; `UPPER_SNAKE_CASE` for constants.
- Use domain terms consistently. Prefer `book_id` and `isbn` over vague names such as `data` or `item`.
- Let Ruff handle formatting and import ordering. The configured line limit is 100 characters.
- BasedPyright uses standard checking overall and strict checking for domain and application code.

[pyproject.toml](../pyproject.toml) and [.editorconfig](../.editorconfig) are authoritative tool configuration. Do not duplicate tool configuration in new files.

## Design and responsibility

- Give each module and class one coherent responsibility. Separate business validation, orchestration, transport, and persistence.
- Keep functions understandable through names and control flow. Extract a helper when it names a distinct responsibility or removes meaningful duplication.
- Prefer explicit constructor dependencies. Do not hide database access or service lookup inside core code.
- Use small `Protocol` ports for capabilities a use case consumes. Follow the existing repository and unit-of-work boundaries.
- New adapters must honor the same return, failure, and transaction semantics as their ports. Type compatibility alone is insufficient.
- Prefer composition to inheritance for sharing behavior. Do not create base classes, factories, or interfaces without a current need.
- Extend behavior at the owning boundary. Avoid speculative extension points and abstractions that have no caller.

These practices apply SOLID through concrete responsibilities and dependencies, rather than maximizing the number of classes.

## Python idioms within familiar boundaries

Preserve the roles of routes, application services, domain entities, and persistence adapters. Their implementation need not reproduce Laravel's class structure or container conventions.

- Use `Protocol` for structural port contracts; adapters need not inherit a port solely to satisfy its type contract.
- Prefer ordinary functions for stateless behavior when a class would only wrap one function without adding a useful responsibility.
- Use dataclasses for suitable core data records and Pydantic models for boundary validation. Keep framework models outside the core.
- Use ordinary constructor dependencies in application and domain code. Register services through Dishka providers in `di/`; keep `FromDishka` annotations at HTTP boundaries. Do not resolve containers inside use cases. See [dependency injection](architecture.md#dependency-injection) for registration and lifetime rules.
- Keep SQLAlchemy models separate from domain entities. Do not assume Eloquent-style active-record behavior or automatic persistence of domain-object mutations.
- Use context managers for resource ownership and pytest fixtures for test setup. Explain their lifecycle implications when introducing them.
- Choose synchronous or asynchronous execution based on the complete I/O path and learning objective. Do not add `async` merely because FastAPI supports it.

When a Python choice differs from a familiar PHP/Laravel approach, briefly explain the reason and relevant tradeoff. Basic HTTP and backend architecture explanations are unnecessary unless requested.

## Domain types and validation

Use value objects when a concept has meaningful validation or equality semantics, such as `ISBN`. Use immutable command/result records for data crossing the application boundary, following the existing frozen dataclasses.

Keep business invariants in the domain even when an HTTP schema also validates input. Transport validation handles request shape; domain validation protects rules for every caller.

For example, a create-book use case constructs `ISBN(command.isbn)` and calls `Book.create(...)`. It does not reimplement checksum or title validation. See [domain rules](domain/books.md).

## Errors and resource ownership

- Raise errors at the layer that understands them. Current domain validation uses `ValueError`; duplicate creation uses `BookAlreadyExistsError`.
- Catch specific errors where recovery or translation is possible. Do not silently swallow failures or turn unexpected errors into successful responses.
- Keep HTTP statuses and framework exceptions out of domain and application code.
- Keep SQLAlchemy exceptions out of port contracts. Translate expected persistence failures at the adapter boundary when implementing that behavior.
- Use context managers for resource lifecycles. Preserve explicit commit and rollback ownership described in [architecture](architecture.md).

## Readability and scope

Write comments for intent, constraints, or non-obvious tradeoffs. Keep public behavior and examples accurate; avoid comments that narrate individual assignments.

Keep edits focused. Do not reformat unrelated files, weaken type checks, or add dependencies to avoid understanding an existing boundary. Update relevant docs and regression tests when behavior changes. Follow [testing](testing.md) for validation.
