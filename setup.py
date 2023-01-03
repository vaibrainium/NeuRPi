from setuptools import find_namespace_packages, find_packages, setup

with open("requirements.txt") as f:
    required = f.read().splitlines()

setup(
    name="NeuRPi",
    author="Vaibhav Thakur (vaibrainium)",
    install_requires=required,
    packages=find_namespace_packages(),
    # packages=find_packages(),
)
