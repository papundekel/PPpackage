# PPpackage

An experimental package meta-manager.

Currently supports [`arch`](https://archlinux.org/) and [`conan`](https://conan.io/) sub-managers. Also implements a custom `PP` submanager for testing and demonstration purposes.

Takes a set of requirements and creates an installation directory with packages that satisfy the requirements.

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
python -m PPpackage_run $containerizer $cache_dir $root_dir --generators $generators_dir < input.json
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
python -m PPpackage_run $containerizer $cache_dir $root_dir --graph $graph_path < input.json
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
./test/all-local.sh < input/basic.json
```

This script runs all submanagers as separate HTTP servers. It requires `hypercorn`
and sends the installation directories through the network so is slower than the
previous option:

```bash
./test/all-remote.sh < input/basic.json
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
./test/containerized-all-local.sh < input/basic.json
```

Before running containerized managers as servers, secrets used for authentication
need to be initialized. This needs to be done only once.
Run the following script:

```bash
./test/containerized-all-remote-init.sh
```

Then its posiible to run this script which runs the metamanager in a container with all submanagers running as HTTP servers in separate containers:

```bash
./test/containerized-all-remote.sh < input/basic.json
```
