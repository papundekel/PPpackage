from setuptools import setup

setup(
    name="PPpackage-PP",
    packages=["PPpackage_PP"],
    version="0.1.0",
    install_requires=["PPpackage-utils"],
    entry_points={"console_scripts": ["PPpackage-PP = PPpackage_PP.main:main"]},
)
