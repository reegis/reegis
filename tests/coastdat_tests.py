# -*- coding: utf-8 -*-

""" This module is designed for the use with the coastdat2 weather data set
of the Helmholtz-Zentrum Geesthacht.

A description of the coastdat2 data set can be found here:
https://www.earth-syst-sci-data.net/6/147/2014/

SPDX-FileCopyrightText: 2016-2019 Uwe Krien <krien@uni-bremen.de>

SPDX-License-Identifier: MIT
"""
__copyright__="Uwe Krien <krien@uni-bremen.de>"
__license__="MIT"


from nose.tools import eq_, assert_raises_regexp
from reegis import coastdat
import unittest


@unittest.skip("URL test is very slow. Use it from time to time.")
def test_coastdat_file_url():
    check=True
    for year in range(1998, 2015):
        f1='coastDat2_de_{0}.h5'.format(year)
        f2=coastdat.download_coastdat_data(year=year, test_only=True)
        if f1 != f2:
            check=year
    eq_(check, True)


def test_coastdat_file_url_2014():
    """
    It takes a long time to test all links, so one link is tested all the
    time to test the general infrastructure, and all links will be tested
    from time to time by removing the skip decorator.
    """
    check=True
    for year in [2014]:
        f1='coastDat2_de_{0}.h5'.format(year)
        f2=coastdat.download_coastdat_data(year=year, test_only=True)
        if f1 != f2:
            check=year
    eq_(check, True)


def test_wrong_url():
    assert_raises_regexp(ValueError, "No URL found",
                         coastdat.download_coastdat_data, year=2018)
    assert_raises_regexp(ValueError, "URL not valid",
                         coastdat.download_coastdat_data,
                         url='https://osf.io/url_id/download')


def test_coordinates_out_of_bound():
    eq_(coastdat.fetch_id_by_coordinates(0, 0), None)
