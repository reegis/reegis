# -*- coding: utf-8 -*-

""" This module is designed for the use with the coastdat2 weather data set
of the Helmholtz-Zentrum Geesthacht.

A description of the coastdat2 data set can be found here:
https://www.earth-syst-sci-data.net/6/147/2014/

Copyright (c) 2016-2018 Uwe Krien <uwe.krien@rl-institut.de>

SPDX-License-Identifier: GPL-3.0-or-later
"""
__copyright__ = "Uwe Krien <uwe.krien@rl-institut.de>"
__license__ = "GPLv3"


from nose.tools import eq_, raises, assert_raises_regexp
import os
from reegis import powerplants
from reegis import config as cfg
from reegis import geometries as geo
# import unittest


def test_opsd2reegis():
    path = os.path.join(os.path.dirname(__file__), 'data')
    fn_in = os.path.join(path, 'opsd_test.h5')
    fn_out = os.path.join(path, 'reegis_pp_test.h5')
    powerplants.pp_opsd2reegis(filename_in=fn_in, filename_out=fn_out)
    geo_path = cfg.get('paths', 'geometry')
    geo_file = cfg.get('geometry', 'federalstates_polygon')
    gdf = geo.load(path=geo_path, filename=geo_file)
    fn = str(fn_out.split(os.sep)[-1])
    pp = powerplants.add_regions_to_powerplants(
        gdf, 'fed_states', filename=fn, path=path, dump=False)
    eq_(int(pp.groupby('fed_states').sum().loc['BE', 'capacity']), 2411)
