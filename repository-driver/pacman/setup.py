from setuptools import setup

setup(
    name="PPpackage-pacman",
    packages=["PPpackage.pacman"],
    version="0.1.0",
    install_requires=[
        "PPpackage-utils",
        "PPpackage-pacman-utils",
        "pydot",
        "networkx",
        "pyalpm",
    ],
)
