from logging import getLogger
from pathlib import Path
from sys import stderr
from typing import Annotated, Any, Generic, TypeVar

from fastapi import Depends, FastAPI
from PPpackage_repository_driver.interface import load_interface_module
from PPpackage_repository_driver.schemes import RepositoryConfig
from PPpackage_utils.http_stream import AsyncChunkReader
from PPpackage_utils.stream import dump_many
from PPpackage_utils.validation import load_from_bytes
from pydantic import ValidationError
from pydantic_settings import BaseSettings
from starlette.status import HTTP_200_OK

from .utils import StreamingResponse, get_reader

RequirementType = TypeVar("RequirementType")

SettingsType = TypeVar("SettingsType", bound=BaseSettings)
StateType = TypeVar("StateType")


class PackageSettings(BaseSettings):
    config_path: Path


package_settings = PackageSettings()  # type: ignore


def parse_config(config_path: Path) -> RepositoryConfig:
    with config_path.open("rb") as f:
        config_json_bytes = f.read()

        try:
            config = load_from_bytes(RepositoryConfig, memoryview(config_json_bytes))
        except ValidationError as e:
            stderr.write("ERROR: Invalid config.\n")
            stderr.write(e.json(indent=4))

            raise

        return config


config = parse_config(package_settings.config_path)


interface = load_interface_module(config.driver.package)


logger = getLogger(__name__)


async def translate_options(reader: Annotated[AsyncChunkReader, Depends(get_reader)]):
    logger.info("Updating database...")

    options = await reader.load_one(Any)  # type: ignore

    translated_options = await interface.translate_options(
        config.driver.parameters, config.parameters, options
    )

    logger.info("Database updated.")

    return translated_options


async def fetch_packages(reader: Annotated[AsyncChunkReader, Depends(get_reader)]):
    logger.info("Resolving...")

    translated_options = await reader.load_one(Any)  # type: ignore

    # TODO: figure out why we need to iterate the async iterable
    outputs = interface.fetch_packages(
        config.driver.parameters, config.parameters, translated_options
    )

    logger.info("Resolved.")

    return StreamingResponse(HTTP_200_OK, dump_many(outputs))


class SubmanagerServer(FastAPI, Generic[SettingsType, StateType, RequirementType]):
    def __init__(self):
        super().__init__(debug=True, redoc_url=None)

        super().post("/translate-options")(translate_options)
        super().post("/fetch-packages")(fetch_packages)


server = SubmanagerServer()
