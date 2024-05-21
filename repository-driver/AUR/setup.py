from setuptools import setup

setup(
    name="PPpackage-repository-driver-AUR",
    packages=["PPpackage.repository_driver.AUR"],
    version="0.1.0",
    install_requires=[
        "PPpackage-repository-driver-interface",
        "PPpackage-utils-async",
        "PPpackage-utils-json",
        "PPpackage-utils-file",
        "httpx[http2]",
        "hishel[sqlite]",
        "aiosqlite",
    ],
)
