from setuptools import setup

setup(
    name="PPpackage-repository-driver-interface",
    packages=["PPpackage.repository_driver.interface"],
    version="0.1.0",
    install_requires=[
        "PPpackage-utils-async",
        "frozendict",
        "pydantic",
    ],
)
