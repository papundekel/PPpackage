from setuptools import setup

setup(
    name="PPpackage-utils-container",
    packages=["PPpackage.utils.container"],
    version="0.1.0",
    install_requires=[
        "podman",
        "pydantic",
        "PPpackage-utils-json",
    ],
)
