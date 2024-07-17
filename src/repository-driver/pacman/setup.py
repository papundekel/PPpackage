from setuptools import setup

setup(
    name="PPpackage-repository-driver-pacman",
    packages=["PPpackage.repository_driver.pacman"],
    version="0.1.0",
    install_requires=[
        "PPpackage-repository-driver-interface",
        "PPpackage-utils-async",
        "PPpackage-utils-file",
        "PPpackage-utils-lock",
        "PPpackage-utils-json",
        "httpx[http2]",
        "networkx",
        "pyalpm",
        "pydot",
    ],
)
