from collections.abc import AsyncIterable, Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, AsyncContextManager, Generic, TypeVar

from PPpackage_utils.server import UserBase
from pydantic_settings import BaseSettings

from .schemes import Dependency, Package, PackageIDAndInfo, Product, ResolutionGraph

RequirementType = TypeVar("RequirementType")
SettingsType = TypeVar("SettingsType", bound=BaseSettings)
StateType = TypeVar("StateType")
UserType = TypeVar("UserType", bound=UserBase)

UpdateDatabaseCallbackType = Callable[[SettingsType, StateType], Awaitable[None]]
ResolveCallbackType = Callable[
    [SettingsType, StateType, Any, AsyncIterable[AsyncIterable[RequirementType]]],
    AsyncIterable[ResolutionGraph],
]
FetchCallbackType = Callable[
    [
        SettingsType,
        StateType,
        Any,
        Package,
        AsyncIterable[Dependency],
        Path | None,
        Path | None,
    ],
    Awaitable[PackageIDAndInfo | AsyncIterable[str]],
]

GenerateCallbackType = Callable[
    [SettingsType, StateType, Any, AsyncIterable[Product], AsyncIterable[str], Path],
    Awaitable[None],
]
InstallCallbackType = Callable[
    [SettingsType, StateType, Path, Product], Awaitable[None]
]


async def update_database_noop(settings: Any, state: Any) -> None:
    pass


async def generate_noop(
    settings: Any,
    state: Any,
    options: Any,
    products: AsyncIterable[Product],
    generators: AsyncIterable[str],
    destination_path: Path,
) -> None:
    async for _ in products:
        pass

    async for _ in generators:
        pass


@dataclass(frozen=True, kw_only=True)
class Interface(Generic[SettingsType, StateType, RequirementType]):
    Settings: type[SettingsType]
    lifespan: Callable[[SettingsType], AsyncContextManager[StateType]]
    update_database: UpdateDatabaseCallbackType[
        SettingsType, StateType
    ] = update_database_noop
    resolve: ResolveCallbackType[SettingsType, StateType, RequirementType]
    fetch: FetchCallbackType[SettingsType, StateType]
    generate: GenerateCallbackType[SettingsType, StateType] = generate_noop
    install: InstallCallbackType[SettingsType, StateType]
