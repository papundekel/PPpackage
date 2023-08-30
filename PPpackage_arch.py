#!/usr/bin/env python

from PPpackage_utils import (
    MyException,
    parse_cl_argument,
    ensure_dir_exists,
    execute,
    subprocess_wait,
    parse_lockfile_simple,
    parse_products_simple,
)

import sys
import subprocess
import re
import os


regex_package_name = re.compile(r"[a-zA-Z0-9\-@._+]+")


def get_cache_paths(cache_path):
    database_path = f"{cache_path}/arch/db"
    cache_path = f"{cache_path}/arch/cache"
    return database_path, cache_path


def parse_requirements(requirements_input):
    if type(requirements_input) is not list:
        raise MyException("Invalid requirements format")

    for requirement_input in requirements_input:
        if type(requirement_input) is not str:
            raise MyException("Invalid requirements format")

    return requirements_input


def update_database():
    cache_path = parse_cl_argument(2, "Missing cache path argument.")

    database_path, _ = get_cache_paths(cache_path)

    ensure_dir_exists(database_path)

    process = subprocess.Popen(
        ["fakeroot", "pacman", "--dbpath", database_path, "-Sy"],
        stdout=sys.stderr,
        encoding="ascii",
    )

    subprocess_wait(process, "Error in `pacman -Sy`")


def submanagers():
    return []


def resolve(cache_path, requirements):
    database_path, _ = get_cache_paths(cache_path)

    # trivial resolution of same-named packages
    requirements = set(requirements)

    dependencies = []

    for requirement in requirements:
        process = subprocess.Popen(
            [
                "pactree",
                "--dbpath",
                database_path,
                "-s",
                requirement,
            ],
            stdout=subprocess.PIPE,
            encoding="utf-8",
        )

        stdout = subprocess_wait(process, "Error in `pactree`.")

        for line in stdout.splitlines():
            match = regex_package_name.search(line)

            if match is None:
                raise MyException("Invalid pactree output.")

            dependency = match.group()
            dependencies.append(dependency)

    # trivial resolution of same-named packages
    dependencies = list(set(dependencies))

    process = subprocess.Popen(
        ["pacinfo", "--dbpath", database_path, "--short", *dependencies],
        stdout=subprocess.PIPE,
        encoding="ascii",
    )

    stdout = subprocess_wait(process, "Error in `pacinfo`.")

    lockfile = {}

    for line in stdout.splitlines():
        if line.startswith(" "):
            continue

        split_line = line.split()

        package = split_line[0].split("/")[-1]
        version = split_line[1].rsplit("-", 1)[0]

        lockfile[package] = version

    return [lockfile]


def fetch(cache_path, lockfile, generators, generators_path):
    database_path, cache_path = get_cache_paths(cache_path)

    ensure_dir_exists(cache_path)

    packages = list(lockfile.keys())

    process = subprocess.Popen(
        [
            "fakeroot",
            "pacman",
            "--dbpath",
            database_path,
            "--cachedir",
            cache_path,
            "--noconfirm",
            "-Sw",
            *packages,
        ],
        stdout=sys.stderr,
        encoding="ascii",
    )

    subprocess_wait(process, "Error in `pacman -Sw`.")

    process = subprocess.Popen(
        [
            "pacman",
            "--dbpath",
            database_path,
            "--cachedir",
            cache_path,
            "--noconfirm",
            "-Sddp",
            *packages,
        ],
        stdout=subprocess.PIPE,
        encoding="ascii",
    )

    stdout = subprocess_wait(process, "Error in `pacman -Sddp`")

    product_ids = {}

    for package, line in zip(packages, stdout.splitlines()):
        package_version_split = (
            line.rsplit("/", 1)[-1].partition(".pkg.tar.zst")[0].rsplit("-", 2)
        )

        product_id = f"{package_version_split[-2]}-{package_version_split[-1]}"

        product_ids[package] = product_id

    return product_ids


def install(cache_path, products, destination_path):
    _, cache_path = get_cache_paths(cache_path)
    database_path = f"{destination_path}/var/lib/pacman"

    ensure_dir_exists(database_path)

    environment = os.environ.copy()
    environment["FAKECHROOT_CMD_SUBST"] = "/usr/bin/ldconfig=/usr/bin/true"

    process = subprocess.Popen(
        [
            "fakechroot",
            "fakeroot",
            "pacman",
            "--noconfirm",
            "--needed",
            "--dbpath",
            database_path,
            "--cachedir",
            cache_path,
            "--root",
            destination_path,
            "-Udd",
            *[
                f"{cache_path}/{product.package}-{product.version}-{product.product_id}.pkg.tar.zst"
                for product in products
            ],
        ],
        stdout=sys.stderr,
        encoding="ascii",
        env=environment,
    )

    subprocess_wait(process, "Error in `pacman -Udd`")


if __name__ == "__main__":
    execute(
        "arch",
        submanagers,
        resolve,
        fetch,
        install,
        parse_requirements,
        parse_lockfile_simple,
        parse_products_simple,
        {"update-db": update_database},
    )
