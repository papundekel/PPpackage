from setuptools import setup

setup(
    name="PPpackage-installer-interface",
    packages=["PPpackage.installer.interface"],
    version="0.1.0",
    install_requires=[
        "pydantic",
    ],
)
