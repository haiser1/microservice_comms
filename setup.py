from setuptools import find_packages, setup

setup(
    name="microservice_comms",
    version="0.2.1",
    author="Markus Ganteng dan Intelek",
    author_email="markus.rabin.r@gmail.com",
    description="A shared library for internal microservice communication.",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/haiser1/microservice_comms",
    packages=find_packages(),
    install_requires=[
        "requests>=2.20.0",
        "pybreaker>=0.6.0",
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
)
