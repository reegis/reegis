# -*- coding: utf-8 -*-

""" Tests for the energy balance module

Copyright (c) 2016-2019 Uwe Krien <krien@uni-bremen.de>

SPDX-License-Identifier: MIT
"""
__copyright__ = "Uwe Krien <krien@uni-bremen.de>"
__license__ = "MIT"


from nose.tools import eq_, assert_raises_regexp
import os
import pandas as pd
from reegis import energy_balance
from geopandas.geodataframe import GeoDataFrame


def test_usage_balance_fix():
    for year in [2012, 2013, 2014]:
        cb = energy_balance.get_usage_balance(year)
        energy_balance.fix_usage_balance(cb, year)
    year = 2011
    cb = energy_balance.get_usage_balance(year)
    with assert_raises_regexp(ValueError,
                              "You cannot edit the balance for year 2011."):
        energy_balance.fix_usage_balance(cb, year)
