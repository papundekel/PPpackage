from logging import getLogger
from pathlib import Path
from sys import stderr
from typing import Any, TypeVar

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from PPpackage.repository_driver.interface.interface import Interface
from PPpackage.repository_driver.interface.schemes import RepositoryConfig
from pydantic import ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict
from starlette.status import HTTP_200_OK, HTTP_304_NOT_MODIFIED

from PPpackage.utils.stream import dump_many
from PPpackage.utils.utils import load_interface_module
from PPpackage.utils.validation import load_from_bytes, load_object

from .utils import StreamingResponse

RequirementType = TypeVar("RequirementType")

SettingsType = TypeVar("SettingsType", bound=BaseSettings)
StateType = TypeVar("StateType")


class PackageSettings(BaseSettings):
    config_path: Path

    model_config = SettingsConfigDict(case_sensitive=False)


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


async def enable_cache(request: Request, response: Response):
    epoch = await interface.get_epoch(driver_parameters, repository_parameters)

    request_epoch = request.headers.get("If-None-Match")

    if request_epoch == epoch:
        raise HTTPException(HTTP_304_NOT_MODIFIED)
    else:
        response.headers["Cache-Control"] = "public, no-cache, max-age=2147483648"
        response.headers["ETag"] = epoch


async def fetch_packages(response: Response):
    logger.info("Fetching packages...")

    outputs = interface.fetch_packages(driver_parameters, repository_parameters)

    logger.info("Fetched packages.")

    return StreamingResponse(HTTP_200_OK, response.headers, dump_many(outputs))


async def translate_options(options: Any):
    logger.info("Translating options...")

    translated_options = await interface.translate_options(
        driver_parameters, repository_parameters, options
    )

    logger.info("Options translated.")

    return translated_options


async def fetch_formula(response: Response, translated_options: Any):
    logger.info("Fetching formula...")

    outputs = interface.fetch_formula(
        driver_parameters, repository_parameters, translated_options
    )

    logger.info("Fetched formula.")

    return StreamingResponse(HTTP_200_OK, response.headers, dump_many(outputs))


class SubmanagerServer(FastAPI):
    def __init__(self):
        super().__init__(redoc_url=None)

        super().get("/fetch-packages", dependencies=[Depends(enable_cache)])(
            fetch_packages
        )
        super().get("/translate-options", dependencies=[Depends(enable_cache)])(
            translate_options
        )
        super().get("/fetch-formula", dependencies=[Depends(enable_cache)])(
            fetch_formula
        )


server = SubmanagerServer()
