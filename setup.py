"""Install packages as defined in this file into the Python environment."""
from setuptools import setup, find_namespace_packages
import ps2mqtt

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="ps2mqtt",
    version=ps2mqtt.__version__,
    author="Diogo Gomes",
    author_email="diogogomes@gmail.com",
    url="https://github.com/dgomes/ps2mqtt",
    description="Python daemon that gets information from psutil to an mqtt broker for integration with Home Assistant.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=["ps2mqtt"],
    install_requires=[
        "setuptools==45.0",
        "paho-mqtt>=1.6.1",
        "python-slugify>=6.1.1",
        "psutil==5.9.0",
        "PyYAML==6.0",
    ],
    entry_points={
        "console_scripts": [
            "ps2mqtt=ps2mqtt.daemon:main",
        ]
    },
    classifiers=[
        "Programming Language :: Python :: 3.0",
        "Topic :: Utilities",
        "Environment :: No Input/Output (Daemon)",
        "Operating System :: POSIX",
        "Intended Audience :: System Administrators",
    ],
)
