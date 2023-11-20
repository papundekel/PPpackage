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
        lambda cache_path, input: resolve(False, data_path, cache_path, input),
        lambda cache_path, input: fetch(False, data_path, cache_path, input),
        lambda cache_path, generators, generators_path, options, packages: generate(
            data_path,
            deployer_path,
            cache_path,
            generators,
            generators_path,
            options,
            packages,
        ),
        install,
        Requirement,
    )
    run(app, "conan")
