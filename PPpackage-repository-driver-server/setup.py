from setuptools import setup

setup(
    name="PPpackage-repository-driver-server",
    packages=["PPpackage_repository_driver_server"],
    version="0.1.0",
    install_requires=["PPpackage-repository-driver", "fastapi"],
)
