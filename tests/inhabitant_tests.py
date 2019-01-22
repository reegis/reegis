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
from reegis import inhabitants
from reegis import config as cfg


def inhabitant_tests():
    test_path = os.path.join(os.path.dirname(__file__), 'data', 'temp')
    os.makedirs(test_path, exist_ok=True)
    cfg.tmp_set('paths', 'inhabitants', test_path)
    ew = inhabitants.get_ew_by_federal_states(2014)
    eq_(int(ew.sum()), 81197537)
