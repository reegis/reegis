# -*- coding: utf-8 -*-

"""
Tests for the openego module.

SPDX-FileCopyrightText: 2016-2019 Uwe Krien <krien@uni-bremen.de>

SPDX-License-Identifier: MIT
"""
__copyright__ = "Uwe Krien <krien@uni-bremen.de>"
__license__ = "MIT"

from nose.tools import eq_, assert_raises_regexp
import os
import warnings
from reegis import openego, demand_elec, geometries, config as cfg

warnings.filterwarnings("ignore", category=UserWarning)


class TestEgoEntsoeDemandAndDownload:
    @classmethod
    def setUpClass(cls):
        cfg.tmp_set("open_ego", "ego_load_areas", "ego_load_areas_db_test.csv")
        openego.get_ego_data(osf=False, query="?where=un_id<10")
        cfg.tmp_set("open_ego", "ego_load_areas", "ego_load_areas_test.csv")
        cfg.tmp_set("open_ego", "osf_url", "https://osf.io/w9pv6/download")
        cfg.tmp_set("open_ego", "ego_file", "oep_ego_demand_combined_test1.h5")
        cls.load = openego.get_ego_data()
        cls.geo = geometries.get_federal_states_polygon()
        filename = "oep_ego_demand_combined_test.h5"
        path = cfg.get("paths", "demand")
        cls.fn = os.path.join(path, filename)
        cls.load.to_hdf(cls.fn, "demand")

    def test_basic_file(self):
        eq_(int(self.load["consumption"].sum()), 31726)

    def test_demand_by_region(self):
        region_demand = (
            openego.get_ego_demand_by_region(self.geo, "test", infile=self.fn)
            .groupby("test")
            .sum()
        )
        eq_(int(region_demand.loc["BB", "consumption"]), 279)
        eq_(int(region_demand.loc["BY", "consumption"]), 7290)

    def test_profile_by_region_with_entsoe_annual_values(self):
        d1 = demand_elec.get_entsoe_profile_by_region(
            self.geo, 2014, "test", "entsoe"
        )
        eq_(int(d1.sum().sum()), 519752444)

    def test_profile_by_region_with_bmwi_annual_values(self):
        d2 = demand_elec.get_entsoe_profile_by_region(
            self.geo, 2013, "test", "bmwi"
        )
        eq_(int(d2.sum().sum()), 535684999)

    def test_profile_by_region_with_openego_annual_values(self):
        d3 = demand_elec.get_entsoe_profile_by_region(
            self.geo, 2013, "test", "openego"
        )
        eq_(int(d3.sum().sum()), 31726254)

    def test_profile_by_region_with_user_annual_values(self):
        d4 = demand_elec.get_entsoe_profile_by_region(
            self.geo, 2011, "test", 200
        )
        eq_(int(round(d4.sum().sum(), 0)), 200)

    def test_profile_by_region_with_wrong_annual_values(self):
        msg = (
            "200 of type <class 'str'> is not a valid input for "
            "'annual_demand'"
        )
        with assert_raises_regexp(ValueError, msg):
            demand_elec.get_entsoe_profile_by_region(
                self.geo, 2011, "test", "200"
            )
