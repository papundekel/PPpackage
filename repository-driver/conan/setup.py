from setuptools import setup

setup(
    name="PPpackage-repository-driver-conan",
    packages=["PPpackage.repository_driver.conan"],
    version="0.1.0",
    package_data={"PPpackage.repository_driver.conan": ["data/*"]},
    install_requires=["PPpackage-utils"],
)
