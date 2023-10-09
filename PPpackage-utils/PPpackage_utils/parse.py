from typing import Any

from PPpackage_utils.utils import MyException, frozendict

Lockfile = frozendict[str, str]


def check_lockfile(debug: bool, lockfile_json: Any) -> None:
    if type(lockfile_json) is not frozendict:
        raise MyException("Invalid lockfile format: not a dict.")

    for version_json in lockfile_json.values():
        if type(version_json) is not str:
            raise MyException(
                f"Invalid lockfile version format: `{version_json}` not a string."
            )


def parse_lockfile(debug: bool, lockfile_json: Any) -> Lockfile:
    check_lockfile(debug, lockfile_json)

    lockfile = lockfile_json

    return lockfile
