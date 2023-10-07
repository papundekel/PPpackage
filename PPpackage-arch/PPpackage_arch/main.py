from PPpackage_utils.app import init, run
from PPpackage_utils.utils import noop, parse_lockfile_simple, parse_products_simple

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
        parse_lockfile_simple,
        parse_products_simple,
    )
    run(app, "arch")
