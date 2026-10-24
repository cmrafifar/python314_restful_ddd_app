# Bookstore API — TypeScript

A standalone NestJS bookstore catalog, temporarily located beside its Python reference project.
Run every command below from this directory. There is no nested Git repository or submodule.

The catalog implements creation, individual reads, PUT/PATCH, hard deletion, strong ETags and
`If-Match`, literal title/author filtering, and bidirectional keyset pagination. It keeps the
domain and application independent of Nest and Prisma. Automated tests are intentionally deferred
until explicitly requested; working code and manual verification do not replace regression tests.

## Stack

| Concern           | Choice                                                                           |
| ----------------- | -------------------------------------------------------------------------------- |
| Runtime           | Node.js 26.12.1, the stable Current release verified at initialization           |
| Package manager   | pnpm 12.15.0 and a committed lockfile                                            |
| HTTP and DI       | NestJS 12 with Express and built-in factory providers                            |
| Persistence       | Prisma ORM 7 with PostgreSQL 18 and the official pg adapter                      |
| Validation        | ValidationPipe, class-validator, class-transformer, explicit response validation |
| Static analysis   | TypeScript 6 strict checks and type-aware typescript-eslint                      |
| Lint and format   | ESLint and Prettier                                                              |
| API documentation | Generated OpenAPI, Swagger UI, and ReDoc CE                                      |

Node Current is a deliberate override of the handoff's LTS preference. TypeScript 6.0.3 is the
newest compatible stable compiler: the selected Swagger and typescript-eslint packages do not
support TypeScript 7 in their declared peer ranges. Prisma is pinned to stable 7.10.1 rather than
the prerelease currently advertised by its `latest` registry tag. Do not update packages blindly.
Review runtime support and compatibility when updating pinned versions.

## Container quick start

Install Docker Engine with Compose or Podman with a compatible Compose provider. From this directory:

```bash
cp .env.example .env
docker compose up --build -d
docker compose logs -f api
```

Use `podman compose` in place of `docker compose` if preferred. Compose uses its own project
name, network, PostgreSQL volume, and ports, separate from Python's MySQL infrastructure.
PostgreSQL binds to `127.0.0.1:5433`; the API binds to `127.0.0.1:3000`.

The migration service waits for PostgreSQL, runs committed migrations, and must succeed before
the API starts. It changes only this stack's database. The Dockerfile has separate tooling and
runtime targets; the API runs as the unprivileged `node` user with production dependencies.
The official Node image uses npm only to bootstrap the pinned pnpm executable. Project dependency
installation, migration, build, and development commands all use pnpm.

The example credentials are for local development. Change them before deployment. If credentials
contain URL-reserved characters, percent-encode them in `DATABASE_URL`; the convenience Compose
URL interpolation assumes URL-safe local credentials. PostgreSQL initialization settings apply
only to a fresh volume; editing `.env` does not rotate an existing user's password.

```bash
docker compose down
```

Stopping preserves the named database volume. Removing that volume is a separate destructive action.

## Local development

Install the version in `.node-version`/`.nvmrc` and pnpm 12.15.0, then:

```bash
cp .env.example .env
pnpm install --frozen-lockfile
docker compose up -d postgres
pnpm db:generate
pnpm db:deploy
pnpm start:dev
```

`db:deploy` applies committed schema changes to the configured database. `db:migrate --name <name>`
creates and applies a new development migration; review its SQL. Do not use `db push` as a replacement
for migrations. Prisma has no automatic Alembic-style downgrade; plan forward fixes and backups.

Generated Prisma code is ignored and regenerated during builds. `pnpm db:generate` is needed after
a fresh install before type checking. Generation and builds do not require a running database;
starting the app requires a valid `DATABASE_URL`, while the first catalog operation connects lazily.
The process health route does not query PostgreSQL.

```bash
pnpm db:validate
pnpm typecheck
pnpm lint
pnpm format:check
pnpm build
pnpm start
```

Run `pnpm format` to format owned source/configuration. No test command or test dependencies are
installed yet. When requested, use Jest, `@nestjs/testing`, Supertest, and a dedicated PostgreSQL
test database rather than reusing development data.

## Explore the API

- [Swagger UI](http://localhost:3000/docs)
- [ReDoc](http://localhost:3000/redoc)
- [OpenAPI JSON](http://localhost:3000/openapi.json)
- [Process health](http://localhost:3000/health)

Both documentation interfaces consume the same generated specification. Swagger assets are served
by the application; ReDoc CE uses a version-pinned public CDN and needs browser internet access.
OpenAPI metadata describes response contracts; `validatedResponse` separately enforces successful
JSON response DTOs at runtime. Invalid outgoing representations produce 500, not a client error.

```bash
curl -i http://localhost:3000/api/v1/books \
  -H 'Content-Type: application/json' \
  -d '{"isbn":"9780132350884","title":"Clean Code","author":"Robert C. Martin"}'
curl -i http://localhost:3000/api/v1/books
```

Retrieve the created UUID at `/api/v1/books/<id>` and copy its complete quoted ETag into `If-Match`
when using PUT, PATCH, or DELETE. GET and PATCH return strong ETags. Transformed PUT, collections,
creation, and empty DELETE responses do not. Express's automatic weak ETag generation is disabled.

See [architecture and contract decisions](docs/architecture.md) for boundaries and deliberate
differences from Python. Route decorators and DTOs own detailed endpoint contracts.

See [API conventions](docs/api-conventions.md) for HTTP behavior and
[technology decisions](docs/decisions.md) for stack choices, tradeoffs, and upgrade policy.

For developer-specific Codex approval rules and check commands, see
[Codex how-tos](docs/ai/codex.md). This is human reference material, separate from agent instructions.
