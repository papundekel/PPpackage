from setuptools import setup

setup(
    name="PPpackage-utils",
    packages=["PPpackage_utils"],
    version="0.1.0",
    install_requires=[
        "typer",
        "frozendict",
        "pydantic",
        "pid",
        "fastapi",
        "sqlmodel",
        "aiosqlite",
    ],
)
