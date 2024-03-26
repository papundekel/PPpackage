from setuptools import setup

setup(
    name="PPpackage-submanager",
    packages=["PPpackage_submanager"],
    version="0.1.0",
    install_requires=[
        "PPpackage_utils",
        "pydantic-settings",
        "sqlmodel",
        "aiosqlite",
        "fastapi",
        "asyncstdlib",
    ],
)
