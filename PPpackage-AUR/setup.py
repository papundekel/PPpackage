from setuptools import setup

setup(
    name="PPpackage-AUR",
    packages=["PPpackage_AUR"],
    version="0.1.0",
    install_requires=["PPpackage-utils", "PPpackage-submanager", "sqlitedict"],
)
