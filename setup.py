from setuptools import setup, find_packages

with open("README.md") as f:
    readme = f.read()

setup(
    name="veidemann_soc",
    version="0.1.0",
    description="Summer of code",
    long_description=readme,
    author="Rolv-Arild Braaten",
    author_email="rolv.braaten@nb.no",
    url="https://github.com/nlnwa/soc",
    packages=find_packages(include="norvegica")
)
