from setuptools import setup

setup(
    name="PPpackage-repository-driver-PP",
    packages=["PPpackage.repository_driver.PP"],
    version="0.1.0",
    install_requires=[
        "PPpackage-utils",
        "PPpackage-repository-driver-interface",
    ],
)
