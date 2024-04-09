from setuptools import setup

setup(
    name="PPpackage-pacman",
    packages=["PPpackage_pacman"],
    version="0.1.0",
    install_requires=[
        "PPpackage-utils",
        "PPpackage-submanager",
        "PPpackage-pacman-utils",
        "pydot",
        "networkx",
        "pyalpm",
    ],
)
