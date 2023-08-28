#!/usr/bin/env python

from PPpackage_manager import *

import shutil
import sys
import json
import tempfile
import subprocess
import jinja2
import contextlib
import os


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
    return json.loads(graph_string)["graph"]["nodes"].values()


def parse_conan_graph_resolve(graph_string):
    nodes = parse_conan_graph_nodes(graph_string)

    return {
        (package_version := ref.split("/", 1))[0]: package_version[1]
        for node in nodes
        if (ref := node["ref"]) != "" and node["user"] != "pppackage"
    }


def parse_conan_graph_fetch(input):
    nodes = parse_conan_graph_nodes(input)

    return {
        ref.split("/", 1)[0]: f"{node['package_id']}#{node['prev']}"
        for node in nodes
        if (ref := node["ref"]) != ""
    }


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
def create_and_render_temp_file(template, template_context, suffix):
    with tempfile.NamedTemporaryFile(mode="w", suffix=suffix) as file:
        content = template.render(**template_context)

        file.write(content)
        file.flush()

        yield file


def export_leaf(environment, template, index, requirement_partition):
    with create_and_render_temp_file(
        template, {"index": index, "requirements": requirement_partition}, ".py"
    ) as conanfile_leaf:
        process = subprocess.Popen(
            [
                "conan",
                "export",
                conanfile_leaf.name,
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            encoding="ascii",
            env=environment,
        )

        subprocess_wait(process, "Error in `conan export`.")


def export_leaves(environment, template, requirement_partitions):
    for index, requirement_partition in enumerate(requirement_partitions):
        export_leaf(environment, template, index, requirement_partition)


def get_lockfile(environment, conanfile_root):
    process = subprocess.Popen(
        [
            "conan",
            "graph",
            "info",
            "--format",
            "json",
            "--profile:build=profile",
            "--profile:host=profile",
            conanfile_root.name,
        ],
        stdout=subprocess.PIPE,
        encoding="ascii",
        env=environment,
    )

    graph_string = subprocess_wait(process, "Error in `conan graph info`")

    lockfile = parse_conan_graph_resolve(graph_string)

    return lockfile


def remove_leaves_from_cache(environment):
    process = subprocess.Popen(
        ["conan", "remove", "--confirm", "leaf-*/1.0.0@pppackage"],
        stdout=subprocess.DEVNULL,
        encoding="ascii",
        env=environment,
    )

    subprocess_wait(process, "Error in `conan remove`")


def patch_generators_paths(generators_path, file_paths):
    for file_path in file_paths:
        presets_path = os.path.join(generators_path, file_path)

        generators_path_abs = os.path.abspath(generators_path)

        if os.path.exists(presets_path):
            with open(presets_path, "r") as presets_file:
                lines = presets_file.readlines()

            lines = [
                line.replace(generators_path_abs, "/PPpackage/generators")
                for line in lines
            ]

            with open(presets_path, "w") as presets_file:
                presets_file.writelines(lines)


def patch_generators(generators_path):
    patch_generators_paths(generators_path, ["CMakePresets.json"])


def install_product(environment, product, destination_path):
    process = subprocess.Popen(
        [
            "conan",
            "cache",
            "path",
            f"{product.package}/{product.version}:{product.product_id}",
        ],
        stdout=subprocess.PIPE,
        encoding="ascii",
        env=environment,
    )

    stdout = subprocess_wait(process, "Error in `conan cache path`")

    product_path = stdout.splitlines()[0]

    shutil.copytree(
        product_path,
        os.path.join(destination_path, product.package),
        symlinks=True,
        dirs_exist_ok=True,
    )


def resolve(cache_path, requirements):
    cache_path = get_cache_path(cache_path)

    ensure_dir_exists(cache_path)

    # CONAN_HOME must be an absolute path
    environment = make_conan_environment(cache_path)

    requirement_partitions = create_requirement_partitions(requirements)

    jinja_loader = jinja2.Environment(
        loader=jinja2.FileSystemLoader(""),
        autoescape=jinja2.select_autoescape(),
    )

    template_leaf = jinja_loader.get_template("conanfile-leaf.py.jinja")

    export_leaves(environment, template_leaf, requirement_partitions)

    template_root = jinja_loader.get_template("conanfile-root.py.jinja")

    with create_and_render_temp_file(
        template_root,
        {"leaf_indices": range(len(requirement_partitions))},
        ".py",
    ) as conanfile_root:
        lockfile = get_lockfile(environment, conanfile_root)

    remove_leaves_from_cache(environment)

    return lockfile


def fetch(cache_path, lockfile, generators, generators_path):
    cache_path = get_cache_path(cache_path)

    environment = make_conan_environment(cache_path)

    jinja_loader = jinja2.Environment(
        loader=jinja2.FileSystemLoader(""),
        autoescape=jinja2.select_autoescape(),
    )

    template = jinja_loader.get_template("conanfile-fetch.py.jinja")

    with create_and_render_temp_file(
        template, {"lockfile": lockfile, "generators": generators}, ".py"
    ) as conanfile:
        process = subprocess.Popen(
            [
                "conan",
                "install",
                "--output-folder",
                os.path.normpath(generators_path),  # conan doesn't normalize paths here
                "--deployer",
                "PPpackage_conan_deployer.py",
                "--build",
                "missing",
                "--format",
                "json",
                "--profile:build=profile",
                "--profile:host=profile",
                conanfile.name,
            ],
            stdout=subprocess.PIPE,
            encoding="ascii",
            env=environment,
        )

        graph_json = subprocess_wait(process, "Error in `conan install`")

    products = parse_conan_graph_fetch(graph_json)

    patch_generators(generators_path)

    return products


def install(cache_path, products, destination_path):
    cache_path = get_cache_path(cache_path)

    environment = make_conan_environment(cache_path)

    destination_path = os.path.join(destination_path, "conan")

    for product in products:
        install_product(environment, product, destination_path)


if __name__ == "__main__":
    execute(
        "conan",
        resolve,
        fetch,
        install,
        parse_requirements,
        parse_lockfile_simple,
        parse_products_simple,
        {},
    )
