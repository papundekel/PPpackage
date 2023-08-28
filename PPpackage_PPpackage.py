#!/usr/bin/env python

from PPpackage_manager import *

import subprocess


def check_requirements(manager_requirements_input):
    if type(manager_requirements_input) is not dict:
        raise MyException("Invalid requirements format.")

    for manager, requirements in manager_requirements_input.items():
        if type(manager) is not str:
            raise MyException("Invalid requirements format.")

        if type(requirements) is not list:
            raise MyException("Invalid requirements format.")


def parse_requirements(manager_requirements_input):
    check_requirements(manager_requirements_input)

    return manager_requirements_input


def resolve(cache_path, manager_requirements):
    manager_lockfiles = {}

    for manager, requirements in manager_requirements.items():
        process = subprocess.Popen(
            [f"./PPpackage_{manager}.py", "resolve", cache_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            encoding="ascii",
        )

        lockfile_output = subprocess_communicate(
            process,
            f"Error in `PPpackage_{manager}.py resolve`",
            json.dumps(requirements),
        )

        manager_lockfiles[manager] = json.loads(lockfile_output)

    return manager_lockfiles


def check_lockfile(manager_lockfiles_input):
    if type(manager_lockfiles_input) is not dict:
        raise MyException("Invalid lockfile format.")

    for manager, lockfile in manager_lockfiles_input.items():
        if type(manager) is not str:
            raise MyException("Invalid lockfile format.")

        check_lockfile_simple(lockfile)


def parse_lockfile(manager_lockfiles_input):
    check_lockfile(manager_lockfiles_input)

    return manager_lockfiles_input


def merge_lockfile_product_ids(lockfile, product_ids):
    output = {}

    for key in lockfile:
        lockfile_value = lockfile[key]

        if key in product_ids:
            product_ids_value = product_ids[key]

            if type(lockfile_value) is dict and type(product_ids_value) is dict:
                output[key] = merge_lockfile_product_ids(
                    lockfile_value, product_ids_value
                )
            else:
                version = lockfile_value
                product_id = product_ids_value
                output[key] = {"version": version, "product_id": product_id}

    return output


def fetch(cache_path, manager_lockfiles, generators, generators_path):
    manager_product_ids = {}

    for manager, lockfile in manager_lockfiles.items():
        process = subprocess.Popen(
            [f"./PPpackage_{manager}.py", "fetch", cache_path, generators_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            encoding="ascii",
        )

        product_ids_output = subprocess_communicate(
            process,
            f"Error in `PPpackage_{manager}.py fetch`",
            json.dumps({"lockfile": lockfile, "generators": generators}),
        )

        product_ids = json.loads(product_ids_output)

        manager_product_ids[manager] = product_ids

    return manager_product_ids


def check_products(manager_products_input):
    if type(manager_products_input) is not dict:
        raise MyException("Invalid products format.")

    for manager, products in manager_products_input.items():
        if type(manager) is not str:
            raise MyException("Invalid products format.")

        check_products_simple(products)


def parse_products(manager_products_input):
    check_products(manager_products_input)

    return manager_products_input


def install(cache_path, manager_products, destination_path):
    for manager, products in manager_products.items():
        process = subprocess.Popen(
            [f"./PPpackage_{manager}.py", "install", cache_path, destination_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            encoding="ascii",
        )

        subprocess_communicate(
            process,
            f"Error in `PPpackage_{manager}.py install`",
            json.dumps(products),
        )


if __name__ == "__main__":
    execute(
        "PPpackage",
        resolve,
        fetch,
        install,
        parse_requirements,
        parse_lockfile,
        parse_products,
        {},
    )
