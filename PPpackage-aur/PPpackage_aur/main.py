from PPpackage_utils.app import init, run
from PPpackage_utils.parse import parse_lockfile, parse_products
from PPpackage_utils.utils import noop

from .fetch import fetch
from .install import install
from .parse import parse_requirements
from .resolve import resolve
from .update_database import update_database


def main():
    app = init(
        update_database,
        resolve,
        fetch,
        install,
        parse_requirements,
        noop,
        parse_lockfile,
        parse_products,
    )
    run(app, "arch")
