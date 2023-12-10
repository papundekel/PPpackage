from setuptools import setup

setup(
    name="PPpackage",
    packages=["PPpackage"],
    version="0.1.0",
    install_requires=[
        "PPpackage-utils",
        "typer",
        "typing-extensions",
        "frozendict",
        "networkx",
        "pydot",
    ],
)
