#!/bin/bash

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
