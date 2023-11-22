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
        lambda *args: resolve(data_path, *args),
        lambda *args: fetch_send(data_path, *args),
        fetch_receive,
        lambda *args: generate(data_path, deployer_path, *args),
        install,
        Requirement,
    )
    run(app, "conan")
