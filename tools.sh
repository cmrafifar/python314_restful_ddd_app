#!/bin/env bash

set -o pipefail


function mylib_error() {
  local msg="$1"
  printf "\033[1;31m[ERROR]\033[0m ${msg}.\n"
}

function mylib_success() {
  local msg="$1"
  printf "\033[32m[SUCCESS]\033[0m ${msg}.\n"
}


function goto_path() {
  local path="${1:-}"
  cd "$HOME/github-repos/cmrafifar/python314_restful_ddd_app/$path" || (mylib_error "failed to navigate to path" && return 1)
  mylib_success "$(pwd)"
}


function docker_validate_compose() {
  podman compose config
}


function docker_up_build() {
  podman compose up --build  -d 
}


function docker_test_mysql_connection() {
	podman compose exec api uv run --no-dev python -c '
	from sqlalchemy import create_engine, text

	engine = create_engine(
	    "mysql+pymysql://bookstore:development_password@mysql:3306/bookstore"
	)

	with engine.connect() as connection:
	    print(connection.scalar(text("SELECT VERSION()")))

	engine.dispose()
	'
}


function docker_migrations_generate() {
  local migration_message="$1"
  if [ -z "$migration_message" ]; then
    echo "argument 1 required: migration message" >&2
    return 1;
  fi

  export APP_DB_HOST=127.0.0.1 \
  && export APP_DB_PORT=3307 \
  && export APP_DB_NAME=bookstore \
  && export APP_DB_USER=bookstore \
  && export APP_DB_PASSWORD=development_password \
  && uv run alembic revision --autogenerate -m "${migration_message}"
}


function docker_migrations_apply() {
  uv run --locked alembic upgrade head
  
  uv run --locked alembic current

  uv run --locked alembic history --verbose
}


function docker_migrations_show_versions() {
  podman compose exec mysql \
  mysql -u bookstore -pdevelopment_password bookstore \
  -e "SELECT * FROM alembic_version;"
}


function docker_mysql_test_start() {
  podman compose --env-file .env.test \
  -p bookstore-integration \
  -f compose.test.yaml \
  up -d mysql-test
}



