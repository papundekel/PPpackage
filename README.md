# PPpackage

An experimental package meta-manager primarily focused on compiled languages, in particular C++.

Currently integrates [pacman](https://pacman.archlinux.page/) (both official and unofficial repositories), [AUR](https://aur.archlinux.org/) and [Conan](https://conan.io/).

Takes a propositional logic formula and produces a directory with a set of packages that satisfy the formula. The resulting directory is intended to be used as a root directory of a container image.

Promotes building packages from source with binary caching. Provides means to communicate ABI compatibility to take full advantage of caching.

Supports and generalizes Conan generators for package consumption.

## Glossary

- **package** - a string identifying a package source. Corresponds to a package version in most managers.
- **(package) source** - a set of files from which a package product can be built.
- **(package) product** - a set of files that are the result of building a package from a package source. Can be installed into a directory. Each package can produce many different products.
- **product info** - a JSON containing information about a product. May contain useful information about the ABI. (Although not necessary, it is also currently used as a unique product identifier).

## Architecture

The application is highly modular. It is divided into the meta-manager part and multiple different modules. The meta-manager is a driver which communicates with the modules. The modules implement the actual package managers' behavior.

The different types of modules are:

- repository driver
- requirement translator
- installer
- generator

Each module type handles a certain part of the package management process. There are typically multiple modules of each type, each implementing a part of some manager's functionality.

All modules ought to implement a Python interface.

#### Current modules

##### Repository drivers

- pacman
- AUR
- conan

##### Requirement translators

- pacman
- conan

AUR uses the archlinux package utility stack, so except for the logic of the repository, it uses the pacman modules.

##### Installers

- pacman
- conan

##### Generators

- conan

### Meta-manager

The task of the meta-manager is to accept input from the user, parse it into requests which can be forwarded and answered by the modules, and to combine and process the results and present them to the user.

Meta-manager also handles the SAT solving part.

Detailed information about the input format can be found in the [Meta-manager Input](#meta-manager-input) section. Information about the configuration file is found in [Meta-manager Configuration](#meta-manager-configuration).

The meta-manager works in these basic phases:

1. **RESOLVE** - the formula is resolved into a dependency graph.
2. **FETCH** - the packages are downloaded/built with respect to the graph.
3. **INSTALL** - each product is installed into the directory with respect to the graph.
4. **GENERATE** - optional. Each generator is invoked on the set of all products.

### Repository drivers

A repository driver is responsible for providing information about packages and their relationships.

#### Epoch

Some repository information is valid indefinitely, such as dependencies of a certain package version. Others can change in time, e. g. the set of all packages, therefore the driver must provide a current epoch identifier. When the epoch changes, all epoch-bound data are invalidated.

Repository drivers provide epoch as a separate interface and also in each interface providing epoch-bound data. This way the data can be validated against each other so every piece of information is from the same epoch.

#### Formula

The formula is the main piece of data that a repository provides. It describes valid package subsets that can coexist in an installation, i.e. it mainly provides the dependencies. It is a propositional logic formula and its variables are JSON objects that are eventually translated into strings.

The final formula is a conjunction of all repositories' formulas.

#### Translator data

In order for repositories to be able to provide packages that interact with each other, some data from repositories needs to be combined into a single structure. This is achieved by the translator data. It is a mapping of symbols to groups which is created from all repositories' translator data.

Its purpose is to provide information about which versions correspond to a single package or a package "provide" in pacman.

#### Package detail

The model satisfying a formula is a set of strings. From this set the package manager needs to derive a dependency graph. For this purpose, the repository driver provides a package detail for each package. If a string doesn't correspond to a package, the driver returns a null value.

A package's detail also contains its interfaces and interface dependencies. These are used to construct the dependency graph. Note that in a typical package manager a single dependency mechanism handles both the valid package sets and the dependency graph. In this application, these two issues are separated.

#### Build context

Information which describes how to fetch a package is here called the build context. It can either be:

- an archive URL - simplest, the product is directly downloaded
- meta build context - a regular input to the meta-manager which is used to construct a container in which the package is built

In the future it would also be possible to support building in a container specified by the image tag or a Dockerfile.

#### Product info

In order to support good caching, package authors and maintainers can provide information for each product. This "product info" is used to 1) identify the product and 2) provide ABI information to depending packages.

The repository driver is responsible for computing a product's info from just the product infos of its dependencies and some information about the build context *without* building the package. This is essential for caching, as we can determine whether a build would produce an equivalent product without actually building the package.

### Requirement translator

The requirement translators are mainly responsible for implementing version semantics. Their input is the whole translator info and a requirement from the formula. The output is again a formula, but with variables being strings.

#### Assumptions

The translators can also provide assumptions, which are variable polarity assignments that the meta-manager is supposed to try to satisfy. This is useful for preferential model selection i.e. when combing pacman and AUR where the user expects AUR packages to be used only if necessary.

### Installer

Since package installation is quite complex in both pacman and Conan, separate installer modules are used.

Pacman supports running arbitrary hooks while installing a package and also maintains a database of installed packages for updates.

Conan installs all packages into a single cache from which they can be used in builds using generators.

### Generator

Generators are used by Conan to provide a way to consume packages. Generators provide paths to libraries, CMake files and so on.

## Meta-manager Input

The input is taken by stdin and it is in JSON format.

### Format

```json
{
    "requirements": [
        {
            "translator": "pacman",
            "value": "official-package"
        },
        {
            "translator": "pacman",
            "value": "AUR-package=v1"
        },
        {
            "translator": "pacman",
            "value": "provide-package>=v2"
        },
        {
            "translator": "conan",
            "value": {
                "package": "package1",
                "version": "1.2.3"
            }
        },
        {
            "translator": "conan",
            "value": {
                "package": "package2",
                "version": "[>=2.3.4]"
            }
        }
    ],
    "generators": [
        "conan-CMakeDeps",
        "conan-CMakeToolchain"
    ]
}
```

### Requirements

The requirements are currently a conjunction but could be any propositional formula.

The `translator` field specifies the requirement translator to be used for translating that particular requirement. The `value` field is the actual value of the requirement.

#### `pacman` translator

Any string valid in pacman depends or conflicts field. This means a (virtual) package name with an optional version specification.

#### `conan` translator

Dictionary with package name and version requirement.

```json
{
    "package": "package",
    "version": "version"
},
```

Corresponds to `package/version` in Conan.

## Meta-manager Configuration

The configuration is a JSON file and is passed to the meta-manager by the `--config` CLI option.

### Format

```json
{
    "cache_path": "/path/to/cache/",
    "containerizer": {
        "url": "unix:///path/to/podman/or/docker.sock"
    },
    "repository_drivers": {
        "driver1": {
            "package": "python.package.driver1",
            "parameters": {
                "implementation_defined": ""
            }
        },
        "driver2": {
            "package": "python.package.driver2",
            "parameters": {
                "implementation_defined": ""
            }
        }
    },
    "translators": {
        "translator1": {
            "package": "python.package.translator1",
            "parameters": {
                "implementation_defined": ""
            }
        },
        "translator2": {
            "package": "python.package.translator2",
            "parameters": {
                "implementation_defined": ""
            }
        }
    },
    "installers": {
        "installer1": {
            "package": "python.package.installer1",
            "parameters": {
                "implementation_defined": ""
            }
        },
        "installer2": {
            "package": "python.package.installer2",
            "parameters": {
                "implementation_defined": ""
            }
        }
    },
    "generators": {
        "exact": {
            "package": "python.package.generator1",
            "parameters": {
                "implementation_defined": ""
            }
        },
        "prefix*": {
            "package": "python.package.generator2",
            "parameters": {
                "implementation_defined": ""
            }
        }
    },
    "repositories": [
        {
            "driver": "driver1",
            "parameters": {
                "implementation_defined": ""
            }
        },
        {
            "driver": "driver1",
            "parameters": {
                "implementation_defined": ""
            }
        },
        {
            "driver": "driver2",
            "parameters": {
                "implementation_defined": ""
            }
        }
    ]
}

```

## Resolution graph

The meta-manager is able to generate a dot file with the resolution graph.

```bash
python -m PPpackage.metamanager --graph <graph_path> ...
```

## Examples

For all testing scenarios, a clone of the repository is required.

All scripts expect to be run from the git repository root.
They create directory `tmp/` to store all files created during the run of the program.

```bash
git clone https://github.com/papundekel/PPpackage
cd PPpackage/
```

The installation directory will be locate in `tmp/root/`. Generators and the resolution graph are located in the `tmp/output/` directory.

Note that the program uses caching and so the first run is very slow compared to subsequent ones.

All scripts are located in the `examples/` directory.

### Native invocation

It is possible to test the application directly on the host machine without any containerization.

As all applications in these scenarios run on the host, we need to install
the required packages first.

```bash
python -m venv .venv/
source .venv/bin/activate
pip install --requirement requirements-dev.txt
```

`pyalpm`, a Python bindings library for `libalpm`, requires `libalpm` to be installed manually. The `pacman` installer uses `fakealpm` which has dependencies.

archlinux:

```bash
pacman -Syu libalpm gcc cmake ninja boost nlohmann-json
```

Ubuntu:

```bash
apt install libalpm-dev gcc cmake ninja-build libboost-dev nlohmann-json3-dev
```

To build `fakealpm`:

```bash
./installer/pacman/fakealpm/build.sh installer/pacman/fakealpm/ installer/pacman/fakealpm/build/ $fakealpm_install_dir
```

If `fakealpm_install_dir` is set to something else than `/usr/local/` then you need to configure `fakealpm_install_path` parameter in the `pacman` installer to that path.

### Containerized invocation

It is also possible to run the application using the Compose Specification.
Both Docker and podman are supported.

The only requirements are therefore Docker or podman and a composer (docker-compose or podman-compose).

Also, you need to build the images.

```bash
./images-build.sh $containerizer
```

Docker requires more configuration because of how
user namespace mappings work, so the compose files are written to work for podman.
Support for Docker can be added to the compose file by supplying the `USER` environment variable to the composer and Dockerfile and bind mounting the `/etc/passwd`
and `/etc/group` files. An example of this configuration can be seen in the github workflow in `.github/compose.yaml`.

### Updating repositories

Before using the manager, databases of used repositories need to be created. The examples contained in this repository always use the same configuration of five repositories. To create or update their databases, use one of the following methods.

```bash
./examples/update/native/update.sh
```

```bash
./examples/update/containerized/update.sh $containerizer
```

These scripts create files in `~/.PPpackage`. It is also the location where run scripts look for the files. All locations are configurable but are left to their simplest defaults for ease of testing.

### Running

```bash
./examples/metamanager/native/run.sh < examples/input/iana-etc.json
```

```bash
./examples/metamanager/containerized/run.sh $containerizer < examples/input/iana-etc.json
```

There are multiple input examples in the `examples/input/` directory, you can try any of them.

### Project

One example project is also provided. It is the project described in the Conan documentation. It resides in `examples/project/compressor/`.

First, the build context for the project is created with our meta-manager:

```bash
./examples/metamanager/$method/run.sh < examples/project/compressor/requirements.json
```

Next we need to move the directories from `tmp/`. `tmp/root` goes to `examples/project/compressor/build/root` and `tmp/output/generators/` into `examples/project/compressor/build/generators/`.

Then we can run the provided script, which uses the `root/` directory as image rootfs and builds the project with build script `examples/project/compressor/build.sh`. The script is just the modified version of commands run in the Conan documentation.

```bash
./examples/project/compressor/build-in-container.sh $containerizer

./examples/project/compressor/build/output/compressor
```

We can also invoke the meta-manager directly without the `run.sh` scripts and then we would not have to move the directories as we could specify the output directories directly. The only problem with this method is that the containerized meta-manager needs to have path translations for the containerizer set for the root directory and that requires changing the config.json file. The native version doesn't have this problem as it resides in the same mount namespace as the containerizer.
