from setuptools import setup

setup(
    name="PPpackage-repository-driver-server",
    packages=["PPpackage.repository_driver.server"],
    version="0.1.0",
    install_requires=[
        "PPpackage-repository-driver-interface",
        "fastapi",
        "pydantic_settings",
    ],
)
