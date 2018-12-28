#! /usr/bin/env python

from setuptools import setup

setup(name='reegis_tools',
      version='0.0.1',
      author='Uwe Krien',
      author_email='uwe.krien@rl-institut.de',
      description='A local heat and power system',
      package_dir={'reegis_tools': 'reegis_tools'},
      install_requires=['oemof >= 0.1.0',
                        'pandas >= 0.17.0',
                        'demandlib',
                        'tables',
                        'matplotlib',
                        'shapely',
                        'windpowerlib',
                        'pvlib',
                        'tables',
                        'geopandas',
                        'requests',
                        'numpy',
                        'geoplot',
                        'workalendar',
                        'owslib',
                        'pyproj',
                        'pytz',
                        'python-dateutil', 'networkx', 'dill']
      )
