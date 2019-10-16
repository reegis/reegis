# -*- coding: utf-8 -*-

""" Tests for the inhabitants module.

Copyright (c) 2016-2019 Uwe Krien <krien@uni-bremen.de>

SPDX-License-Identifier: MIT
"""
__copyright__ = "Uwe Krien <krien@uni-bremen.de>"
__license__ = "MIT"


from nose.tools import eq_
import os
from reegis import inhabitants, config as cfg


def inhabitant_tests():
    test_path = os.path.join(os.path.dirname(__file__), 'data', 'temp')
    os.makedirs(test_path, exist_ok=True)
    cfg.tmp_set('paths', 'inhabitants', test_path)
    ew = inhabitants.get_ew_by_federal_states(2014)
    eq_(int(ew.sum()), 81197537)
