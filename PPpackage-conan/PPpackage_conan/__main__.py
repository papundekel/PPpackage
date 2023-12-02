from functools import partial

from PPpackage_utils.submanager import fetch_receive_discard, main
from PPpackage_utils.utils import anoop

from .fetch import fetch_send
from .generate import generate
from .install import install
from .parse import Requirement
from .resolve import resolve
from .utils import get_package_paths

data_path, deployer_path = get_package_paths()

main(
    "conan",
    anoop,
    partial(resolve, data_path),
    partial(fetch_receive_discard, partial(fetch_send, data_path)),
    partial(generate, data_path, deployer_path),
    install,
    Requirement,
)
