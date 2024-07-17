from setuptools import setup

setup(
    name="PPpackage-utils-lock",
    packages=["PPpackage.utils.lock"],
    version="0.1.0",
    install_requires=[
        "aiorwlock",
        "fasteners",
    ],
)
