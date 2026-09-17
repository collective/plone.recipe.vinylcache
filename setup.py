# -*- coding: utf-8 -*-
from setuptools import find_namespace_packages
from setuptools import setup


# versioning scheme: positions 1-3 match the exact supported Vinyl Cache
# (formerly Varnish Cache) release, currently 9.0.3. Position 4:
# plone.recipe.vinylcache's own patch release number.
version = "9.0.3.0.dev0"

setup(
    name="plone.recipe.vinylcache",
    version=version,
    description="Build and/or configure Vinyl Cache (formerly Varnish Cache) with zc.buildout",
    long_description=(open("README.rst").read() + "\n" + open("CHANGES.rst").read()),
    classifiers=[
        "Framework :: Buildout",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: BSD License",
        "Operating System :: POSIX",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Internet :: Proxy Servers",
        "Development Status :: 4 - Beta",
    ],
    keywords="buildout varnish vinylcache vinyl-cache cache proxy",
    author="Wichert Akkerman, et al",
    author_email="wichert@wiggy.net",
    python_requires=">=3.8",
    url="https://pypi.python.org/pypi/plone.recipe.vinylcache",
    license="BSD",
    packages=find_namespace_packages(include=["plone.*"]),
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        "jinja2>=3.0",
        "setuptools",
        "zc.buildout",
        "zc.recipe.cmmi",
    ],
    extras_require=dict(test=["interlude"]),
    entry_points={
        "zc.buildout": [
            "build = plone.recipe.vinylcache.recipe:BuildRecipe",
            "configuration = plone.recipe.vinylcache.recipe:ConfigureRecipe",
            "script = plone.recipe.vinylcache.recipe:ScriptRecipe",
        ],
    },
)
