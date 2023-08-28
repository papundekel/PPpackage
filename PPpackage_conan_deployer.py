from conan.internal.deploy import full_deploy

import os
import sys


def deploy(graph, output_folder, **kwargs):
    conanfile = graph.root.conanfile

    for dep in conanfile.dependencies.values():
        path = os.path.join("/conan", dep.ref.name)
        dep.set_deploy_folder(path)
