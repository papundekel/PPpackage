from setuptools import setup

setup(
    name="PPpackage-generator-conan",
    packages=["PPpackage.generator.conan"],
    version="0.1.0",
    install_requires=[
        "PPpackage-generator-interface",
        "conan",
        "PPpackage-utils",
    ],
)
