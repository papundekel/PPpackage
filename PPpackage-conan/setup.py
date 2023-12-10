from setuptools import setup

setup(
    name="PPpackage-conan",
    packages=["PPpackage_conan"],
    version="0.1.0",
    package_data={"PPpackage_conan": ["data/*"]},
    install_requires=["PPpackage-utils", "Jinja2"],
)
