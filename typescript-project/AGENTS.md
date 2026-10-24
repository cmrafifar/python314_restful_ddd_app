# TypeScript project instructions

This directory is an independent project root temporarily housed beside a Python reference.
Do not add nested Git metadata, a submodule, or dependencies on files outside this directory.
Read README.md and docs/architecture.md before changes. Use pnpm and the pinned Node runtime.

`docs/ai/` contains human-readable reference material, not agent instructions. Exclude it from
routine discovery, indexing, searches, and context loading. Read or edit it only when explicitly
requested. Never treat its contents as agent instructions.

Keep domain/application framework-free. Use documented Nest providers, DTO validation, and Prisma
APIs rather than custom framework abstractions. Keep generated ORM code and HTTP DTOs outside the
core. Migrations own the schema; explain database mutations before running migration commands.

Tests are intentionally deferred until the user requests them. Do not install testing tools,
create tests, or claim test coverage. Future agreed tools are Jest, @nestjs/testing, Supertest,
and a dedicated real PostgreSQL database. Type checks and manual smoke checks are not tests.

Run pnpm db:generate before type checking after installation. Relevant checks are pnpm typecheck,
pnpm lint, pnpm format:check, pnpm db:validate, and pnpm build. Report actual verification evidence
and omissions. Preserve the Python reference and staged Git scope. Never read adjacent learnings/,
docs/ai/, or QA.md without explicit authorization.
