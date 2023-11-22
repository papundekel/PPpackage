from PPpackage_utils.app import init, run
from PPpackage_utils.utils import anoop

from .fetch import receive as fetch_receive
from .fetch import send as fetch_send
from .generate import generate
from .install import install
from .parse import Requirement
from .resolve import resolve
from .utils import get_package_paths


def main():
    data_path, deployer_path = get_package_paths()

    app = init(
        anoop,
        lambda debug, cache_path, options, requirements_list: resolve(
            debug, data_path, cache_path, options, requirements_list
        ),
        lambda debug, cache_path, options, packages: fetch_send(
            debug, data_path, cache_path, options, packages
        ),
        fetch_receive,
        lambda debug, cache_path, generators_path, options, products, generators: generate(
            debug,
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
