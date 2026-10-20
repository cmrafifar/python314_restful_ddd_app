# Codex how-tos

Practical Codex setup notes for this repository. Keep agent instructions in [AGENTS.md](../../AGENTS.md); this document is a reference for developers.

## Allow routine checks without repeated approval

Codex approval rules control which commands can run outside the sandbox. An instruction in chat or `AGENTS.md` does not override sandbox restrictions. For example, `uv` may need to write to its cache outside the repository.

Add these entries to `~/.codex/rules/default.rules`, preserving existing rules:

```python
prefix_rule(pattern=["uv", "run", "pytest"], decision="allow")
prefix_rule(pattern=["uv", "run", "basedpyright"], decision="allow")
```

Restart Codex after editing the file. Alternatively, save the matching command prefix when approving a command in the approval dialog.

These are user-wide rules, not repository settings. They allow commands with these exact argument prefixes, including trailing arguments, to run outside the sandbox without prompting. Only allow tools and repositories you trust: pytest executes project code. More restrictive managed rules can still require approval or block execution.

The prefixes do not match commands with intervening arguments, such as `uv run --env-file .env.test pytest`. A wrapper also needs its own prefix; for example, `uv run rtk pytest` differs from `uv run pytest`.

### Verify the rules

```bash
codex execpolicy check --pretty \
  --rules ~/.codex/rules/default.rules \
  -- uv run pytest

codex execpolicy check --pretty \
  --rules ~/.codex/rules/default.rules \
  -- uv run basedpyright
```

Each check should report an `allow` decision for this file. It does not execute the target command or prove that no other policy restricts the current session.

### Remove an approval

Delete the corresponding `prefix_rule` entry and restart Codex. Preserve unrelated entries.

Reference: [official Codex rules documentation](https://developers.openai.com/codex/rules/).

## Run this project's tests

```bash
uv run pytest
```

The default run needs no database credentials and skips MySQL tests. For database setup, ignored local credentials, and the explicit integration command, follow [Testing](../testing.md#mysql-integration-setup).
