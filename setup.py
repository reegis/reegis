#! /usr/bin/env python

"""Setup module of reegis."""

from setuptools import setup, find_packages
import os
import reegis

github = "@https://github.com/"
if not os.environ.get("READTHEDOCS") == "True":
    requirements = [
        "pandas == 1.1.4",
        "demandlib{0}oemof/demandlib/archive/v0.1.7b1.zip".format(github),
        "tables == 3.6.1",
        "shapely == 1.7.1",
        "pvlib == 0.8.0",
        "geopandas == 0.8.1",
        "requests == 2.25",
        "numpy == 1.19.4",
        "workalendar == 13.0.0",
        "pyproj == 3.0.0.post1",
        "pytz == 2020.4",
        "windpowerlib{0}wind-python/windpowerlib/archive/v0.2.1b1.zip".format(
            github
        ),
        "python-dateutil == 2.8.1",
        "Rtree == 0.9.4",
        "xlrd == 1.2.0",
        "xlwt == 1.3.0",
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
