"""Install packages as defined in this file into the Python environment."""
from setuptools import setup, find_namespace_packages
import ps2mqtt


setup(
    name="ps2mqtt",
    author="Diogo Gomes",
    author_email="diogogomes@gmail.com",
    url="https://github.com/dgomes/ps2mqtt",
    description="Daemon that pushes psutil information to mqtt broker",
    version=ps2mqtt.__version__,
    packages=['ps2mqtt'],
    install_requires=[
        "setuptools==45.0",
        "paho-mqtt>=1.6.1",
        "python-slugify>=6.1.1",
        "psutil==5.9.0",
        "PyYAML==6.0"
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
