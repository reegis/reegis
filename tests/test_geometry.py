# -*- coding: utf-8 -*-

""" Tests for the geometry module

Copyright (c) 2016-2019 Uwe Krien <krien@uni-bremen.de>

SPDX-License-Identifier: MIT
"""
__copyright__ = "Uwe Krien <krien@uni-bremen.de>"
__license__ = "MIT"


from nose.tools import eq_, ok_, assert_raises_regexp
import os
import pandas as pd
from reegis import geometries
from geopandas.geodataframe import GeoDataFrame


def test_load_hdf():
    path = os.path.join(os.path.dirname(__file__), 'data')
    filename = 'germany_with_awz.h5'
    gdf = geometries.load(path, filename)
    ok_(isinstance(gdf, GeoDataFrame))


def test_load_csv():
    path = os.path.join(os.path.dirname(__file__), 'data')
    filename = 'germany_with_awz.csv'
    gdf = geometries.load(path, filename)
    ok_(isinstance(gdf, GeoDataFrame))


def test_load_wrong_csv():
    path = os.path.join(os.path.dirname(__file__), 'data')
    filename = 'csv_without_geometry.csv'
    with assert_raises_regexp(
            ValueError, 'Could not create GeoDataFrame. Missing geometries.'):
        gdf = geometries.load(path, filename)


def test_load_error():
    path = os.path.join(os.path.dirname(__file__), 'data')
    filename = 'germany_with_awz.tiff'
    with assert_raises_regexp(ValueError,
                              "Cannot load file with a 'tiff' extension."):
        geometries.load(path, filename)


def test_creation_of_gdf():
    path = os.path.join(os.path.dirname(__file__), 'data')
    filename = 'germany_with_awz.csv'
    fn = os.path.join(path, filename)
    df = pd.read_csv(fn, index_col=[0])
    with assert_raises_regexp(ValueError,
                              'Cannot find column for longitude: lon'):
        geometries.create_geo_df(df, lon_column='lon')
    with assert_raises_regexp(ValueError,
                              'Cannot find column for latitude: lon'):
        geometries.create_geo_df(df, lat_column='lon')
    gdf = geometries.create_geo_df(df, wkt_column='geometry')
    ok_(isinstance(gdf, GeoDataFrame))
