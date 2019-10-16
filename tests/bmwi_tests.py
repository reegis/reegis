# -*- coding: utf-8 -*-

"""
Tests for the bmwi module.

Copyright (c) 2016-2019 Uwe Krien <krien@uni-bremen.de>

SPDX-License-Identifier: MIT
"""
__copyright__ = "Uwe Krien <krien@uni-bremen.de>"
__license__ = "MIT"


from nose.tools import eq_, assert_raises_regexp
import os
from reegis import config as cfg
from reegis import bmwi


def read_bmwi_sheet_7_test():
    test_path = os.path.join(os.path.dirname(__file__), 'data', 'temp')
    os.makedirs(test_path, exist_ok=True)
    cfg.tmp_set('paths', 'general', test_path)
    eq_(bmwi.bmwi_re_energy_capacity().loc[2016, ('water', 'capacity')], 5598)
    eq_(bmwi.get_annual_electricity_demand_bmwi(2014), 523.988)
    fs = bmwi.read_bmwi_sheet_7('a').sort_index()
    total = int(float(fs.loc[('Industrie', 'gesamt'), 2014]))
    eq_(total, 2545)
    fs = bmwi.read_bmwi_sheet_7('b').sort_index()
    total = int(float(fs.loc[('private Haushalte', 'gesamt'), 2014]))
    eq_(total, 2188)
    assert_raises_regexp(ValueError, "No BMWi electricity demand found",
                         bmwi.get_annual_electricity_demand_bmwi, year=1900)
