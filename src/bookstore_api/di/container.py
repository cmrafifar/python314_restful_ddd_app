from dishka import Container, Provider, Scope, make_container

from bookstore_api.config import Settings
from bookstore_api.di.providers.books import BooksProvider
from bookstore_api.di.providers.persistence import PersistenceProvider


def create_container(settings: Settings, *provider_overrides: Provider) -> Container:
    configuration = Provider(scope=Scope.APP)
    configuration.from_context(Settings)

    return make_container(
        configuration,
        PersistenceProvider(),
        BooksProvider(),
        *provider_overrides,
        context={Settings: settings},
    )
