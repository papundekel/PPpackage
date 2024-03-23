from setuptools import setup

setup(
    name="PPpackage-AUR",
    packages=["PPpackage_AUR"],
    version="0.1.0",
    package_data={"PPpackage_AUR": ["data/*"]},
    install_requires=[
        "PPpackage-utils",
        "PPpackage-submanager",
        "PPpackage-pacman-utils",
        "sqlitedict",
    ],
)
