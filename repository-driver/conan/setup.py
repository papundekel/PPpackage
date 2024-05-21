from setuptools import setup

setup(
    name="PPpackage-repository-driver-conan",
    packages=["PPpackage.repository_driver.conan"],
    version="0.1.0",
    install_requires=[
        "PPpackage-repository-driver-interface",
        "PPpackage-utils-async",
        "PPpackage-utils-lock",
        "PPpackage-utils-json",
        "aiorwlock",
        "conan",
        "fasteners",
        "pydantic",
    ],
)
