from setuptools import setup

setup(
    name="PPpackage-translator-conan",
    packages=["PPpackage.translator.conan"],
    version="0.1.0",
    install_requires=["PPpackage-translator-interface", "conan"],
)
