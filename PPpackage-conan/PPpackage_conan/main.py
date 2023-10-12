from PPpackage_utils.app import init, run
from PPpackage_utils.parse import parse_lockfile, parse_products
from PPpackage_utils.utils import anoop

from .fetch import fetch
from .install import install
from .parse import parse_options, parse_requirements
from .resolve import resolve
from .utils import get_package_paths


def main():
    data_path, deployer_path = get_package_paths()

    app = init(
        anoop,
        lambda cache_path, requirements, options: resolve(
            data_path, cache_path, requirements, options
        ),
        lambda cache_path, lockfile, options, generators, generators_path: fetch(
            data_path,
            deployer_path,
            cache_path,
            lockfile,
            options,
            generators,
            generators_path,
        ),
        install,
        parse_requirements,
        parse_options,
        parse_lockfile,
        parse_products,
    )
    run(app, "conan")
