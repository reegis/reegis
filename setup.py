#! /usr/bin/env python

"""Setup module of reegis."""

from setuptools import setup
import os
import reegis

if not os.environ.get('READTHEDOCS') == 'True':
    requirements = [
        'pandas >= 0.21.0, < 0.25',
        'demandlib',
        'tables',
        'shapely',
        'pvlib < 0.7',
        'geopandas < 0.5',
        'requests',
        'numpy < 1.16',
        'workalendar',
        'pyproj',
        'pytz',
        'windpowerlib < 0.3',
        'python-dateutil',
        'cython',
        'Rtree']
else:
    requirements = ['cycler']


setup(name='reegis',
      version=reegis.__version__,
      author='Uwe Krien',
      author_email='krien@uni-bremen.de',
      description='Open geospatial data model',
      package_dir={'reegis': 'reegis'},
      install_requires=requirements)
