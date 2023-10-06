from setuptools import setup

setup(
    name="PPpackage-runc",
    packages=["PPpackage_runc"],
    version="0.1.0",
    install_requires=["PPpackage-utils", "python-daemon", "typer"],
    entry_points={"console_scripts": ["PPpackage-runc = PPpackage_runc.main:main"]},
)
