from setuptools import setup

setup(
    name="PPpackage-run",
    packages=["PPpackage_run"],
    version="0.1.0",
    install_requires=[
        "typer",
        "PPpackage",
        "PPpackage-utils",
        "PPpackage-runner",
        "PPpackage-PP",
        "PPpackage-arch",
        "PPpackage-conan",
        "hypercorn",
        "httpx[http2]",
    ],
)
