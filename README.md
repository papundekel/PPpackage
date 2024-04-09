# PPpackage

An experimental package meta-manager.

Currently supports [`arch`](https://archlinux.org/) and [`conan`](https://conan.io/) sub-managers. Also implements a custom `PP` submanager for testing and demonstration purposes.

Takes a set of requirements and creates an installation directory with packages that satisfy the requirements.

## Architecture

The application consists of two main parts. The meta-manager, with which the user interacts, and submanagers, which are queried by the meta-manager.

### Glossary

- **package** - a string identifying a set of related package versions. Unique to a submanager.
- **package version** - a string identifying a specific version of a package. Corresponds to one **package source**.
- **package source** - a set of files from which a package can be built.
- **package product** or **product** - a set of files that are the result of building a package from a package source. Can be installed into a directory.
- **product ID** - a string identifying a product.
- **product info** - a JSON containing information about a product. May contain useful information about ABI. **infos** of dependencies are consumed when building the depending package.
- **requirement** - a JSON with specific meaning to a submanager. Constrains the resulting installation.

### Meta-manager

The task of the meta-manager is to accept input from the user, parse it into requests which can be forwarded and answered by the submanagers, and to combine the results and present them to the user.

Detailed information about the input format can be found in the [Meta-manager Input](#meta-manager-input) section.

The meta-manager works in these basic phases:

1. **RESOLVE** - forwards the requirements to the submanagers until a set of package versions that satisfy the requirements is found
2. **FETCH** - when versions are known, the submanagers are requested to fetch the package products (e. g. binaries). This may mean downloading built binaries or building the packages. Outputs of this phase are also the product ID and product info. Fetching is done in the order defined by the dependency graph. Unordered packages are fetched in parallel.
3. **INSTALL** - when products are known, the submanagers are requested to install them into the installation directory. Output of this phase is the installation directory. Installation is done sequentially in the order defined by the dependency graph.
4. **GENERATE** - optional. When the installation directory is used to build a package depending on the installed packages, generators can be produced. Output of this phase is the generators directory. It contains necessary files for building against the installed packages.

### Submanagers

Submanagers are the actual package managers. They are responsible for resolving requirements, downloading or building binaries and installing them into a directory.

Communication between the meta-manager and submanagers can be done in two ways. The first is by running the submanagers as part of the meta-manager by loading them as Python modules. The second is by making requests to a REST API. The way in which the submanagers are used is defined the meta-manager configuration.

The same interface that can be loaded by the meta-manager can also be used by the framework `PPpackage-submanager` to create a HTTP server serving the REST API interface needed by the meta-manager.

## Interfaces

### Python

```python
from PPpackage.submanager.schemes import (
    Dependency,
    Package,
    Product,
    ResolutionGraph,
)

async def update_database(
    settings: Settings,
    state: State,
):
    ...

async def resolve(
    settings: Settings,
    state: State,
    options: Any,
    requirements: AsyncIterable[AsyncIterable[Requirement]],
) -> AsyncIterable[ResolutionGraph]:
    ...

async def fetch(
    settings: Settings,
    state: State,
    options: Any,
    package: Package,
    dependencies: AsyncIterable[Dependency],
    installation_path: Path | None,
    generators_path: Path | None,
) -> ProductIDAndInfo | AsyncIterable[str]:
    ...

async def install(
    settings: Settings,
    state: State,
    options: Any,
    product: Product,
    installation_path: Path,
) -> None:
    ...

async def generate(
    settings: Settings,
    state: State,
    options: Any,
    products: AsyncIterable[Product],
    generators: AsyncIterable[str],
    generators_path: Path,
):
    ...
```

`Settings` and `State` are defined by the submanager.

### REST API

<summary><code>POST</code> <code><b>/resolve</b></code></summary>
<summary><code>POST</code> <code><b>/products</b></code></summary>
<summary><code>POST</code> <code><b>/installations</b></code></summary>
<summary><code>PATCH</code> <code><b>/installations/{id}</b></code></summary>
<summary><code>PUT</code> <code><b>/installations/{id}</b></code></summary>
<summary><code>GET</code> <code><b>/installations/{id}</b></code></summary>
<summary><code>DELETE</code> <code><b>/installations/{id}</b></code></summary>
<summary><code>POST</code> <code><b>/generators</b></code></summary>

\
All endpoints behave as their Python counterparts except for installation.

The **INSTALL** phase is fragmented in remote submanagers to allow for request interleaving.

To simulate the same behavior as in the Python interface, these steps are made:

1. a `POST` request is made to `/installations` to upload a directory. `id` is returned.
2. a series of `PATCH` requests is made to `/installations/{id}` to install products
3. `GET` request is made to `/installations/{id}` to download the installation directory
4. other submanagers do work on the directory
5. a `PUT` request is made to `/installations/{id}` to update the directory after changes made
6. `GET` request is made to `/installations/{id}` to download the installation directory when all work is done
7. a `DELETE` request is made to `/installations/{id}` to delete the installation directory

## Meta-manager Input

The input is taken by stdin and it is in JSON format.

### Format

```json
{
    "requirements": {
        "manager1": [
            "req1",
            {
                "name": "req2",
                "version": ">=1.0.0"
            },
        ],
        "manager2": [
            ["req1a", "req1b"],
            ["req2a", "req2b", "req2c"]
        ],
    },
    "options": {
        "manager2": {
            "settings": {
                "arch": "x86_64",
                "build_type": "Release",
                "os": "Linux"
            },
        }
    },
    "generators": [
        "generator1",
        "generator2"
    ]
}
```

## Requirements

Each sub-manager can have any number of requirements.
The format of individual requirements is defined by the sub-manager.
Requirements are passed as-is by the meta-manager.

### arch

Just the package name or `provides` string, e.g. `bash` or `sh`.

### conan

Dictionary with package name and version requirement.

```json
{
    "package": "openssl",
    "version": "[>=3.1.0]"
},
```

Corresponds to `openssl/[>=3.1.0]` in Conan.

## Options

Any JSON object for a sub-manager. Modifies the behavior of the respective sub-manager.
Affects the resulting installation.

Inspired by Conan.

### arch

Ignored.

### conan

Parsed into a Conan [profile](https://docs.conan.io/2/reference/config_files/profiles.html) INI file.

## Generators

A set of strings.

Applies to all sub-managers (each gets the whole set).

Only useful when building. The installation contains the dependencies and generators are used to build againts them.

```bash
python -m PPpackage --generators <generators_path> ...
```

### arch

Ignored.

### conan

[generators](https://docs.conan.io/2/reference/conanfile/methods/generate.html?highlight=generator).

## Input example

```json
{
    "requirements": {
        "arch": [
            "sh",
            "coreutils",
        ],
        "conan": [
            {
                "package": "openssl",
                "version": "[>=3.1.0]"
            },
            {
                "package": "nameof",
                "version": "0.10.1"
            },
            {
                "package": "openssl",
                "version": "[>=3.1.1]"
            }
        ]
    },
    "options": {
        "conan": {
            "settings": {
                "arch": "x86_64",
                "build_type": "Release",
                "compiler": "gcc",
                "compiler.cppstd": "gnu17",
                "compiler.libcxx": "libstdc++11",
                "compiler.version": "13",
                "os": "Linux"
            },
            "options": {
                "zlib*:shared": "True"
            }
        }
    },
    "generators": [
        "CMakeDeps",
        "CMakeToolchain",
    ]
}
```

More input examples can be found in the `input/` directory.

## Resolution graph

The meta-manager is able to generate a dot file with the resolution graph.

```bash
python -m PPpackage --graph <graph_path> ...
```

## Testing

For all testing scenarios, a clone of the repository is required.

An empty directory where all temporary files and outputs can be stored is also helpful.
All scripts must be run from the root of the repository and expect the `tmp/` directory to exist.

```bash
git clone https://github.com/papundekel/PPpackage
cd PPpackage/
mkdir tmp/
```

The installation directory, generators and the resolution graph are located
in the `tmp/output/` directory in all scenarios.

Leaving the outputs before subsequent runs is possible, but note that in that case
the installation will be done on top of that content.

Note that all submanagers use caching and the first runs can take a few minutes.
Do not remove the cache directories/volumes to get the best performance.

All scripts are located in the `test/` directory.

### Native

It is possible to test the application directly on the host machine without any containerization.

As all applications in these scenarios run on the host, we need to install
the required packages first.

```bash
python -m venv .venv/
source .venv/bin/activate
pip install -r requirements-dev.txt
```

This script runs all submanagers as part of the meta-manager. Is the fastest
with the least requirements:

```bash
./test/all-local.sh < examples/input/basic.json
```

This script runs all submanagers as separate HTTP servers. It requires `hypercorn`
and sends the installation directories through the network so is slower than the
previous option:

```bash
./test/all-remote.sh < examples/input/basic.json
```

### Containerized

It is also possible to run the application using the Compose Specification.
Both Docker and podman are supported.

Docker requires more configuration because of how
user namespace mappings work, so the compose files are written to work for podman.
Support for Docker can be added to the compose file by supplying the `USER` environment variable to the composer and Dockerfile and bind mounting the `/etc/passwd`
and `/etc/group` files. An example of this configuration can be seen in the github workflow in `.github/compose.yaml`.

Submanager caches are configured to be stored in volumes. This means that
the cache from native runs will not be used. To use the cache from native runs,
change the compose files and bind mount the cache directories instead.

This script runs the metamanager in a container with all submanagers running
as its parts:

```bash
./test/containerized-all-local.sh < examples/input/basic.json
```

Before running containerized managers as servers, secrets used for authentication
need to be initialized. This needs to be done only once.
Run the following script:

```bash
./test/containerized-all-remote-init.sh
```

Then its posiible to run this script which runs the metamanager in a container with all submanagers running as HTTP servers in separate containers:

```bash
./test/containerized-all-remote.sh < examples/input/basic.json
```
