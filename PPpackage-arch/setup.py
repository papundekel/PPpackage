from setuptools import setup

setup(
    name="PPpackage-arch",
    packages=["PPpackage_arch"],
    version="0.1.0",
    install_requires=["PPpackage-utils", "pydot", "networkx"],
    entry_points={"console_scripts": ["PPpackage-arch = PPpackage_arch.main:main"]},
)
