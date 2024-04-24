from setuptools import setup

setup(
    name="PPpackage-repository-driver-update",
    packages=["PPpackage.repository_driver.update"],
    version="0.1.0",
    install_requires=[
        "PPpackage-repository-driver-interface",
    ],
)
