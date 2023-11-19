from PPpackage_utils.app import init, run
from PPpackage_utils.utils import anoop

from .fetch import fetch
from .generate import generate
from .install import install
from .parse import Requirement
from .resolve import resolve
from .utils import get_package_paths


def main():
    data_path, deployer_path = get_package_paths()

    app = init(
        anoop,
        lambda cache_path, options, requirements_list: resolve(
            data_path, cache_path, options, requirements_list
        ),
        lambda cache_path, options, packages: fetch(
            data_path, cache_path, options, packages
        ),
        lambda cache_path, generators_path, options, products, generators: generate(
            data_path,
            deployer_path,
            cache_path,
            generators_path,
            options,
            products,
            generators,
        ),
        install,
        Requirement,
    )
    run(app, "conan")
