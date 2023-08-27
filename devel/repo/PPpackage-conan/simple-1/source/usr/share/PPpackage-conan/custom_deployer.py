from conan.internal.deploy import full_deploy

import os


def deploy(graph, output_folder, **kwargs):
    conanfile = graph.root.conanfile

    with open(os.path.join(output_folder, "deps"), "w") as f:
        for dep in conanfile.dependencies.values():
            f.write(
                f"{dep.ref}#{dep.ref.revision}:{dep.pref.package_id}#{dep.pref.revision}\n"
            )

    # full_deploy(graph, output_folder, **kwargs)
    for dep in conanfile.dependencies.values():
        path = os.path.join("/conan", dep.ref.name)
        dep.set_deploy_folder(path)
