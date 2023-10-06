from setuptools import setup

setup(
    name="PPpackage",
    packages=["PPpackage"],
    version="0.1.0",
    install_requires=["PPpackage-utils", "typer", "typing-extensions"],
    entry_points={"console_scripts": ["PPpackage = PPpackage.main:main"]},
)
