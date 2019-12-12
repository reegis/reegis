# -*- coding: utf-8 -*-

""" Tests for the inhabitants module.

SPDX-FileCopyrightText: 2016-2019 Uwe Krien <krien@uni-bremen.de>

SPDX-License-Identifier: MIT
"""
__copyright__="Uwe Krien <krien@uni-bremen.de>"
__license__="MIT"


from nose.tools import eq_, assert_raises_regexp
import os
from reegis import inhabitants, config as cfg, geometries as geo


def inhabitant_tests():
    test_path=os.path.join(os.path.dirname(__file__), 'data', 'temp')
    os.makedirs(test_path, exist_ok=True)
    cfg.tmp_set('paths', 'inhabitants', test_path)
    ew=inhabitants.get_ew_by_federal_states(2014)
    eq_(int(ew.sum()), 81197537)


def test_too_old_year():
    fs=geo.get_federal_states_polygon()
    with assert_raises_regexp(
            Exception, "Years < 2011 are not allowed in this function."):
        inhabitants.get_inhabitants_by_region(2010, fs, 'federal_states')
