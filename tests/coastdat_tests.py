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
from reegis import coastdat
import unittest


@unittest.skip("URL test is very slow. Use it from time to time.")
def test_coastdat_file_url():
    check = True
    for year in range(1998, 2015):
        f1 = 'coastDat2_de_{0}.h5'.format(year)
        f2 = coastdat.download_coastdat_data(year=year, test_only=True)
        if f1 != f2:
            check = year
    eq_(check, True)
