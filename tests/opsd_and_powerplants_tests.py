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
import os
from shutil import rmtree
from reegis import (powerplants, geometries as geo, coastdat, opsd,
                    config as cfg)


# import unittest


def test_01_opsd2reegis():
    path = os.path.join(os.path.dirname(__file__), 'data')
    cfg.tmp_set('paths_pattern', 'opsd', path)
    cfg.tmp_set('paths', 'powerplants', path)
    fn_opsd = opsd.opsd_power_plants()
    fn_reegis = powerplants.pp_opsd2reegis()
    os.remove(fn_opsd)
    filename = str(fn_reegis.split(os.sep)[-1])

    gdf1 = geo.get_federal_states_polygon()
    powerplants.add_regions_to_powerplants(
        gdf1, 'fed_states', filename=filename, path=path, dump=True)

    geo_path = cfg.get('paths', 'geometry')
    geo_file = cfg.get('coastdat', 'coastdatgrid_polygon')
    gdf2 = geo.load(path=geo_path, filename=geo_file)
    pp = powerplants.add_regions_to_powerplants(
        gdf2, 'coastdat2', filename=filename, path=path, dump=False)

    year = 2014
    pp2 = powerplants.get_powerplants_by_region(gdf1, year, 'my_states')

    pp2['efficiency_{0}'.format(year)] = pp2['capacity_{0}'.format(year)].div(
        pp2['capacity_in_{0}'.format(year)])

    pp2.drop(['capacity', 'capacity_in', 'thermal_capacity'],
             axis=1, inplace=True)

    fn_reegis2 = fn_reegis.replace('.h5', '_my_states.h5')
    os.remove(fn_reegis2)
    os.remove(fn_reegis)
    rmtree(os.path.join(path, 'messages'))

    eq_(int(pp.groupby('fed_states').sum().loc['BE', 'capacity']), 2427)

    eq_(round(pp2.loc[('BE', 'Hard coal'), 'efficiency_2014'], 3), 0.386)

    year = 2000

    pp = powerplants.get_reegis_powerplants(year, pp=pp)
    eq_(int(pp.groupby('fed_states').sum().loc['BE', 'capacity_2000']), 2391)

    eq_(coastdat.windzone_region_fraction(
        pp, name='fed_states', year=year).round(2).loc['NI', 3], 0.24)


def test_99_read_conv_pp():
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
    print(df.columns)
    eq_(int(df['capacity_net_bnetza'].sum()), 118684)
