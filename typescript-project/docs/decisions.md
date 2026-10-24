# Technology and design decisions

These records describe the implemented project and its tradeoffs. The goal is practical TypeScript
backend experience with recognizable open-source tools, clear DDD boundaries, and an independently
runnable catalog. Framework familiarity supports job preparation; it does not guarantee hiring,
compensation, or a particular tool's market share.

## 1. NestJS with built-in dependency injection

**Decision:** Use Nest modules, controllers, providers, and Express. Compose the plain BookCatalog
application service through a factory provider. Domain and application code do not import Nest.

**Reason:** Nest supplies established routing, dependency injection, lifecycle management, and
validation integration. It replaces FastAPI plus Dishka at the application boundary without
creating a second container or custom framework.

**Tradeoff:** Decorators and framework metadata add explicit configuration. Keeping Nest outside
the core requires deliberate provider wiring. The catalog remains a modular monolith; CQRS,
microservices, and generic service frameworks are not required by its current behavior.

## 2. Prisma ORM with PostgreSQL

**Decision:** Use Prisma's generated client with its PostgreSQL adapter, committed SQL migrations,
and explicit mapping between persistence records and domain objects.

**Reason:** Generated query types and schema tooling provide a practical TypeScript persistence
workflow. PostgreSQL supplies transactions, unique constraints, and the SQL operations required
by the catalog. This is a standalone database choice, not a migration of the Python MySQL data.

**Tradeoff:** Prisma is not a SQLAlchemy identity map or unit of work. Domain objects are not ORM
entities, and saving changes requires explicit adapter operations. Literal substring filtering
uses bound SQL fragments where they express the contract more directly than model operations.
Substring searches may scan despite bounded page sizes.

Migrations own the schema, including the SQL version constraint. Review generated SQL before
applying it. Prisma has no automatic Alembic-style downgrade; use reviewed forward fixes and
backups when recovery requires them. See README for mutation commands.

## 3. Callback transactions and optimistic concurrency

**Decision:** Expose a small application transaction interface. Its Prisma adapter supplies a
transaction-bound repository; successful callbacks commit and thrown errors roll back.

**Reason:** This follows Prisma's interactive transaction lifecycle while preserving application
ownership of transaction boundaries. It replaces Python's explicit commit pattern rather than
imitating SQLAlchemy sessions.

**Tradeoff:** All database work within a use case must use the supplied repository. Transactions
use PostgreSQL Read Committed isolation. Version predicates and affected-row checks protect
updates and deletions; the ISBN unique constraint protects creation races. Conflicts surface to
callers without automatic retries. Comprehensive concurrent-write and rollback proof remains
deferred with automated tests.

## 4. DTO validation and generated API documentation

**Decision:** Use class-validator and class-transformer with Nest's global ValidationPipe. Map
and validate successful response DTOs explicitly. Use `@nestjs/swagger` and its compiler plugin
for OpenAPI and Swagger UI; host ReDoc against the same specification.

**Reason:** These libraries integrate with Nest's class-based request handling and metadata.
They cover the runtime boundary that TypeScript's erased types cannot protect.

**Tradeoff:** Pydantic's responsibilities span several components here. OpenAPI annotations,
request validation, response validation, and domain rules must remain consistent. ReDoc uses a
pinned CDN script. Nest's standard validation envelope and 400 status differ from FastAPI;
see [API conventions](api-conventions.md) for the implemented contract.

## 5. Strict TypeScript, ESLint, and Prettier

**Decision:** Use strict TypeScript compilation, type-aware typescript-eslint rules, ESLint,
and Prettier. ESLint also restricts framework imports into domain and application code.

**Reason:** TypeScript covers static typing analogous to BasedPyright. ESLint covers lint and
promise misuse; Prettier owns formatting. Together they cover the roles served by BasedPyright
and Ruff without forcing a one-to-one tool mapping.

**Tradeoff:** Multiple configurations must agree, and type-aware linting requires generated
Prisma types. Formatting does not prove correctness. Compiler, lint, and build success do not
establish behavior or persistence guarantees.

## 6. Pinned Node Current, pnpm, and native ESM

**Decision:** Pin Node and pnpm in project metadata and runtime files. Use native ESM with
NodeNext resolution and `.js` extensions in relative source imports. Commit `pnpm-lock.yaml`.

**Reason:** The user explicitly requested the latest stable Node runtime and pnpm. ESM matches
the selected framework and generated-client configuration. Frozen lockfile installs keep local
and container dependency resolution reproducible.

**Tradeoff and upgrade policy:** Current has a faster lifecycle than LTS. This is a learning
project's explicit runtime choice; reassess deployment support when preparing a production
release. Do not use floating `latest` tags as compatibility evidence. Check package stability,
Node support, compiler peer ranges, Prisma generation, and container compatibility before
upgrading. Update package metadata, lockfile, runtime version files, and Dockerfile together
when applicable. Run the documented static checks and build, then verify affected HTTP and
database behavior. Add automated regression checks when testing is authorized.

The initial dependency versions are recorded in package.json and README; this document does not
claim those versions remain the newest releases. Compiler and ORM upgrades must respect the
selected libraries' compatibility ranges, even when newer versions exist.

## 7. Separate container stack and deferred tests

**Decision:** Keep this directory independently runnable with its own Dockerfile, Compose project,
PostgreSQL volume, and ports. A migration service must succeed before the API starts. The runtime
image uses production dependencies and an unprivileged user.

**Reason:** Side-by-side operation preserves the Python reference and models a future independent
repository without nested Git metadata or external file dependencies.

**Tradeoff:** Compose is a local development workflow, not a complete production deployment design.
Process liveness does not prove database readiness. Example credentials are local defaults.

Automated tests and testing dependencies are explicitly deferred by user request. Planned tools
are Jest, `@nestjs/testing`, Supertest, and a dedicated PostgreSQL test database. Do not install
them or claim coverage until that work is requested. Manual checks remain limited evidence.
