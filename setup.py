#! /usr/bin/env python

from setuptools import setup

setup(name='reegis',
      version='0.0.1',
      author='Uwe Krien',
      author_email='uwe.krien@posteo.eu',
      description='Open geospatial data model',
      package_dir={'reegis': 'reegis'},
      install_requires=['oemof >= 0.1.0',
                        'pandas >= 0.17.0',
                        'demandlib',
                        'tables',
                        'matplotlib',
                        'shapely',
                        'windpowerlib',
                        'pvlib',
                        'geopandas',
                        'requests',
                        'numpy',
                        'geoplot',
                        'workalendar',
                        'owslib',
                        'pyproj',
                        'pytz',
                        'python-dateutil',
		        'networkx',
			'dill']
      )
