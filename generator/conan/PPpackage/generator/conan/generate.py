from collections.abc import Iterable
from pathlib import Path
from sys import stderr

from conan.api.conan_api import ConanAPI
from conans.model.recipe_ref import RecipeReference

from PPpackage.utils.utils import TemporaryDirectory

from .schemes import Parameters


def set_deploy_folders(api: ConanAPI, cache_directory_path: Path, graph):
    conanfile = graph.root.conanfile

    for dep in conanfile.dependencies.values():
        path = Path(api.cache.package_path(dep.pref))

        dep.set_deploy_folder(
            str(Path("/") / "root" / ".conan2" / path.relative_to(cache_directory_path))
        )


async def generate(
    parameters: Parameters,
    generator_full: str,
    products: Iterable[tuple[str, Path]],
    output_path: Path,
):
    with TemporaryDirectory() as cache_directory_path:
        api = ConanAPI(str(cache_directory_path))

        detected_profile = api.profiles.detect()

        (cache_directory_path / "profiles").mkdir(parents=True, exist_ok=True)

        with (cache_directory_path / "profiles" / "default").open("w") as profile_file:
            profile_file.write("[settings]\n")

            for setting, value in detected_profile.settings.items():
                profile_file.write(f"{setting}={value}\n")

        packages = list[RecipeReference]()

        for package, path in products:
            if package.startswith("conan-"):
                packages.append(RecipeReference.loads(package[len("conan-") :]))
                api.cache.restore(path)

        build_profile = api.profiles.get_profile(["default"])  # TODO
        host_profile = build_profile

        graph = api.graph.load_graph_requires(
            packages,
            profile_build=build_profile,
            profile_host=host_profile,
            tool_requires=[],
            lockfile=None,
            remotes=[],
            update=False,
        )

        api.graph.analyze_binaries(graph, remotes=[])
        api.install.install_binaries(graph)

        set_deploy_folders(api, cache_directory_path, graph)

        graph.root.conanfile.virtualrunenv = False
        graph.root.conanfile.virtualbuildenv = False

        generator = generator_full[len("conan-") :]

        with TemporaryDirectory() as fake_source_folder_path:
            api.install.install_consumer(
                graph, [generator], fake_source_folder_path, str(output_path.absolute())
            )
