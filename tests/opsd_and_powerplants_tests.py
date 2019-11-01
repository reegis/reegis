# -*- coding: utf-8 -*-

""" This module is designed for the use with the coastdat2 weather data set
of the Helmholtz-Zentrum Geesthacht.

A description of the coastdat2 data set can be found here:
https://www.earth-syst-sci-data.net/6/147/2014/

Copyright (c) 2016-2019 Uwe Krien <krien@uni-bremen.de>

SPDX-License-Identifier: MIT
"""
__copyright__ = "Uwe Krien <krien@uni-bremen.de>"
__license__ = "MIT"


from nose.tools import ok_, eq_, assert_raises_regexp
from unittest.mock import MagicMock
import os
from shutil import rmtree, copyfile
from reegis import (powerplants, geometries as geo, coastdat, opsd,
                    config as cfg)


class TestOpsd2reegis:

    @classmethod
    def setUpClass(cls):
        path = os.path.join(os.path.dirname(__file__), 'data')
        cfg.tmp_set('paths_pattern', 'opsd', path)
        cfg.tmp_set('paths', 'powerplants', path)
        fn_opsd = opsd.opsd_power_plants()
        os.remove(fn_opsd)
        fn_opsd = os.path.join(
            cfg.get('paths_pattern', 'opsd'), cfg.get('opsd', 'opsd_prepared'))
        fn_test = fn_opsd.replace('.h5', '_test.h5')
        copyfile(fn_test, fn_opsd)
        fn_reegis = powerplants.pp_opsd2reegis()
        os.remove(fn_opsd)
        filename = str(fn_reegis.split(os.sep)[-1])

        cls.gdf1 = geo.get_federal_states_polygon()
        powerplants.add_regions_to_powerplants(
            cls.gdf1, 'fed_states', filename=filename, path=path, dump=True)

        geo_path = cfg.get('paths', 'geometry')
        geo_file = cfg.get('coastdat', 'coastdatgrid_polygon')
        gdf2 = geo.load(path=geo_path, filename=geo_file)
        cls.pp = powerplants.add_regions_to_powerplants(
            gdf2, 'coastdat2', filename=filename, path=path, dump=False)

        year = 2014
        cls.pp2 = powerplants.get_powerplants_by_region(
            cls.gdf1, year, 'my_states')

        cls.pp2['efficiency_{0}'.format(year)] = (
            cls.pp2['capacity_{0}'.format(year)].div(
                cls.pp2['capacity_in_{0}'.format(year)]))

        cls.pp2.drop(['capacity', 'capacity_in', 'thermal_capacity'],
                     axis=1, inplace=True)

        fn_reegis2 = fn_reegis.replace('.h5', '_my_states.h5')
        os.remove(fn_reegis2)
        os.remove(fn_reegis)
        rmtree(os.path.join(path, 'messages'))

    def test_001(self):
        eq_(int(self.pp.groupby('fed_states').sum().loc['BE', 'capacity']),
            2427)

        eq_(round(
            self.pp2.loc[('BE', 'Hard coal'), 'efficiency_2014'], 3),
            0.386)

    def test_002(self):
        year = 2000

        pp = powerplants.get_reegis_powerplants(year, pp=self.pp)
        eq_(int(pp.groupby('fed_states').sum().loc['BE', 'capacity_2000']),
            2391)

        eq_(coastdat.windzone_region_fraction(
            pp, name='fed_states', year=year).round(2).loc['NI', 3], 0.24)

    def test_003(self):
        pp = powerplants.get_reegis_powerplants(
            2001, pp=self.pp, overwrite_capacity=True)
        eq_(int(pp.groupby('fed_states').sum().loc['BE', 'capacity_2000']),
            2391)

    def test_004(self):
        opsd.opsd_power_plants = MagicMock(return_value='/home/pet/pp.h5')
        with assert_raises_regexp(Exception,
                                  "File /home/pet/pp.h5 does not exist"):
            powerplants.add_regions_to_powerplants(self.gdf1, 'fed_states')
        with assert_raises_regexp(Exception,
                                  "File /home/pet/pp.h5 does not exist"):
            powerplants.get_reegis_powerplants(2013)


def test_read_conv_pp():
    my_dir = os.path.join(os.path.expanduser('~'), 'reegis_opsd_test')
    os.makedirs(my_dir, exist_ok=True)
    cfg.tmp_set('paths_pattern', 'opsd', my_dir)
    cfg.tmp_set('paths', 'powerplants', my_dir)
    with assert_raises_regexp(ValueError, "Category 'conv' is not valid."):
        opsd.load_original_opsd_file('conv', True)
    df = opsd.load_original_opsd_file('conventional', True)
    for f in ['conventional_readme.md', 'conventional_datapackage.json',
              'conventional_power_plants_DE.csv']:
        ok_(os.path.isfile(os.path.join(my_dir, f)))
    rmtree(my_dir)
    eq_(int(df['capacity_net_bnetza'].sum()), 118684)
