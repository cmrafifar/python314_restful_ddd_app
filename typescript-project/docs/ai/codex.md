# Codex how-tos

Practical Codex setup notes for this TypeScript repository. Keep agent instructions in
[AGENTS.md](../../AGENTS.md); this document is a reference for developers, not agent instructions.
It mirrors the Python reference's `docs/ai/codex.md`, using this project's actual pnpm scripts.

## Allow routine checks without repeated approval

Codex approval rules control which commands can run outside the sandbox. An instruction in chat
or `AGENTS.md` does not override sandbox restrictions. For example, pnpm may need access to its
store or network access to download dependencies. Approval does not install dependencies or
change the project's pinned Node.js and pnpm versions.

Add these entries to `~/.codex/rules/default.rules`, preserving existing rules:

```python
prefix_rule(pattern=["pnpm", "typecheck"], decision="allow")
prefix_rule(pattern=["pnpm", "lint"], decision="allow")
prefix_rule(pattern=["pnpm", "format:check"], decision="allow")
```

Restart Codex after editing the file. Alternatively, save the matching command prefix when
approving a command in the approval dialog.

These are user-wide rules, not repository settings. They allow commands with these exact argument
prefixes, including trailing arguments, to run outside the sandbox without prompting. Only allow
tools and repositories you trust: pnpm scripts execute commands from the current project's
`package.json`, and tools can load executable configuration. More restrictive managed rules can
still require approval or block execution.

The prefixes do not match alternate spellings or wrappers. For example, `pnpm run typecheck`,
`pnpm --dir typescript-project typecheck`, and `rtk pnpm typecheck` differ from `pnpm typecheck`.
Run project commands from this directory rather than approving a broad `pnpm` prefix. Dependency
installation and schema-changing commands need separate consideration; these examples do not
approve them.

### Verify the rules

```bash
codex execpolicy check --pretty \
  --rules ~/.codex/rules/default.rules \
  -- pnpm typecheck

codex execpolicy check --pretty \
  --rules ~/.codex/rules/default.rules \
  -- pnpm lint

codex execpolicy check --pretty \
  --rules ~/.codex/rules/default.rules \
  -- pnpm format:check
```

Each check should report an `allow` decision for this file. It does not execute the target command
or prove that no other policy restricts the current session.

### Remove an approval

Delete the corresponding `prefix_rule` entry and restart Codex. Preserve unrelated entries.

Reference: [official Codex rules documentation](https://developers.openai.com/codex/rules/).

## Run this project's checks

From the project root, after installing the pinned dependencies:

```bash
pnpm db:generate
pnpm typecheck
pnpm lint
pnpm format:check
pnpm build
```

Prisma generates its TypeScript client before type checking. Generation writes ignored generated
files; it does not apply database migrations. The build also generates the client before compiling
the NestJS application. Formatting checks report differences without rewriting files; `pnpm format`
rewrites them.

Unlike the Python project's pytest workflow, this project currently has no test script, test
dependencies, or test suite. Static checks and builds do not establish behavioral test coverage.
Tests are deferred until explicitly requested, so there is no `pnpm test` approval to add yet.

See [local development](../../README.md#local-development) for installation, environment setup,
database commands, and the planned testing tools. `pnpm db:deploy` applies committed migrations;
`pnpm db:migrate --name <name>` creates and applies development migrations. Both change the
configured database and are separate from the routine check approvals above.
