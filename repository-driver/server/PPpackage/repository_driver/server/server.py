from logging import getLogger
from pathlib import Path
from sys import stderr
from typing import Annotated, Any, TypeVar

from asyncstdlib import chain as async_chain
from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
from pydantic import ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict
from starlette.status import HTTP_200_OK, HTTP_304_NOT_MODIFIED

from PPpackage.repository_driver.interface.interface import Interface
from PPpackage.repository_driver.interface.schemes import (
    ArchiveProductDetail,
    DependencyProductInfos,
    RepositoryConfig,
)
from PPpackage.utils.stream import dump_bytes_chunked, dump_many, dump_one
from PPpackage.utils.utils import load_interface_module
from PPpackage.utils.validation import load_from_bytes, load_from_string, load_object

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


async def enable_epoch_cache(request: Request, response: Response):
    epoch = await interface.get_epoch(driver_parameters, repository_parameters)

    request_epoch = request.headers.get("If-None-Match")

    if request_epoch == epoch:
        raise HTTPException(HTTP_304_NOT_MODIFIED)
    else:
        response.headers["Cache-Control"] = "public, no-cache, max-age=2147483648"
        response.headers["ETag"] = epoch


async def enable_permanent_cache(response: Response):
    response.headers["Cache-Control"] = "public, max-age=2147483648"


ModelType = TypeVar("ModelType")


def load_model_from_query(model: type[ModelType], alias: str):
    def dependency(parameter: Annotated[str, Query(alias=alias)]) -> ModelType:
        return load_from_string(model, parameter)

    return dependency


async def fetch_translator_data(response: Response):
    logger.info("Preparing translator data...")

    translator_data = interface.fetch_translator_data(
        driver_parameters, repository_parameters
    )

    logger.info("Translator data ready.")

    return StreamingResponse(HTTP_200_OK, response.headers, dump_many(translator_data))


async def translate_options(
    options: Annotated[Any, Depends(load_model_from_query(Any, "options"))]  # type: ignore
):
    logger.info("Translating options...")

    translated_options = await interface.translate_options(
        driver_parameters, repository_parameters, options
    )

    logger.info("Options translated.")

    return translated_options


async def get_formula(
    response: Response,
    translated_options: Annotated[
        Any, Depends(load_model_from_query(Any, "translated_options"))  # type: ignore
    ],
):
    logger.info("Preparing formula...")

    formula = interface.get_formula(
        driver_parameters, repository_parameters, translated_options
    )

    logger.info("Formula ready.")

    return StreamingResponse(HTTP_200_OK, response.headers, dump_many(formula))


async def get_package_detail(
    response: Response,
    translated_options: Annotated[
        Any, Depends(load_model_from_query(Any, "translated_options"))  # type: ignore
    ],
    package: str,
):
    logger.info(f"Preparing package detail for {package}...")

    package_detail = await interface.get_package_detail(
        driver_parameters, repository_parameters, translated_options, package
    )

    logger.info(f"Package detail for {package} ready.")

    if (
        package_detail is not None
        and isinstance(package_detail.product, ArchiveProductDetail)
        and isinstance(package_detail.product.archive, Path)
    ):
        # TODO: iterate file chunks
        with package_detail.product.archive.open("rb") as file:
            archive_bytes = memoryview(file.read())

            return StreamingResponse(
                HTTP_200_OK,
                response.headers,
                async_chain(
                    dump_one(package_detail), dump_bytes_chunked(archive_bytes)
                ),
            )

    return package_detail


async def compute_product_info(
    translated_options: Annotated[
        Any, Depends(load_model_from_query(Any, "translated_options"))  # type: ignore
    ],
    package: str,
    dependency_product_infos: Annotated[
        DependencyProductInfos,
        Depends(
            load_model_from_query(DependencyProductInfos, "dependency_product_infos")
        ),
    ],
):
    logger.info(f"Computing product info for {package}...")

    product_info = await interface.compute_product_info(
        driver_parameters,
        repository_parameters,
        translated_options,
        package,
        dependency_product_infos,
    )

    logger.info(f"Product info for {package} ready.")

    return product_info


class SubmanagerServer(FastAPI):
    def __init__(self):
        super().__init__(redoc_url=None)

        super().get("/translator-data", dependencies=[Depends(enable_epoch_cache)])(
            fetch_translator_data
        )
        super().get("/translate-options", dependencies=[Depends(enable_epoch_cache)])(
            translate_options
        )
        super().get("/formula", dependencies=[Depends(enable_epoch_cache)])(get_formula)
        super().get(
            "/packages/{package}", dependencies=[Depends(enable_permanent_cache)]
        )(get_package_detail)
        super().get(
            "/packages/{package}/product-info",
            dependencies=[Depends(enable_permanent_cache)],
        )(compute_product_info)


server = SubmanagerServer()
