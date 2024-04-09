from setuptools import setup

setup(
    name="PPpackage-installer-simple",
    packages=["PPpackage.installer.simple"],
    version="0.1.0",
    install_requires=["PPpackage-installer-interface"],
)
