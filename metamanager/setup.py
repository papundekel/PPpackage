from setuptools import setup

setup(
    name="PPpackage-metamanager",
    packages=[
        "PPpackage.metamanager",
        "PPpackage.metamanager.fetch",
        "PPpackage.metamanager.schemes",
        "PPpackage.metamanager.repository",
    ],
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
        "python-sat[aiger, approxmc, cryptosat, pblib]",
        "asyncstdlib",
        "sqlitedict",
        "hishel[sqlite]",
    ],
)
