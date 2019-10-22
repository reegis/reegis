# -*- coding: utf-8 -*-

"""
Tests for the openego module.

Copyright (c) 2016-2019 Uwe Krien <krien@uni-bremen.de>

SPDX-License-Identifier: MIT
"""
__copyright__ = "Uwe Krien <krien@uni-bremen.de>"
__license__ = "MIT"

from nose.tools import eq_
import os
from reegis import openego, demand_elec, geometries, config as cfg


class TestEgoEntsoeDemandAndDownload:
    @classmethod
    def setUpClass(cls):
        cfg.tmp_set('open_ego', 'ego_load_areas', 'ego_load_areas_db_test.csv')
        openego.get_ego_data(query='?where=un_id<10')
        cfg.tmp_set('open_ego', 'ego_load_areas', 'ego_load_areas_test.csv')
        cfg.tmp_set('open_ego', 'osf_url', 'https://osf.io/w9pv6/download')
        cls.load = openego.get_ego_data(osf=True)
        cls.geo = geometries.get_federal_states_polygon()
        filename = 'oep_ego_demand_combined_test.h5'
        path = cfg.get('paths', 'demand')
        cls.fn = os.path.join(path, filename)
        cls.load.to_hdf(cls.fn, 'demand')

    def test_basic_file(self):
        eq_(int(self.load['consumption'].sum()), 31726)

    def test_demand_by_region(self):
        region_demand = openego.get_ego_demand_by_region(
            self.geo, 'test', infile=self.fn).groupby('test').sum()
        eq_(int(region_demand.loc['BB', 'consumption']), 279)
        eq_(int(region_demand.loc['BY', 'consumption']), 7290)

    def test_profile_by_region_without_annual_values(self):
        d1 = demand_elec.get_entsoe_profile_by_region(self.geo, 2014, 'test')
        eq_(int(d1.sum().sum()), 519757349)
        d1 = demand_elec.get_entsoe_profile_by_region(self.geo, 2012, 'test')
        eq_(int(d1.sum().sum()), 516020478)

    def test_profile_by_region_with_annual_values(self):
        d2 = demand_elec.get_entsoe_profile_by_region(
            self.geo, 2013, 'test', 'bmwi')
        eq_(int(d2.sum().sum()), 535)
        d3 = demand_elec.get_entsoe_profile_by_region(
            self.geo, 2011, 'test', 200)
        eq_(round(d3.sum().sum()), 200.0)
