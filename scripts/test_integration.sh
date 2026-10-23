#!/usr/bin/env bash
# Start isolated MySQL, migrate, check schema drift, and run integration tests.
set -euo pipefail
cd "$(dirname "$0")/.."

set -a
source .env.test
set +a
export APP_DB_HOST=127.0.0.1 APP_DB_PORT=3308
export APP_DB_NAME=bookstore_test APP_DB_USER=bookstore_test
# Parent pytest flags must not change this runner's selected suite or integration opt-in.
unset PYTEST_ADDOPTS

compose=(podman compose --env-file .env.test -p bookstore-integration -f compose.test.yaml)
"${compose[@]}" up -d mysql-test
deadline=$((SECONDS + 90))
until "${compose[@]}" exec -T mysql-test sh -c \
  'MYSQL_PWD="$MYSQL_PASSWORD" mysql -h 127.0.0.1 -u "$MYSQL_USER" -D "$MYSQL_DATABASE" -e "SELECT 1"' \
  >/dev/null 2>&1; do
  if ((SECONDS >= deadline)); then
    echo "Test MySQL did not become ready within 90 seconds. Check its logs and credentials." >&2
    exit 1
  fi
  sleep 1
done

BOOKSTORE_TEST_DATABASE_URL=$(uv run --locked python - <<'PY'
from bookstore_api.config import get_settings
from bookstore_api.infrastructure.persistence.database import create_db_engine

print(create_db_engine(get_settings()).url.render_as_string(hide_password=False))
PY
)
export BOOKSTORE_TEST_DATABASE_URL

uv run --locked alembic upgrade head
uv run --locked alembic check
uv run --locked pytest tests/integration --run-integration
