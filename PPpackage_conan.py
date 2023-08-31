#!/usr/bin/env python

from PPpackage_utils import (
    MyException,
    asubprocess_communicate,
    check_dict_format,
    ensure_dir_exists,
    parse_lockfile_simple,
    parse_products_simple,
    init,
    app,
    run,
)

import shutil
import json
import tempfile
import subprocess
import jinja2
import contextlib
import os
import asyncio
import sys


def get_cache_path(cache_path):
    return f"{cache_path}/conan/"


def make_conan_environment(cache_path):
    environment = os.environ.copy()

    environment["CONAN_HOME"] = os.path.abspath(cache_path)

    return environment


class Requirement:
    def __init__(self, package, version):
        self.package = package
        self.version = version


def check_requirements(requirements_input):
    if type(requirements_input) is not list:
        raise MyException("Invalid requirements format.")

    for requirement_input in requirements_input:
        check_dict_format(
            requirement_input,
            {"package", "version"},
            set(),
            "Invalid requirement format.",
        )

        if type(requirement_input["package"]) is not str:
            raise MyException("Invalid requirement format.")

        if type(requirement_input["version"]) is not str:
            raise MyException("Invalid requirement format.")


def parse_requirements(requirements_input):
    check_requirements(requirements_input)

    return [
        Requirement(requirement_input["package"], requirement_input["version"])
        for requirement_input in requirements_input
    ]


def parse_conan_graph_nodes(graph_string):
    return [
        node
        for node in json.loads(graph_string)["graph"]["nodes"].values()
        if node["ref"] != ""
    ]


def parse_conan_graph_resolve(graph_string):
    nodes = parse_conan_graph_nodes(graph_string)

    return {
        (package_and_version := node["ref"].split("/", 1))[0]: package_and_version[1]
        for node in nodes
        if node["user"] != "pppackage"
    }


class GraphInfo:
    def __init__(self, node):
        self.product_id = f"{node['package_id']}#{node['prev']}"
        self.cpp_info = node["cpp_info"]


def parse_conan_graph_fetch(input):
    nodes = parse_conan_graph_nodes(input)

    return {node["ref"].split("/", 1)[0]: GraphInfo(node) for node in nodes}


def create_requirement_partitions(requirements):
    requirement_partitions = []

    for requirement in requirements:
        partition_available = next(
            (
                partition
                for partition in requirement_partitions
                if requirement.package not in partition
            ),
            None,
        )

        if partition_available is None:
            requirement_partitions.append({})
            partition_available = requirement_partitions[-1]

        partition_available[requirement.package] = requirement.version

    return requirement_partitions


@contextlib.contextmanager
def create_and_render_temp_file(template, template_context, suffix=None):
    with tempfile.NamedTemporaryFile(mode="w", suffix=suffix) as file:
        content = template.render(**template_context)

        file.write(content)
        file.flush()

        yield file


async def export_leaf(environment, template, index, requirement_partition):
    with create_and_render_temp_file(
        template, {"index": index, "requirements": requirement_partition}, ".py"
    ) as conanfile_leaf:
        process = asyncio.create_subprocess_exec(
            "conan",
            "export",
            conanfile_leaf.name,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            env=environment,
        )

        await asubprocess_communicate(await process, "Error in `conan export`.")


async def export_leaves(environment, template, requirement_partitions):
    for index, requirement_partition in enumerate(requirement_partitions):
        await export_leaf(environment, template, index, requirement_partition)


async def get_lockfile(
    environment, root_template, profile_template, requirement_partitions, options
):
    with (
        create_and_render_temp_file(
            root_template,
            {"leaf_indices": range(len(requirement_partitions))},
            ".py",
        ) as root_file,
        create_and_render_temp_file(
            profile_template, {"options": options}
        ) as profile_file,
    ):
        process = asyncio.create_subprocess_exec(
            "conan",
            "graph",
            "info",
            "--format",
            "json",
            f"--profile:host={profile_file.name}",
            "--profile:build=profile",
            root_file.name,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=None,
            env=environment,
        )

        graph_string = await asubprocess_communicate(
            await process, "Error in `conan graph info`"
        )

    lockfile = parse_conan_graph_resolve(graph_string.decode("ascii"))

    return lockfile


async def remove_leaves_from_cache(environment):
    process = asyncio.create_subprocess_exec(
        "conan",
        "remove",
        "--confirm",
        "leaf-*/1.0.0@pppackage",
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=None,
        env=environment,
    )

    await asubprocess_communicate(await process, "Error in `conan remove`")


def patch_native_generators_paths(
    old_generators_path, new_generators_path, files_to_patch_paths
):
    for file_to_patch_path in files_to_patch_paths:
        old_generators_path_abs = os.path.abspath(old_generators_path)

        if os.path.exists(file_to_patch_path):
            with open(file_to_patch_path, "r") as file_to_patch:
                lines = file_to_patch.readlines()

            lines = [
                line.replace(old_generators_path_abs, new_generators_path)
                for line in lines
            ]

            with open(file_to_patch_path, "w") as file_to_patch:
                file_to_patch.writelines(lines)


def patch_native_generators(native_generators_path, native_generators_path_suffix):
    new_generators_path = os.path.join(
        "/PPpackage/generators", native_generators_path_suffix
    )
    patch_native_generators_paths(
        native_generators_path,
        new_generators_path,
        [
            os.path.join(native_generators_path, file_sub_path)
            for file_sub_path in ["CMakePresets.json"]
        ],
    )


async def install_product(environment, destination_path, product):
    process = await asyncio.create_subprocess_exec(
        "conan",
        "cache",
        "path",
        f"{product.package}/{product.version}:{product.product_id}",
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=None,
        env=environment,
    )

    stdout = await asubprocess_communicate(process, "Error in `conan cache path`")

    product_path = stdout.decode("ascii").splitlines()[0]

    shutil.copytree(
        product_path,
        os.path.join(destination_path, product.package),
        symlinks=True,
        dirs_exist_ok=True,
    )


def generator_info(generators_path, graph_infos):
    info_path = os.path.join(generators_path, "info")
    ensure_dir_exists(info_path)

    for package, graph_info in graph_infos.items():
        with open(os.path.join(info_path, f"{package}.json"), "w") as file:
            json.dump(graph_info.cpp_info, file, indent=4)


additional_generators = {"info": generator_info}


def check_options(input):
    check_dict_format(input, set(), {"settings", "options"}, "Invalid input format.")

    for category_input, assignments_input in input.items():
        if type(assignments_input) is not dict:
            raise MyException(
                f"Invalid input format. options[{category_input}] not a dict."
            )

        for value in assignments_input.values():
            if type(value) is not str:
                raise MyException(f"Invalid input format. `{value}` not a string.")


def parse_options(input):
    check_options(input)

    options = input

    return options


async def submanagers():
    return []


async def resolve(cache_path, requirements, options):
    cache_path = get_cache_path(cache_path)

    ensure_dir_exists(cache_path)

    # CONAN_HOME must be an absolute path
    environment = make_conan_environment(cache_path)

    requirement_partitions = create_requirement_partitions(requirements)

    jinja_loader = jinja2.Environment(
        loader=jinja2.FileSystemLoader(""),
        autoescape=jinja2.select_autoescape(),
    )

    leaf_template = jinja_loader.get_template("conanfile-leaf.py.jinja")

    await export_leaves(environment, leaf_template, requirement_partitions)

    root_template = jinja_loader.get_template("conanfile-root.py.jinja")
    profile_template = jinja_loader.get_template("profile.jinja")

    lockfile = await get_lockfile(
        environment, root_template, profile_template, requirement_partitions, options
    )

    await remove_leaves_from_cache(environment)

    return [lockfile]


async def fetch(cache_path, lockfile, options, generators, generators_path):
    cache_path = get_cache_path(cache_path)

    environment = make_conan_environment(cache_path)

    jinja_loader = jinja2.Environment(
        loader=jinja2.FileSystemLoader(""),
        autoescape=jinja2.select_autoescape(),
    )

    conanfile_template = jinja_loader.get_template("conanfile-fetch.py.jinja")
    profile_template = jinja_loader.get_template("profile.jinja")

    native_generators_path_suffix = "conan"
    native_generators_path = os.path.join(
        generators_path, native_generators_path_suffix
    )

    with (
        create_and_render_temp_file(
            conanfile_template,
            {
                "lockfile": lockfile,
                "generators": generators - additional_generators.keys(),
            },
            ".py",
        ) as conanfile_file,
        create_and_render_temp_file(
            profile_template, {"options": options}
        ) as profile_file,
    ):
        process = asyncio.create_subprocess_exec(
            "conan",
            "install",
            "--output-folder",
            os.path.normpath(
                native_generators_path
            ),  # conan doesn't normalize paths here
            "--deployer",
            "PPpackage_conan_deployer.py",
            "--build",
            "missing",
            "--format",
            "json",
            f"--profile:host={profile_file.name}",
            "--profile:build=profile",
            conanfile_file.name,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=None,
            env=environment,
        )

        graph_json = await asubprocess_communicate(
            await process, "Error in `conan install`"
        )

    graph_infos = parse_conan_graph_fetch(graph_json.decode("ascii"))

    patch_native_generators(native_generators_path, native_generators_path_suffix)

    for generator in generators & additional_generators.keys():
        additional_generators[generator](generators_path, graph_infos)

    product_ids = {
        package: graph_info.product_id for package, graph_info in graph_infos.items()
    }

    return product_ids


async def install(cache_path, products, destination_path):
    cache_path = get_cache_path(cache_path)

    environment = make_conan_environment(cache_path)

    destination_path = os.path.join(destination_path, "conan")

    if os.path.exists(destination_path):
        shutil.rmtree(destination_path)

    async with asyncio.TaskGroup() as group:
        for product in products:
            group.create_task(install_product(environment, destination_path, product))


if __name__ == "__main__":
    init(
        submanagers,
        resolve,
        fetch,
        install,
        parse_requirements,
        parse_options,
        parse_lockfile_simple,
        parse_products_simple,
    )
    run("conan")
