# -*- coding: utf-8 -*-

""" This module is designed for the use with the coastdat2 weather data set
of the Helmholtz-Zentrum Geesthacht.

A description of the coastdat2 data set can be found here:
https://www.earth-syst-sci-data.net/6/147/2014/

Copyright (c) 2016-2018 Uwe Krien <uwe.krien@rl-institut.de>

SPDX-License-Identifier: MIT
"""
__copyright__ = "Uwe Krien <uwe.krien@rl-institut.de>"
__license__ = "MIT"

from nose.tools import eq_
import os
from reegis import openego
from reegis import geometries
from reegis import config as cfg
from reegis import demand_elec


def test_ego_demand_and_download():
    cfg.tmp_set('open_ego', 'ego_load_areas', 'ego_load_areas_db_test.csv')
    openego.get_ego_data(query='?where=un_id<10')
    cfg.tmp_set('open_ego', 'ego_load_areas', 'ego_load_areas_test.csv')
    cfg.tmp_set('open_ego', 'osf_url', 'https://osf.io/w9pv6/download')
    load = openego.get_ego_data(osf=True)
    eq_(int(load['consumption'].sum()), 31726)
    filename = 'oep_ego_demand_combined_test.h5'
    path = cfg.get('paths', 'demand')
    fn = os.path.join(path, filename)
    load.to_hdf(fn, 'demand')
    geo = geometries.get_federal_states_polygon()
    region_demand = openego.get_ego_demand_by_region(
        geo, 'test', infile=fn).groupby('test').sum()
    eq_(int(region_demand.loc['BB', 'consumption']), 279)
    eq_(int(region_demand.loc['BY', 'consumption']), 7290)
    d1 = demand_elec.get_entsoe_profile_by_region(geo, 2014, 'test')
    eq_(int(d1.sum().sum()), 519757349)
    d2 = demand_elec.get_entsoe_profile_by_region(geo, 2014, 'test', 'bmwi')
    eq_(int(d2.sum().sum()), 523)
    d3 = demand_elec.get_entsoe_profile_by_region(geo, 2014, 'test', 200)
    eq_(round(d3.sum().sum()), 200.0)
