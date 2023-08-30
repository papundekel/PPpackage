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


def submanagers():
    return []


def resolve(cache_path, manager_requirements):
    manager_lockfiles = {}

    for manager, requirements in manager_requirements.items():
        process = subprocess.Popen(
            [f"./PPpackage_{manager}.py", "resolve", cache_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            encoding="ascii",
        )

        lockfiles_output = subprocess_communicate(
            process,
            f"Error in {manager}'s resolve.",
            json.dumps(requirements),
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


def fetch(cache_path, manager_lockfile_dict, generators, generators_path):
    manager_product_ids = {}

    for manager, lockfile in manager_lockfile_dict.items():
        process = subprocess.Popen(
            [f"./PPpackage_{manager}.py", "fetch", cache_path, generators_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            encoding="ascii",
        )

        product_ids_output = subprocess_communicate(
            process,
            f"Error in {manager}'s fetch.",
            json.dumps(
                {"lockfile": lockfile, "generators": generators}, cls=SetEncoder
            ),
        )

        product_ids = json.loads(product_ids_output)

        manager_product_ids[manager] = product_ids

    return manager_product_ids


def install(cache_path, manager_versions, manager_product_ids, destination_path):
    for manager, versions in manager_versions.items():
        product_ids = manager_product_ids[manager]

        products = merge_lockfiles(versions, product_ids)

        process = subprocess.Popen(
            [f"./PPpackage_{manager}.py", "install", cache_path, destination_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            encoding="ascii",
        )

        subprocess_communicate(
            process,
            f"Error in {manager}'s install.",
            json.dumps(products),
        )


def parse_requirements_generators(input):
    check_dict_format(
        input,
        {"requirements", "generators"},
        set(),
        "Invalid requirements-generators format.",
    )

    requirements = parse_requirements(input["requirements"])
    generators = parse_generators(input["generators"])

    return requirements, generators


if __name__ == "__main__":
    try:
        cache_path = parse_cl_argument(1, "Missing cache path argument.")
        generators_path = parse_cl_argument(2, "Missing generators path argument.")
        destination_path = parse_cl_argument(3, "Missing destination path argument.")

        requirements_generators_input = json.load(sys.stdin)

        requirements, generators = parse_requirements_generators(
            requirements_generators_input
        )

        versions = resolve(cache_path, requirements)

        product_ids = fetch(cache_path, versions, generators, generators_path)

        install(cache_path, versions, product_ids, destination_path)
    except MyException as e:
        print(f"PPpackage: {e}", file=sys.stderr)
        sys.exit(1)
