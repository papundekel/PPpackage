from setuptools import setup

setup(
    name="PPpackage-repository-driver-pacman",
    packages=["PPpackage.repository_driver.pacman"],
    version="0.1.0",
    install_requires=[
        "PPpackage-utils",
        "PPpackage-repository-driver-interface",
        "pydot",
        "networkx",
        "pyalpm",
        "httpx[http2]",
    ],
)
