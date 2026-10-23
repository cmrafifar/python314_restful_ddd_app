import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy.engine import make_url


@pytest.mark.parametrize("failed_step", [None, "up", "python", "upgrade", "check"])
def test_bash_runner_uses_test_database_and_stops_on_failure(
    tmp_path: Path, failed_step: str | None
) -> None:
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    runner = scripts / "test_integration.sh"
    shutil.copyfile(Path(__file__).resolve().parents[2] / "scripts/test_integration.sh", runner)
    (tmp_path / ".env.test").write_text(
        "APP_DB_HOST=production.example.com\nAPP_DB_PORT=3307\n"
        "APP_DB_NAME=bookstore\nAPP_DB_USER=root\n"
        "APP_DB_PASSWORD='test-password-with-@:/#%$'\nTEST_MYSQL_ROOT_PASSWORD=test-root\n"
    )
    commands = tmp_path / "commands.jsonl"
    stub = tmp_path / "command"
    stub.write_text(
        f"#!{sys.executable}\n"
        "import json, os, subprocess, sys\n"
        "from pathlib import Path\n"
        "arguments = sys.argv[1:]\n"
        "with open(os.environ['COMMAND_LOG'], 'a') as log:\n"
        "    selected = {key: value for key, value in os.environ.items() "
        "if key.startswith('APP_DB_') or key in ('BOOKSTORE_TEST_DATABASE_URL', 'PYTEST_ADDOPTS')}\n"
        "    log.write(json.dumps({'arguments': arguments, 'environment': selected}) + '\\n')\n"
        "if os.environ['FAILED_STEP'] in arguments:\n"
        "    sys.exit(7)\n"
        "if Path(sys.argv[0]).name == 'uv' and 'python' in arguments:\n"
        "    sys.exit(subprocess.call([sys.executable, '-'], env=os.environ))\n"
    )
    stub.chmod(0o755)
    (tmp_path / "podman").symlink_to(stub)
    (tmp_path / "uv").symlink_to(stub)
    environment = dict(os.environ)
    environment.update(
        PATH=f"{tmp_path}:{os.environ['PATH']}",
        COMMAND_LOG=str(commands),
        FAILED_STEP=failed_step or "none",
        PYTEST_ADDOPTS="--collect-only",
        BOOKSTORE_TEST_DATABASE_URL="mysql+pymysql://wrong-target/bookstore",
    )

    result = subprocess.run(["bash", str(runner)], env=environment, check=False)

    assert result.returncode == (7 if failed_step else 0)
    calls = [json.loads(line) for line in commands.read_text().splitlines()]
    if failed_step:
        assert failed_step in calls[-1]["arguments"]
        assert not any("pytest" in call["arguments"] for call in calls)
    else:
        last = calls[-1]
        assert last["arguments"] == [
            "run",
            "--locked",
            "pytest",
            "tests/integration",
            "--run-integration",
        ]
        target = make_url(last["environment"]["BOOKSTORE_TEST_DATABASE_URL"])
        assert (target.host, target.port, target.database, target.username) == (
            "127.0.0.1",
            3308,
            "bookstore_test",
            "bookstore_test",
        )
        assert target.password == "test-password-with-@:/#%$"
        assert "PYTEST_ADDOPTS" not in last["environment"]
