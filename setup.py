#! /usr/bin/env python

"""Setup module of reegis."""

from setuptools import setup, find_packages
import os
import reegis

github = "@https://github.com/"
if not os.environ.get("READTHEDOCS") == "True":
    requirements = [
        "pandas",
        "demandlib",
        "tables",
        "shapely",
        "pvlib",
        "geopandas",
        "requests",
        "numpy",
        "workalendar",
        "pyproj",
        "pytz",
        "windpowerlib",
        "python-dateutil",
        "Rtree",
        "xlrd",
        "xlwt",
    ]
else:
    requirements = ["cycler"]


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


setup(
    name="reegis",
    version="0.2.1",
    author="Uwe Krien",
    author_email="krien@uni-bremen.de",
    description="Open geospatial data model",
    long_description=read("README.rst"),
    long_description_content_type="text/x-rst",
    package_dir={"reegis": "reegis"},
    url="https://github.com/reegis/reegis",
    packages=find_packages(),
    install_requires=requirements,
    license="MIT",
    python_requires=">=3.6",
    extras_require={
        "dev": [
            "nose",
            "cython",
            "sphinx",
            "sphinx_rtd_theme",
            "matplotlib",
            "descartes",
            "request",
        ]
    },
    package_data={
        "reegis": [
            os.path.join("data", "static", "*.csv"),
            os.path.join("data", "static", "*.txt"),
            os.path.join("data", "geometries", "*.csv"),
            os.path.join("data", "geometries", "*.geojson"),
            "*.ini",
        ]
    },
)
