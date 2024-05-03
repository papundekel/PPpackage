from contextlib import asynccontextmanager
from functools import partial
from logging import getLogger
from pathlib import Path
from sys import stderr
from typing import Annotated, Any

from asyncstdlib import chain as async_chain
from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
from PPpackage.repository_driver.interface.interface import Interface
from PPpackage.repository_driver.interface.schemes import (
    ArchiveBuildContextDetail,
    ProductInfos,
    RepositoryConfig,
)
from pydantic import ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict
from starlette.status import HTTP_200_OK, HTTP_304_NOT_MODIFIED

from PPpackage.utils.stream import dump_bytes_chunked, dump_many, dump_one
from PPpackage.utils.utils import iterable_with_result, load_interface_module
from PPpackage.utils.validation import validate_json, validate_python

from .utils import StreamingResponse


class PackageSettings(BaseSettings):
    config_path: Path

    model_config = SettingsConfigDict(case_sensitive=False)


package_settings = PackageSettings()  # type: ignore


def parse_config(config_path: Path) -> RepositoryConfig:
    with config_path.open("rb") as f:
        config_json_bytes = f.read()

        try:
            config = validate_json(RepositoryConfig, config_json_bytes)
        except ValidationError as e:
            stderr.write("ERROR: Invalid config.\n")
            stderr.write(e.json(indent=4))

            raise

        return config


config = parse_config(package_settings.config_path)


interface = load_interface_module(Interface, config.driver.package)

driver_parameters = validate_python(
    interface.DriverParameters, config.driver.parameters
)
repository_parameters = validate_python(
    interface.RepositoryParameters, config.parameters
)


logger = getLogger(__name__)


def epoch_cache(request: Request, response: Response, epoch: str):
    request_epoch = request.headers.get("If-None-Match")

    if request_epoch == epoch:
        raise HTTPException(HTTP_304_NOT_MODIFIED)
    else:
        response.headers["Cache-Control"] = "public, no-cache, max-age=2147483648"
        response.headers["ETag"] = epoch


async def enable_permanent_cache(response: Response):
    response.headers["Cache-Control"] = "public, max-age=2147483648"


def load_model_from_query[T](Model: type[T], alias: str):
    def dependency(parameter: Annotated[str, Query(alias=alias)]) -> T:
        return validate_json(Model, parameter)

    return dependency


def get_state(request: Request):
    return request.state.state


async def fetch_translator_data(
    request: Request, response: Response, state: Annotated[Any, Depends(get_state)]
):
    logger.info("Preparing translator data...")

    epoch, translator_data = await iterable_with_result(
        partial(
            interface.fetch_translator_data,
            state,
            driver_parameters,
            repository_parameters,
        )
    )

    epoch_cache(request, response, epoch)

    logger.info("Translator data ready.")

    return StreamingResponse(HTTP_200_OK, response.headers, dump_many(translator_data))


async def translate_options(
    request: Request,
    response: Response,
    state: Annotated[Any, Depends(get_state)],
    options: Annotated[Any, Depends(load_model_from_query(Any, "options"))],  # type: ignore
):
    logger.info("Translating options...")

    epoch, translated_options = await interface.translate_options(
        state, driver_parameters, repository_parameters, options
    )

    epoch_cache(request, response, epoch)

    logger.info("Options translated.")

    return translated_options


async def get_formula(
    request: Request,
    response: Response,
    state: Annotated[Any, Depends(get_state)],
    translated_options: Annotated[
        Any, Depends(load_model_from_query(Any, "translated_options"))  # type: ignore
    ],
):
    logger.info("Preparing formula...")

    epoch, formula = await iterable_with_result(
        partial(
            interface.get_formula,
            state,
            driver_parameters,
            repository_parameters,
            translated_options,
        )
    )

    epoch_cache(request, response, epoch)

    logger.info("Formula ready.")

    return StreamingResponse(HTTP_200_OK, response.headers, dump_many(formula))


async def get_package_detail(
    response: Response,
    state: Annotated[Any, Depends(get_state)],
    translated_options: Annotated[
        Any, Depends(load_model_from_query(Any, "translated_options"))  # type: ignore
    ],
    package: str,
):
    logger.info(f"Preparing package detail for {package}...")

    package_detail = await interface.get_package_detail(
        state, driver_parameters, repository_parameters, translated_options, package
    )

    logger.info(f"Package detail for {package} ready.")

    return package_detail


async def get_build_context(
    state: Annotated[Any, Depends(get_state)],
    translated_options: Annotated[
        Any, Depends(load_model_from_query(Any, "translated_options"))  # type: ignore
    ],
    package: str,
    runtime_product_infos: Annotated[
        ProductInfos,
        Depends(
            load_model_from_query(ProductInfos, "runtime_product_infos")  # type: ignore
        ),
    ],
):
    logger.info(f"Fetching build context for {package}...")

    build_context = await interface.get_build_context(
        state,
        driver_parameters,
        repository_parameters,
        translated_options,
        package,
        runtime_product_infos,
    )

    logger.info(f"Build context for {package} ready.")

    return build_context


async def compute_product_info(
    state: Annotated[Any, Depends(get_state)],
    translated_options: Annotated[
        Any, Depends(load_model_from_query(Any, "translated_options"))  # type: ignore
    ],
    package: str,
    build_product_infos: Annotated[
        ProductInfos,
        Depends(
            load_model_from_query(ProductInfos, "build_product_infos")  # type: ignore
        ),
    ],
    runtime_product_infos: Annotated[
        ProductInfos,
        Depends(
            load_model_from_query(ProductInfos, "runtime_product_infos")  # type: ignore
        ),
    ],
):
    logger.info(f"Computing product info for {package}...")

    product_info = await interface.compute_product_info(
        state,
        driver_parameters,
        repository_parameters,
        translated_options,
        package,
        build_product_infos,
        runtime_product_infos,
    )

    logger.info(f"Product info for {package} ready.")

    return product_info


@asynccontextmanager
async def lifespan(_: FastAPI):
    async with interface.lifespan(driver_parameters, repository_parameters) as state:
        yield {"state": state}


class SubmanagerServer(FastAPI):
    def __init__(self):
        super().__init__(redoc_url=None, lifespan=lifespan)

        super().get("/translator-data")(fetch_translator_data)
        super().get("/translate-options")(translate_options)
        super().head("/translate-options")(translate_options)
        super().get("/formula")(get_formula)
        super().get(
            "/packages/{package}", dependencies=[Depends(enable_permanent_cache)]
        )(get_package_detail)
        super().get(
            "/packages/{package}/build-context",
            dependencies=[Depends(enable_permanent_cache)],
        )(get_build_context)
        super().get(
            "/packages/{package}/product-info",
            dependencies=[Depends(enable_permanent_cache)],
        )(compute_product_info)


server = SubmanagerServer()
