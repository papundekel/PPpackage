from setuptools import setup

setup(
    name="PPpackage-repository-driver-AUR",
    packages=["PPpackage.repository_driver.AUR"],
    version="0.1.0",
    install_requires=[
        "PPpackage-utils",
        "PPpackage-repository-driver-interface",
        "sqlitedict",
        "httpx[http2]",
        "hishel[sqlite]",
    ],
)
