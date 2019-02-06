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


from nose.tools import eq_
import os
from reegis import powerplants
from reegis import coastdat
from reegis import opsd
from reegis import config as cfg
from reegis import geometries as geo
# import unittest


def test_opsd2reegis():
    path = os.path.join(os.path.dirname(__file__), 'data')
    cfg.tmp_set('paths', 'opsd', path)
    cfg.tmp_set('paths', 'powerplants', path)
    fn_opsd = opsd.opsd_power_plants()
    fn_reegis = powerplants.pp_opsd2reegis()
    os.remove(fn_opsd)
    filename = str(fn_reegis.split(os.sep)[-1])

    geo_path = cfg.get('paths', 'geometry')
    geo_file = cfg.get('geometry', 'federalstates_polygon')
    gdf = geo.load(path=geo_path, filename=geo_file)
    powerplants.add_regions_to_powerplants(
        gdf, 'fed_states', filename=filename, path=path, dump=True)

    geo_path = cfg.get('paths', 'geometry')
    geo_file = cfg.get('coastdat', 'coastdatgrid_polygon')
    gdf = geo.load(path=geo_path, filename=geo_file)
    pp = powerplants.add_regions_to_powerplants(
        gdf, 'coastdat2', filename=filename, path=path, dump=False)

    os.remove(fn_reegis)
    eq_(int(pp.groupby('fed_states').sum().loc['BE', 'capacity']), 2427)

    year = 2000

    pp = powerplants.get_reegis_powerplants(year, pp=pp)
    eq_(int(pp.groupby('fed_states').sum().loc['BE', 'capacity_2000']), 2391)

    eq_(coastdat.windzone_region_fraction(
        pp, name='fed_states', year=year).round(2).loc['NI', 3], 0.24)
