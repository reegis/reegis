#! /usr/bin/env python

"""Setup module of reegis."""

from setuptools import setup, find_packages
import os
import reegis

github = "@https://github.com/"
if not os.environ.get("READTHEDOCS") == "True":
    requirements = [
        "pandas",
        "demandlib{0}oemof/demandlib/archive/v0.1.7b1.zip".format(github),
        "tables",
        "shapely",
        "pvlib",
        "geopandas",
        "requests",
        "numpy",
        "workalendar",
        "pyproj",
        "pytz",
        "windpowerlib{0}wind-python/windpowerlib/archive/v0.2.1b1.zip".format(
            github
        ),
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
    version=reegis.__version__,
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
