from pathlib import Path


def deploy(graph, output_folder, **kwargs):
    conanfile = graph.root.conanfile

    for dep in conanfile.dependencies.values():
        path = Path("/conan") / dep.ref.name
        dep.set_deploy_folder(str(path))
