from collections.abc import Callable, Iterator
from functools import partial

from dishka import Provider, Scope, provide
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from bookstore_api.application.unit_of_work import UnitOfWork
from bookstore_api.config import Settings
from bookstore_api.infrastructure.persistence.database import (
    create_db_engine,
    create_session_factory,
)
from bookstore_api.infrastructure.persistence.sqlalchemy_unit_of_work import SqlAlchemyUnitOfWork


class PersistenceProvider(Provider):
    scope = Scope.APP

    @provide
    def engine(self, settings: Settings) -> Iterator[Engine]:
        engine = create_db_engine(settings)
        try:
            yield engine
        finally:
            engine.dispose()

    @provide
    def session_factory(self, engine: Engine) -> sessionmaker[Session]:
        # Use the Engine already constructed from your Settings.
        return create_session_factory(engine)

    @provide
    def unit_of_work_factory(
        self, session_factory: sessionmaker[Session]
    ) -> Callable[[], UnitOfWork]:
        return partial(SqlAlchemyUnitOfWork, session_factory)
