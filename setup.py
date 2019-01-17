#! /usr/bin/env python

from setuptools import setup
import os

if not os.environ.get('READTHEDOCS') == 'True':
    requirements = [
        'oemof >= 0.2.1',
        'pandas >= 0.17.0',
        'demandlib',
        'tables',
        'matplotlib',
        'shapely',
        'windpowerlib',
        'pvlib==v0.6.1-beta',
        'geopandas',
        'requests',
        'numpy',
        'workalendar',
        'owslib',
        'pyproj',
        'pytz',
        'python-dateutil',
        'networkx',
        'dill',
        'PyQt5',
        'cython']
else:
    requirements = ['pvlib', 'oemof']


setup(name='reegis',
      version='0.0.1',
      author='Uwe Krien',
      author_email='uwe.krien@posteo.eu',
      description='Open geospatial data model',
      package_dir={'reegis': 'reegis'},
      install_requires=requirements)
