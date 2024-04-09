from setuptools import setup

setup(
    name="PPpackage-metamanager",
    packages=["PPpackage.metamanager"],
    version="0.1.0",
    install_requires=[
        "PPpackage-utils",
        "PPpackage-repository-driver-interface",
        "typer",
        "typing-extensions",
        "frozendict",
        "networkx",
        "pydot",
        "httpx[http2]",
    ],
)
