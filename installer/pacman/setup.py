from setuptools import setup

setup(
    name="PPpackage-installer-pacman",
    packages=["PPpackage.installer.pacman"],
    version="0.1.0",
    install_requires=["PPpackage-installer-interface"],
)
