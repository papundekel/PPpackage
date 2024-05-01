from setuptools import setup

setup(
    name="PPpackage-installer-conan",
    packages=["PPpackage.installer.conan"],
    version="0.1.0",
    install_requires=["PPpackage-installer-interface", "conan"],
)
