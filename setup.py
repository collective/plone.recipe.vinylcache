# -*- coding: utf-8 -*-
from setuptools import find_packages
from setuptools import setup


# packages/package_dir/namespace_packages are not expressible via
# pyproject.toml's [project] table; everything else lives there.
setup(
    packages=find_packages("src", exclude=["ez_setup"]),
    package_dir={"": "src"},
    namespace_packages=["plone", "plone.recipe"],
)
