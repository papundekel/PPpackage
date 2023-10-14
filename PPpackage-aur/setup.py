from setuptools import setup

setup(
    name="PPpackage-aur",
    packages=["PPpackage_aur"],
    version="0.1.0",
    install_requires=["PPpackage-utils"],
    entry_points={"console_scripts": ["PPpackage-aur = PPpackage_aur.main:main"]},
)
