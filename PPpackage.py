#!/usr/bin/env python

from PPpackage_utils import (
    MyException,
    subprocess_communicate,
    check_dict_format,
    parse_generators,
    parse_cl_argument,
    SetEncoder,
)

import subprocess
import itertools
import json
import sys
import os


def check_requirements(manager_requirements_input):
    if type(manager_requirements_input) is not dict:
        raise MyException("Invalid requirements format.")

    for manager, requirements in manager_requirements_input.items():
        if type(manager) is not str:
            raise MyException("Invalid requirements format.")

        if type(requirements) is not list:
            raise MyException("Invalid requirements format.")


def parse_requirements(input):
    check_requirements(input)

    requirements = input

    return requirements


def merge_lockfiles(versions, product_ids):
    return {
        package: {"version": versions[package], "product_id": product_ids[package]}
        for package in versions
        if package in product_ids
    }


def get_manager_path(managers_path, manager):
    return os.path.join(managers_path, f"PPpackage_{manager}.py")


def check_options(input):
    if type(input) is not dict:
        raise MyException("Invalid options format.")

    for options_input in input.values():
        if type(options_input) is not dict:
            raise MyException("Invalid options format.")


def parse_options(input):
    check_options(input)

    options = input

    return options


def parse_input(input):
    check_dict_format(
        input,
        {"requirements", "options", "generators"},
        set(),
        "Invalid input format.",
    )

    requirements = parse_requirements(input["requirements"])
    options = parse_options(input["options"])
    generators = parse_generators(input["generators"])

    return requirements, options, generators


def submanagers():
    return []


def resolve(managers_path, cache_path, manager_requirements, manager_options_dict):
    manager_lockfiles = {}

    for manager, requirements in manager_requirements.items():
        manager_path = get_manager_path(managers_path, manager)

        process = subprocess.Popen(
            [manager_path, "resolve", cache_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            encoding="ascii",
        )

        options = manager_options_dict.get(manager)

        lockfiles_output = subprocess_communicate(
            process,
            f"Error in {manager}'s resolve.",
            json.dumps(
                {
                    "requirements": requirements,
                    "options": options,
                }
            ),
        )

        lockfiles = json.loads(lockfiles_output)

        if type(lockfiles) is not list:
            raise MyException("Invalid lockfile format.")

        manager_lockfiles[manager] = lockfiles

    lockfiles = [
        {manager: lockfile for manager, lockfile in i}
        for i in itertools.product(
            *[
                [(manager, lockfile) for lockfile in lockfiles]
                for manager, lockfiles in manager_lockfiles.items()
            ]
        )
    ]

    lockfile = lockfiles[0]

    return lockfile


def fetch(
    managers_path,
    cache_path,
    manager_lockfile_dict,
    manager_options_dict,
    generators,
    generators_path,
):
    manager_product_ids = {}

    for manager, lockfile in manager_lockfile_dict.items():
        manager_path = get_manager_path(managers_path, manager)

        process = subprocess.Popen(
            [manager_path, "fetch", cache_path, generators_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            encoding="ascii",
        )

        options = manager_options_dict.get(manager)

        product_ids_output = subprocess_communicate(
            process,
            f"Error in {manager}'s fetch.",
            json.dumps(
                {"lockfile": lockfile, "options": options, "generators": generators},
                cls=SetEncoder,
            ),
        )

        product_ids = json.loads(product_ids_output)

        manager_product_ids[manager] = product_ids

    return manager_product_ids


def install(
    managers_path, cache_path, manager_versions, manager_product_ids, destination_path
):
    for manager, versions in manager_versions.items():
        manager_path = get_manager_path(managers_path, manager)

        process = subprocess.Popen(
            [manager_path, "install", cache_path, destination_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            encoding="ascii",
        )

        product_ids = manager_product_ids[manager]

        products = merge_lockfiles(versions, product_ids)

        subprocess_communicate(
            process, f"Error in {manager}'s install.", json.dumps(products)
        )


if __name__ == "__main__":
    try:
        managers_path = parse_cl_argument(1, "Missing managers path argument.")
        cache_path = parse_cl_argument(2, "Missing cache path argument.")
        generators_path = parse_cl_argument(3, "Missing generators path argument.")
        destination_path = parse_cl_argument(4, "Missing destination path argument.")

        requirements_generators_input = json.load(sys.stdin)

        requirements, options, generators = parse_input(requirements_generators_input)

        versions = resolve(managers_path, cache_path, requirements, options)

        product_ids = fetch(
            managers_path, cache_path, versions, options, generators, generators_path
        )

        install(managers_path, cache_path, versions, product_ids, destination_path)
    except MyException as e:
        print(f"PPpackage: {e}", file=sys.stderr)
        sys.exit(1)
