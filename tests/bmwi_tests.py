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
from reegis import config as cfg
from reegis import bmwi


def read_bmwi_sheet_7_test():
    test_path = os.path.join(os.path.dirname(__file__), 'data', 'temp')
    os.makedirs(test_path, exist_ok=True)
    cfg.tmp_set('paths', 'general', test_path)
    eq_(bmwi.bmwi_re_energy_capacity().loc[2016, ('water', 'capacity')], 5601)
    eq_(bmwi.get_annual_electricity_demand_bmwi(2014), 523.988)
    eq_(bmwi.get_annual_electricity_demand_bmwi(1900), None)
    fs = bmwi.read_bmwi_sheet_7('a').sort_index()
    total = int(float(fs.loc[('Industrie', 'gesamt'), 2014]))
    eq_(total, 2545)
    fs = bmwi.read_bmwi_sheet_7('b').sort_index()
    total = int(float(fs.loc[('private Haushalte', 'gesamt'), 2014]))
    eq_(total, 2188)
