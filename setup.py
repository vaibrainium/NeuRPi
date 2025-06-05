"""
NeuRPi: Distributed Neuroscience Experimentation Platform
"""

import os

from setuptools import find_packages, setup


# Read README for long description
def read_readme():
    with open("README.md", encoding="utf-8") as fh:
        return fh.read()


# Read requirements files
def read_requirements(filename):
    with open(os.path.join("requirements", filename)) as f:
        return [line.strip() for line in f if line.strip() and not line.startswith("#")]


setup(
    name="NeuRPi",
    version="0.2.0",
    author="Vaibhav Thakur",
    author_email="vaibhavt459@gmail.com",
    description="Distributed Neuroscience Experimentation Platform",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    url="https://github.com/vaibrainium/NeuRPi",
    packages=find_packages(),
    # packages=find_named_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering :: Bio-Informatics",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.8",
    install_requires=read_requirements("base.txt"),
    extras_require={
        # "dev": read_requirements("dev.txt"),
        # "hardware": read_requirements("hardware.txt"),
        # "cloud": read_requirements("cloud.txt"),
        # "full": (
        #     read_requirements("base.txt")
        #     + read_requirements("gui.txt")
        #     + read_requirements("hardware.txt")
        #     + read_requirements("cloud.txt")
        # ),
    },
    entry_points={
        "console_scripts": [
            "neurpi=neurpi.cli.main:main",
            "neurpi-setup=neurpi.cli.setup:main",
            "neurpi-deploy=neurpi.cli.deploy:main",
        ],
    },
    include_package_data=True,
    package_data={
        "neurpi": [
            "config/*.yaml",
        ],
    },
    keywords="neuroscience, experiment, distributed, raspberry-pi, behavioral-analysis",
)
