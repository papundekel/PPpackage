from logging import getLogger
from pathlib import Path
from sys import stderr
from typing import Annotated, Any, Generic, TypeVar

from fastapi import Depends, FastAPI
from PPpackage.repository_driver.interface.interface import Interface
from PPpackage.repository_driver.interface.schemes import RepositoryConfig
from pydantic import ValidationError
from pydantic_settings import BaseSettings
from starlette.status import HTTP_200_OK

from PPpackage.utils.stream import dump_many
from PPpackage.utils.utils import load_interface_module
from PPpackage.utils.validation import load_from_bytes, load_object

from .utils import StreamingResponse

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


interface = load_interface_module(Interface, config.driver.package)

driver_parameters = load_object(interface.DriverParameters, config.driver.parameters)
repository_parameters = load_object(interface.RepositoryParameters, config.parameters)


logger = getLogger(__name__)


async def fetch_packages():
    logger.info("Fetching packages...")

    # TODO: figure out why we need to iterate the async iterable
    outputs = interface.fetch_packages(driver_parameters, repository_parameters)

    logger.info("Fetched packages.")

    return StreamingResponse(HTTP_200_OK, dump_many(outputs))


async def translate_options(options: Any):
    logger.info("Updating database...")

    translated_options = await interface.translate_options(
        driver_parameters, repository_parameters, options
    )

    logger.info("Database updated.")

    return translated_options


async def fetch_formula(translated_options: Any):
    logger.info("Fetching formula...")

    # TODO: figure out why we need to iterate the async iterable
    outputs = interface.fetch_formula(
        driver_parameters, repository_parameters, translated_options
    )

    logger.info("Fetched formula.")

    return StreamingResponse(HTTP_200_OK, dump_many(outputs))


class SubmanagerServer(FastAPI, Generic[SettingsType, StateType, RequirementType]):
    def __init__(self):
        super().__init__(debug=True, redoc_url=None)

        super().get("/fetch-packages")(fetch_packages)
        super().get("/translate-options")(translate_options)
        super().get("/fetch-formula")(fetch_formula)


server = SubmanagerServer()
