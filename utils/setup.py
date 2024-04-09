from setuptools import setup

setup(
    name="PPpackage-utils",
    packages=["PPpackage.utils"],
    version="0.1.0",
    install_requires=["typer", "frozendict", "pydantic", "pid", "Jinja2"],
)
