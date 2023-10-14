from setuptools import setup

setup(
    name="PPpackage-runner",
    packages=["PPpackage_runner"],
    version="0.1.0",
    install_requires=["PPpackage-utils", "python-daemon", "typer", "pid"],
    entry_points={"console_scripts": ["PPpackage-runner = PPpackage_runner.main:main"]},
)
