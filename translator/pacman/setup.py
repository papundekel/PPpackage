from setuptools import setup

setup(
    name="PPpackage-translator-pacman",
    packages=["PPpackage.translator.pacman"],
    version="0.1.0",
    install_requires=["PPpackage-translator-interface", "pysat"],
)
