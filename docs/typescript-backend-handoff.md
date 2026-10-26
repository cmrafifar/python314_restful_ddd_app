# TypeScript Backend Learning Project: Handoff

Prepared: 2026-10-23. Target: remote backend engineering roles in the United States.

## Ultimate goal

Help an experienced PHP 8.4/Laravel 12 backend engineer become fluent in modern JavaScript,
TypeScript, Node.js, and their production ecosystem. Build a small, professionally engineered
bookstore API using idiomatic libraries, DDD, and hexagonal boundaries. Use the project to
develop demonstrable skills for well-paid US remote backend roles.

This is an adaptation of the Python bookstore learning project, not a mechanical translation.
Preserve its learning strategy: familiar business and architectural boundaries make language,
framework, persistence, and operational differences visible. Explain consequential choices
through comparisons with Laravel and the Python implementation, without reteaching basic
backend engineering.

Success means the developer can independently implement, test, deploy, debug, and explain a
TypeScript backend. Framework vocabulary alone is insufficient. No stack guarantees placement,
compensation, or an easy hiring process. Position the developer as an experienced backend
engineer adding TypeScript expertise, not as a beginner restarting their career.

## Handoff scope and current status

This document defines the proposed TypeScript project and its teaching workflow. It does not
authorize scaffolding, rewriting the Python application, migrating existing data, or deploying
paid infrastructure. No TypeScript implementation or passing TypeScript checks are claimed.

The source project's README, architecture, domain, API conventions, testing guide, learning
strategy decision, and task inventory were reviewed. The inventory currently marks catalog
creation, retrieval, conditional updates/deletion, filtering, and bidirectional keyset pagination
complete. That is inventory evidence, not a fresh execution of its tests.

Create the TypeScript project separately when implementation is authorized. Treat the Python
project as a behavioral reference. A fresh PostgreSQL schema and seed data are sufficient;
production data migration and exact HTTP compatibility are separate requirements.

## Recommended stack

Use mature, supported stable releases with a supported Node.js LTS. Verify compatibility and
licenses at project initialization, pin the runtime and package manager, and commit a lockfile.
Do not select prereleases merely because they are newer.

| Capability | Default choice | Reason |
|---|---|---|
| Language | TypeScript with strict compiler checks | Learn sound boundaries, inference, and everyday production types |
| Runtime | Node.js LTS | Learn the runtime used beneath the framework |
| HTTP framework | NestJS with its default Express adapter | Learn modules, controllers, providers, guards, pipes, filters, and lifecycle hooks |
| Dependency injection | Nest's built-in container | Avoid a second container; wire plain core services with factory providers |
| Database | PostgreSQL | Build transferable relational modeling, SQL, indexing, and concurrency skills |
| Persistence | Prisma ORM and its migration tooling | Typed database access, explicit mapping, and versioned schema changes |
| Request validation | Nest `ValidationPipe`, `class-validator`, and `class-transformer` | Follow Nest's documented DTO workflow |
| HTTP documentation | `@nestjs/swagger` and OpenAPI | Maintain an executable, reviewable API contract |
| Testing | Jest, `@nestjs/testing`, and Supertest | Isolated core tests, provider overrides, and HTTP verification |
| Database verification | A dedicated real PostgreSQL instance | Prove constraints, migrations, transaction visibility, and competing writes |
| Quality | TypeScript compiler, ESLint, typescript-eslint, and Prettier | Check types, promise handling, code quality, and formatting |
| Package management | npm with a committed lockfile and `npm ci` | Keep installation and CI reproducible with minimal tooling |
| Local infrastructure | Podman or Docker Engine with Compose | Keep development and integration databases separate |

Nest documents Express as its default platform, its validation pipeline, and Prisma integration.
Use those supported integrations before adding custom glue. Validation of incoming DTOs does
not automatically validate outgoing responses; use explicit response mapping and contract tests.
[Nest setup](https://docs.nestjs.com/first-steps),
[validation](https://docs.nestjs.com/techniques/validation),
[Prisma integration](https://docs.nestjs.com/recipes/prisma).

### Documentation parity and ergonomics

Preserve the Python project's documentation experience as an explicit acceptance requirement:

- `/docs`: interactive Swagger UI through the official `@nestjs/swagger` integration.
- `/redoc`: a small served HTML page rendering open-source Redoc CE.
- `/openapi.json`: one generated OpenAPI document consumed by both interfaces.

These are chosen project paths, not Nest defaults. Nest requires installing and configuring
its Swagger integration; ReDoc needs a separate page or static asset integration. Do not maintain
a second handwritten specification or build a custom documentation framework. Both interfaces
must reflect the same routes, request/response schemas, statuses, and headers. Verify document
generation and UI availability as part of TS-04, with a browser check that ReDoc loads the schema.
[Nest Swagger setup](https://docs.nestjs.com/openapi/introduction),
[Redoc CE HTML integration](https://redocly.com/docs/redoc/deployment/html).

Enable Nest's supported Swagger CLI plugin when compatible with the selected build toolchain.
It infers DTO metadata and some constraints from TypeScript and validation decorators, reducing
repeated annotations. Keep explicit metadata for contracts it cannot infer, especially errors,
headers, and complex schemas. Runtime validators remain necessary. Configure tests to use the
same metadata generation strategy as the application build.
[Swagger CLI plugin](https://docs.nestjs.com/openapi/cli-plugin).

Do not promise identical ergonomics. FastAPI/Pydantic integrate validation, serialization, and
documentation more directly. The selected Nest DTO approach needs more decorators and setup;
TypeScript types alone do not validate data, and documented response schemas do not enforce
response validation. Nest provides integrated modules, DI, testing utilities, and lifecycle
conventions, while TypeScript provides rich static tooling. The preference depends on the task.
Use documented integrations to reduce ceremony without hiding these differences behind custom
abstractions. Job relevance is the reason for choosing this stack; automatic FastAPI feature
parity is not assumed.

The application stack should remain open source and runnable locally without a mandatory
commercial platform. Prisma ORM is distinct from Prisma's hosted products. AWS and hosted CI
are optional operational services, not open-source components. Review licensing before adding
later dependencies; do not assume a free hosted tier means open source.

### Why this stack, and what the evidence supports

This is a practical curriculum choice, not a statistically established ranking of US job demand.
US remote backend postings demonstrate demand for TypeScript, cloud delivery, databases,
operational ownership, and communication. Individual listings also mention NestJS, while other
teams use different frameworks or languages. The evidence does not establish Prisma as the
most requested ORM or NestJS as the highest-paying framework.

Examples reviewed on 2026-10-23:

- [Prismatic: Senior Backend Engineer, Platform & Infrastructure](https://job-boards.greenhouse.io/prismatic/jobs/5045321007)
  describes a US-based, fully remote team using TypeScript, AWS, PostgreSQL, infrastructure as
  code, and CI, with responsibility for performance, observability, and production delivery.
- [Pragmatike: Backend Software Engineer, US Remote](https://jobs.ashbyhq.com/pragmatike/d1056838-7ae3-4ebd-9963-f5fe12c1883e)
  describes TypeScript/NestJS services and background processing. Its description says remote,
  but the location-type field says on-site; verify eligibility rather than assuming the label.

These are illustrative snapshots, not guaranteed openings or a representative market survey.
Before tailoring applications, sample recent employer postings in the developer's eligible US
states. Record recurring skills, remote restrictions, work authorization requirements, and
compensation disclosures. Prioritize repeated requirements over framework popularity claims.

Learn Express fundamentals underneath Nest. Gain enough TypeORM literacy to understand an
existing Nest codebase if target postings request it; do not install two ORMs in this project.
Fastify, MikroORM, Drizzle, and Zod remain valid alternatives, but learning all of them is not
an initial objective. Use the selected stack deeply before evaluating replacements.

## Business scope to preserve

Begin with the same deliberately small bookstore catalog. The AI collaborator may propose
coherent teaching requirements and explain their consequences. Implement only the agreed slice.

- A Book is one edition in one format, not an individual copy or every edition of a title.
- One catalog record exists per ISBN. A UUID identifies the record independently of ISBN.
- ISBN is an immutable value object containing exactly 13 ASCII digits with a valid checksum.
  Initially reject formatted ISBNs, ISBN-10, and non-ASCII digits. Do not add prefix or assignment
  verification without a new requirement.
- Trim title and author at the boundaries and in domain behavior. Title length is 1–100
  characters; author length is 1–80. Preserve internal whitespace.
- Validate all proposed detail changes before mutating either field. ID and ISBN are not writable
  through the update API. PATCH omission preserves a field; explicit null and empty patches fail.
- Enforce ISBN uniqueness in the database as well as providing an application-level duplicate
  check. Concurrent creation must not bypass the constraint.
- Track persisted versions from 1. Accepted updates advance the version even when text is unchanged.
- Delete permanently, reject missing records, and allow ISBN reuse with a different UUID.
- Support bounded collection reads, agreed literal text filters, stable ISBN ordering, and opaque
  versioned cursors for forward/backward keyset navigation. Deleted cursor anchors must work.

Make cross-language semantics explicit. JavaScript string length counts UTF-16 code units;
Python string length counts Unicode code points. Choose and test Unicode length and whitespace
rules deliberately. Specify PostgreSQL case/accent matching and wildcard escaping rather than
assuming its defaults reproduce MySQL or an in-memory fake.

Inventory, orders, pricing, lending, payments, and separate author entities remain outside the
initial catalog. Add a new business capability only for an agreed learning need.

## Architecture and idiomatic TypeScript

Keep a modular monolith. Dependencies point inward:

```text
HTTP adapter -> application -> domain
Persistence adapter -> application ports and domain
Composition root -> adapters and application
```

- Domain code uses plain TypeScript classes, value objects, and explicit behavior. Keep it free
  of Nest, ORM, validation-library, and HTTP types.
- Application services coordinate domain rules through small ports. Use plain command/result
  types with `readonly` where appropriate. Keep framework exceptions and generated ORM types out.
- TypeScript interfaces provide structural contracts, similar to Python protocols. They disappear
  at runtime; use explicit registration tokens and factories for DI.
- Keep Nest modules, DTO decorators, guards, filters, and provider registrations in adapters or
  composition code. Plain application services can be constructed with Nest factory providers.
- Keep Prisma records separate from domain objects. Reconstruct existing identities rather than
  generating new UUIDs. Changing a domain object does not automatically persist it.
- Use functions when a class adds no responsibility. Avoid generic repositories, base services,
  custom DI wrappers, event buses, or CQRS infrastructure without a concrete requirement.

Nest's factory providers support this separation without a custom container framework.
[Custom providers](https://docs.nestjs.com/fundamentals/custom-providers).

An initial layout can be small:

```text
src/
  books/
    domain/
    application/
    adapters/http/
    adapters/persistence/
    books.module.ts
  platform/
    persistence/
    configuration/
  app.module.ts
  main.ts
prisma/
  migrations/
tests/
  unit/
  integration/
  e2e/
```

### Transactions: preserve guarantees, adapt the mechanism

The Python project now uses a callback transaction port (decision 0004). Prisma does not reproduce
SQLAlchemy's session, identity map, or dirty checking. Do not manufacture those mechanisms.

Use a small application-owned transaction capability implemented with Prisma's documented
transaction API. An idiomatic callback can provide transaction-bound repositories, commit when
the callback succeeds, and roll back when it throws. The application chooses the atomic work;
the adapter owns connection and transaction mechanics. Preserve this boundary using Prisma rather
than copying SQLAlchemy-specific implementation details.

All repositories participating in one atomic operation must use the same transaction client.
Do not accidentally call a global client inside that operation. Keep transactions short and
external network calls outside them unless a concrete requirement explains otherwise.

Implement atomic ID-plus-version update/delete predicates and check affected results. Preserve
version increments on unchanged updates. Translate only recognized database failures into
application errors. Demonstrate these guarantees against competing PostgreSQL connections.
[Prisma transaction documentation](https://www.prisma.io/docs/orm/v7/prisma-client/queries/transactions).

Verify the installed Prisma major version's APIs before implementation; examples and transaction
types can differ across releases. Never wrap an incompatible example in a custom framework.

## HTTP contract

Preserve resource-focused REST semantics, explicit representations, and generated OpenAPI.
Use GET for reads, POST for creation, PUT for replacing writable details, PATCH for partial
updates, and DELETE for removal. Updates do not upsert missing books.

Retain strong ETags and required `If-Match` for protected writes. Teach tag lists, weak versus
strong matching, wildcard existence checks, and races after reads. Missing preconditions return
428, malformed preconditions 400, and stale writes 412. Keep versions out of JSON representations.
Preserve the source project's transformed-PUT validator policy and empty DELETE responses.

Agree on an error contract before implementation. Nest's default request validation uses 400;
the Python API uses FastAPI's 422. Prefer documented Nest behavior for a new standalone API
unless compatibility is explicitly required. Document any other intentional differences.
Map invalid ISBN checksums to a deliberate client error; do not copy the Python project's known
unmapped-error limitation. Never turn unknown defects into successful responses or client errors.

## Curriculum and delivery order

Each milestone is proposed work. Complete one agreed component at a time; these rows do not
authorize implementing the entire curriculum.

| Milestone | Deliverable and learning focus | Acceptance evidence |
|---|---|---|
| TS-01 | Minimal tooling and a short JavaScript/TypeScript foundation through catalog examples | Explain runtime versus types, modules, narrowing, promises, and strict compiler behavior |
| TS-02 | Book, ISBN, create use case, ports, and fakes | Independent domain rules and duplicate behavior; no framework imports in the core |
| TS-03 | PostgreSQL persistence, mappings, migrations, and transactions | Real uniqueness, identity reconstruction, commit visibility, and rollback |
| TS-04 | Nest composition, health, POST, GET, DTOs, and OpenAPI | Supported provider wiring, HTTP behavior, and resource cleanup |
| TS-05 | PUT/PATCH/DELETE with ETags and `If-Match` | HTTP contracts plus real competing-write and rollback proofs |
| TS-06 | Filtering and bidirectional keyset pagination | Stable ordering, bounded reads, deleted anchors, collection changes, and database/fake agreement |
| TS-07 | Consistent expected errors and complete vertical-slice review | Accurate contracts, meaningful error translation, and current verification evidence |
| TS-08 | Authentication and authorization | Agreed reader/editor policy, trusted token validation, and permitted/denied behavior |
| TS-09 | Rate limiting | Explicit limit scope, actual enforcement, and accurate `Retry-After` behavior |
| TS-10 | One reliable background-work requirement | Durable intent, retry behavior, duplicate handling, and recovery after failure |
| TS-11 | Idempotency for an agreed operation | Concurrent ownership, request replay, conflict rules, and crash recovery |
| TS-12 | Observability, deployment, and infrastructure definitions | Repeatable deploy, operational signals, migration safety, and documented teardown |

Async programming is cross-cutting from TS-01 onward. Unlike the synchronous Python baseline,
Node database I/O normally uses promises. Teach `async`/`await`, rejection handling, cancellation,
timeouts, bounded concurrency, event-loop blocking, and cleanup through actual I/O needs.
Avoid unbounded `Promise.all`, floating promises, and unexplained type assertions or `any`.
Explain that TypeScript `readonly` and branded types do not provide runtime validation or deep freezing.

## Later operational choices

Select these when their milestone needs them; do not provision them during initial scaffolding.

- Authentication: use established OIDC/OAuth libraries and a trusted identity provider. A local
  open-source provider such as Keycloak is an option. Agree on issuer, audience, expiry, key
  rotation, permissions, and test strategy. Do not build a custom identity platform.
- Background work: start with one concrete requirement, such as durable catalog-export jobs.
  Choose AWS SQS for the AWS path, or BullMQ with a compatible open-source Redis implementation
  for a local queue path. Pick one initially. If persistence and publishing must be atomic,
  evaluate a transactional outbox. Document at-least-once delivery and idempotent consumers.
- Observability: structured logs with request correlation; OpenTelemetry tracing/metrics when
  useful. Demonstrate one investigation from an HTTP request to its database or worker activity.
  [OpenTelemetry JavaScript](https://opentelemetry.io/docs/languages/js/).
- Deployment: propose one AWS path, such as ECS/Fargate plus RDS PostgreSQL. Include image
  publishing, IAM, secrets, TLS, graceful shutdown, readiness, migrations, and teardown. Explain
  recurring costs and obtain authorization before creating resources. Keep a local workflow.
- Infrastructure as code: prefer OpenTofu for the open-source requirement; explain the transferable
  HCL, state, planning, and provider concepts encountered in Terraform-based jobs. Verify provider
  compatibility. [OpenTofu](https://opentofu.org/docs/intro/).
- CI: GitHub Actions is a practical hosted option, distinct from the open-source application.
  Keep build and verification commands runnable locally. Prove a clean install and migrations
  against an empty integration database before merging a deployable change.

React/Next.js, Kubernetes, Kafka, microservices, event sourcing, vector databases, and AI features
are optional later studies. None is required to demonstrate this backend's professional quality.

## Verification standard

Use domain/application tests for business behavior, HTTP tests for contracts, and real PostgreSQL
tests for database guarantees. Fakes do not prove locking, SQL predicates, rollback, collation,
or schema migration behavior. Use independent connections and inspect persisted outcomes for races.

Migrations own the integration schema. Do not substitute ORM schema synchronization or an
ad hoc test schema. Review generated SQL. Prove clean installation and relevant data-preserving
upgrades. Prisma migrations do not supply Alembic-style automatic downgrade functions; agree on
forward fixes, backups, and restore procedures appropriate to each change.

Document which HTTP tests use fake persistence and which execute the full stack. Include a
small real-database HTTP smoke path before declaring the application deployable. Default local
tests should work without database credentials; a clearly named integration command should fail
if its required database is unavailable rather than silently claiming success.

Run applicable type, lint, formatting, build, and test checks. Record commands actually executed,
results, environment, and omissions. Test presence and task status never imply a fresh passing run.
Do not set an arbitrary coverage percentage in place of behavioral evidence.

## Teaching and collaboration contract

1. Inspect current evidence before planning a lesson. State the exact component, minimum files,
   and intended acceptance conditions. Wait for explicit authorization before implementation.
2. Coach the developer to write the implementation. Review their work first. When asked to
   implement, write application code before tests; keep those changes separate and prompt the
   developer to write tests before creating or modifying tests yourself.
3. Explain what comes from JavaScript, TypeScript, Node, Nest, Prisma, and PostgreSQL. Compare
   with Laravel/Python where useful, while using each library's documented conventions.
4. Keep requirements coherent and complexity earned. Distinguish implemented behavior, required
   rules, and proposals. Do not advance to another lesson without authorization.
5. Preserve staged Git scope. Review the complete relevant diff and report verification limits.
   Use scoped Conventional Commits when commits are requested.
6. Keep human learning notes out of routine agent discovery and indexing. In the source project,
   `learnings/`, `docs/ai/`, and `QA.md` require explicit task-specific permission to access.

## Final portfolio acceptance

The finished project should provide evidence of backend ownership:

- A documented, runnable API with protected invariants, clear contracts, and deliberate failures.
- Real database evidence for constraints, migrations, transactions, pagination, and concurrency.
- An authenticated, authorized vertical slice and one justified reliability/background-work slice.
- Reproducible CI and a deployed demonstration, with configuration, migration, and recovery notes.
- Useful logs and a concrete operational investigation or failure-recovery exercise.
- A concise architecture explanation, significant decision records, and measured query/load findings
  with reproducible methodology rather than unsupported scale claims.
- Clear written handoffs and PR descriptions demonstrating asynchronous collaboration for remote work.

The developer must be able to explain the trade-offs and modify the system without relying on
generated scaffolding. Present portfolio work honestly; it demonstrates skills but does not count
as years of commercial TypeScript experience.

## First action for the receiving collaborator

Read this document, confirm the developer's JavaScript/TypeScript experience, and inspect any
existing target repository. Verify supported package versions and propose TS-01 with exact files
and a small acceptance checklist. Ask for authorization before scaffolding. Do not restart or
modify the Python curriculum as part of this handoff.
