from functools import partial

from PPpackage_utils.submanager import fetch_receive_discard, generate_empty, main
from PPpackage_utils.utils import anoop

from .fetch import fetch_send
from .install import install
from .resolve import resolve

main(
    "PP",
    anoop,
    resolve,
    partial(fetch_receive_discard, fetch_send),
    generate_empty,
    install,
    str,
)
