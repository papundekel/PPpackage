from asyncio import TaskGroup, create_subprocess_exec
from asyncio.subprocess import DEVNULL, PIPE
from collections.abc import (
    Callable,
    Generator,
    Iterable,
    Mapping,
    MutableMapping,
    MutableSequence,
    Sequence,
    Set,
)
from contextlib import contextmanager
from json import dump as json_dump
from json import loads as json_loads
from os import environ
from pathlib import Path
from shutil import copytree, rmtree
from tempfile import NamedTemporaryFile, _TemporaryFileWrapper
from typing import Any, NotRequired, Optional, TypedDict
from typing import cast as typing_cast

from jinja2 import Environment as Jinja2Environment
from jinja2 import FileSystemLoader as Jinja2FileSystemLoader
from jinja2 import Template as Jinja2Template
from jinja2 import select_autoescape as jinja2_select_autoescape
from PPpackage_utils.app import init, run
from PPpackage_utils.utils import (
    MyException,
    Product,
    asubprocess_communicate,
    check_dict_format,
    communicate_from_sub,
    ensure_dir_exists,
    parse_lockfile_simple,
    parse_products_simple,
)


def get_path(module) -> Path:
    return Path(module.__file__)


def get_package_paths():
    import PPpackage_conan

    from . import deployer

    data_path = get_path(PPpackage_conan).parent / "data"
    deployer_path = get_path(deployer)

    return data_path, deployer_path


async def update_database(cache_path: Path) -> None:
    pass


class Options(TypedDict):
    settings: NotRequired[Mapping[str, str]]
    options: NotRequired[Mapping[str, str]]


def get_cache_path(cache_path: Path) -> Path:
    return cache_path / "conan"


def make_conan_environment(cache_path: Path) -> Mapping[str, str]:
    environment = environ.copy()

    environment["CONAN_HOME"] = str(cache_path.absolute())

    return environment


class Requirement:
    def __init__(self, package: str, version: str):
        self.package = package
        self.version = version


def check_requirements(input: Any) -> Iterable[Mapping[str, str]]:
    if type(input) is not list:
        raise MyException("Invalid requirements format.")

    for requirement_input in input:
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

    return input


def parse_requirements(input: Any) -> Iterable[Requirement]:
    input_checked = check_requirements(input)

    return [
        Requirement(requirement_input["package"], requirement_input["version"])
        for requirement_input in input_checked
    ]


class Node(TypedDict):
    ref: str
    package_id: str
    prev: str
    user: str
    cpp_info: Mapping[str, Any]


def parse_conan_graph_nodes(
    graph_string: str,
) -> Iterable[Node]:
    return [
        node
        for node in json_loads(graph_string)["graph"]["nodes"].values()
        if node["ref"] != ""
    ]


def parse_conan_graph_resolve(graph_string: str) -> Mapping[str, str]:
    nodes = parse_conan_graph_nodes(graph_string)

    return {
        (package_and_version := node["ref"].split("/", 1))[0]: package_and_version[1]
        for node in nodes
        if node["user"] != "pppackage"
    }


class GraphInfo:
    def __init__(self, node: Node):
        self.product_id = f"{node['package_id']}#{node['prev']}"
        self.cpp_info = node["cpp_info"]


def parse_conan_graph_fetch(input: str) -> Mapping[str, GraphInfo]:
    nodes = parse_conan_graph_nodes(input)

    return {node["ref"].split("/", 1)[0]: GraphInfo(node) for node in nodes}


def create_requirement_partitions(
    requirements: Iterable[Requirement],
) -> Sequence[Mapping[str, str]]:
    requirement_partitions: MutableSequence[MutableMapping[str, str]] = []

    for requirement in requirements:
        partition_available: Optional[MutableMapping[str, str]] = next(
            (
                partition
                for partition in requirement_partitions
                if requirement.package not in partition
            ),
            None,
        )

        if partition_available is None:
            partition_available = typing_cast(MutableMapping[str, str], {})
            requirement_partitions.append(partition_available)

        partition_available[requirement.package] = requirement.version

    return requirement_partitions


@contextmanager
def create_and_render_temp_file(
    template: Jinja2Template,
    template_context: Mapping[str, Any],
    suffix: Optional[str] = None,
) -> Generator[_TemporaryFileWrapper, Any, Any]:
    with NamedTemporaryFile(mode="w", suffix=suffix) as file:
        content = template.render(**template_context)

        file.write(content)
        file.flush()

        yield file


async def export_leaf(
    environment: Mapping[str, str],
    template: Jinja2Template,
    index: int,
    requirement_partition: Mapping[str, str],
) -> None:
    with create_and_render_temp_file(
        template, {"index": index, "requirements": requirement_partition}, ".py"
    ) as conanfile_leaf:
        process = create_subprocess_exec(
            "conan",
            "export",
            conanfile_leaf.name,
            stdin=DEVNULL,
            stdout=DEVNULL,
            stderr=PIPE,
            env=environment,
        )

        await asubprocess_communicate(await process, "Error in `conan export`.")


async def export_leaves(
    environment: Mapping[str, str],
    template: Jinja2Template,
    requirement_partitions: Iterable[Mapping[str, str]],
) -> None:
    for index, requirement_partition in enumerate(requirement_partitions):
        await export_leaf(environment, template, index, requirement_partition)


async def get_lockfile(
    environment: Mapping[str, str],
    root_template: Jinja2Template,
    profile_template: Jinja2Template,
    build_profile_path: Path,
    requirement_partitions: Sequence[Mapping[str, str]],
    options: Options,
) -> Mapping[str, str]:
    with (
        create_and_render_temp_file(
            root_template,
            {"leaf_indices": range(len(requirement_partitions))},
            ".py",
        ) as root_file,
        create_and_render_temp_file(
            profile_template, {"options": options}
        ) as host_profile_file,
    ):
        host_profile_path = Path(host_profile_file.name)

        process = create_subprocess_exec(
            "conan",
            "graph",
            "info",
            "--format",
            "json",
            f"--profile:host={host_profile_path}",
            f"--profile:build={build_profile_path}",
            root_file.name,
            stdin=DEVNULL,
            stdout=PIPE,
            stderr=None,
            env=environment,
        )

        graph_string = await asubprocess_communicate(
            await process, "Error in `conan graph info`"
        )

    lockfile = parse_conan_graph_resolve(graph_string.decode("ascii"))

    return lockfile


async def remove_leaves_from_cache(environment: Mapping[str, str]) -> None:
    process = create_subprocess_exec(
        "conan",
        "remove",
        "--confirm",
        "leaf-*/1.0.0@pppackage",
        stdin=DEVNULL,
        stdout=DEVNULL,
        stderr=None,
        env=environment,
    )

    await asubprocess_communicate(await process, "Error in `conan remove`")


def patch_native_generators_paths(
    old_generators_path: Path,
    new_generators_path: Path,
    files_to_patch_paths: Iterable[Path],
) -> None:
    old_generators_path_abs_str = str(old_generators_path.absolute())
    new_generators_path_str = str(new_generators_path)

    for file_to_patch_path in files_to_patch_paths:
        if file_to_patch_path.exists():
            with open(file_to_patch_path, "r") as file_to_patch:
                lines = file_to_patch.readlines()

            lines = [
                line.replace(old_generators_path_abs_str, new_generators_path_str)
                for line in lines
            ]

            with open(file_to_patch_path, "w") as file_to_patch:
                file_to_patch.writelines(lines)


def patch_native_generators(
    native_generators_path: Path, native_generators_path_suffix: Path
) -> None:
    new_generators_path = Path("/PPpackage/generators") / native_generators_path_suffix

    patch_native_generators_paths(
        native_generators_path,
        new_generators_path,
        [
            native_generators_path / file_sub_path
            for file_sub_path in [Path("CMakePresets.json")]
        ],
    )


async def install_product(
    environment: Mapping[str, str], destination_path: Path, product: Product
) -> None:
    process = await create_subprocess_exec(
        "conan",
        "cache",
        "path",
        f"{product.package}/{product.version}:{product.product_id}",
        stdin=DEVNULL,
        stdout=PIPE,
        stderr=None,
        env=environment,
    )

    stdout = await asubprocess_communicate(process, "Error in `conan cache path`")

    product_path = stdout.decode("ascii").splitlines()[0]

    copytree(
        product_path,
        destination_path / product.package,
        symlinks=True,
        dirs_exist_ok=True,
    )


def generator_info(generators_path: Path, graph_infos: Mapping[str, GraphInfo]) -> None:
    info_path = generators_path / "info"
    ensure_dir_exists(info_path)

    for package, graph_info in graph_infos.items():
        with open(info_path / f"{package}.json", "w") as file:
            json_dump(graph_info.cpp_info, file, indent=4)


additional_generators: Mapping[str, Callable[[Path, Mapping[str, GraphInfo]], None]] = {
    "info": generator_info
}


def check_options(input: Any) -> Options:
    input_checked = typing_cast(
        Options,
        check_dict_format(
            input, set(), {"settings", "options"}, "Invalid input format."
        ),
    )

    for category_input, assignments_input in input_checked.items():
        if type(assignments_input) is not dict:
            raise MyException(
                f"Invalid input format. options[{category_input}] not a dict."
            )

        for value in assignments_input.values():
            if type(value) is not str:
                raise MyException(f"Invalid input format. `{value}` not a string.")

    return input_checked


def parse_options(input: Any) -> Options:
    input_checked = check_options(input)

    options = input_checked

    return options


async def resolve(
    templates_path: Path,
    cache_path: Path,
    requirements: Iterable[Requirement],
    options: Options,
) -> Iterable[Mapping[str, str]]:
    cache_path = get_cache_path(cache_path)

    ensure_dir_exists(cache_path)

    # CONAN_HOME must be an absolute path
    environment = make_conan_environment(cache_path)

    requirement_partitions = create_requirement_partitions(requirements)

    jinja_loader = Jinja2Environment(
        loader=Jinja2FileSystemLoader(templates_path),
        autoescape=jinja2_select_autoescape(),
    )

    leaf_template = jinja_loader.get_template("conanfile-leaf.py.jinja")
    root_template = jinja_loader.get_template("conanfile-root.py.jinja")
    profile_template = jinja_loader.get_template("profile.jinja")

    await export_leaves(environment, leaf_template, requirement_partitions)

    build_profile_path = templates_path / "profile"

    lockfile = await get_lockfile(
        environment,
        root_template,
        profile_template,
        build_profile_path,
        requirement_partitions,
        options,
    )

    await remove_leaves_from_cache(environment)

    return [lockfile]


async def fetch(
    templates_path: Path,
    deployer_path: Path,
    cache_path: Path,
    lockfile: Mapping[str, str],
    options: Options,
    generators: Iterable[str],
    generators_path: Path,
) -> Mapping[str, str]:
    cache_path = get_cache_path(cache_path)

    environment = make_conan_environment(cache_path)

    jinja_loader = Jinja2Environment(
        loader=Jinja2FileSystemLoader(templates_path),
        autoescape=jinja2_select_autoescape(),
    )

    conanfile_template = jinja_loader.get_template("conanfile-fetch.py.jinja")
    profile_template = jinja_loader.get_template("profile.jinja")

    native_generators_path_suffix = Path("conan")
    native_generators_path = generators_path / native_generators_path_suffix

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
        ) as host_profile_file,
    ):
        host_profile_path = Path(host_profile_file.name)
        build_profile_path = templates_path / "profile"

        process = create_subprocess_exec(
            "conan",
            "install",
            "--output-folder",
            str(native_generators_path),
            "--deployer",
            deployer_path,
            "--build",
            "missing",
            "--format",
            "json",
            f"--profile:host={host_profile_path}",
            f"--profile:build={build_profile_path}",
            conanfile_file.name,
            stdin=DEVNULL,
            stdout=PIPE,
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


async def install(
    cache_path: Path,
    products: Set[Product],
    destination_path: Path,
    pipe_from_sub_path: Path,
    pipe_to_sub_path: Path,
) -> None:
    cache_path = get_cache_path(cache_path)

    environment = make_conan_environment(cache_path)

    destination_path = destination_path / "conan"

    if destination_path.exists():
        rmtree(destination_path)

    async with TaskGroup() as group:
        for product in products:
            group.create_task(install_product(environment, destination_path, product))

    with communicate_from_sub(pipe_from_sub_path), open(pipe_to_sub_path, "r"):
        pass


def main():
    data_path, deployer_path = get_package_paths()

    app = init(
        update_database,
        lambda cache_path, requirements, options: resolve(
            data_path, cache_path, requirements, options
        ),
        lambda cache_path, lockfile, options, generators, generators_path: fetch(
            data_path,
            deployer_path,
            cache_path,
            lockfile,
            options,
            generators,
            generators_path,
        ),
        install,
        parse_requirements,
        parse_options,
        parse_lockfile_simple,
        parse_products_simple,
    )
    run(app, "conan")
