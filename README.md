# PPpackage

An experimental package meta-manager.

Currently supports [`arch`](https://archlinux.org/) and [`conan`](https://conan.io/) sub-managers.

Takes a set of requirements and creates an installation directory with packages that satisfy the requirements.

## Usage

```bash
python -m venv .venv/
source .venv/bin/activate
pip install -r requirements.txt
python -m PPpackage_run $containerizer $cache_dir $root_dir < input.json
```

`containerizer` is either `docker` or `podman`.

`cache_dir` is a directory where sub-managers can cache their packages.

`root_dir` is the directory where the installation will be created.

## Requirements

- `python` >=3.11
- `podman` (and `crun`, should be installed with `podman`)
- `docker` when `containerizer` is `docker`

## Input

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
