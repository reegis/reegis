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


import os
import pandas as pd
import pvlib

from nose.tools import eq_

from windpowerlib.wind_turbine import WindTurbine

from reegis import coastdat
from reegis import feedin
from reegis import config as cfg


def feedin_wind_sets_tests():
    fn = os.path.join(os.path.dirname(__file__), os.pardir, 'tests',
                      'data', 'test_coastdat_weather.csv')
    wind_sets = feedin.create_windpowerlib_sets()
    weather = pd.read_csv(fn, header=[0, 1])['1126088']
    data_height = cfg.get_dict('coastdat_data_height')
    wind_weather = coastdat.adapt_coastdat_weather_to_windpowerlib(
        weather, data_height)
    df = pd.DataFrame()
    for wind_key, wind_set in wind_sets.items():
        df[str(wind_key).replace(' ', '_')] = feedin.feedin_wind_sets(
            wind_weather, wind_set).sum().sort_index()
    s1 = df.transpose()['1']
    s2 = pd.Series({
        'ENERCON_127_hub135_7500': 1277.28988,
        'ENERCON_82_hub138_2300': 1681.47858,
        'ENERCON_82_hub78_3000': 1057.03957,
        'ENERCON_82_hub98_2300': 1496.55769})
    pd.testing.assert_series_equal(s1.sort_index(), s2.sort_index(),
                                   check_names=False)


def feedin_windpowerlib_test():
    fn = os.path.join(os.path.dirname(__file__), os.pardir, 'tests',
                      'data', 'test_coastdat_weather.csv')
    weather = pd.read_csv(fn, header=[0, 1])['1126088']
    turbine = {
        'hub_height': 135,
        'turbine_type': 'E-141/4200'}
    data_height = cfg.get_dict('coastdat_data_height')
    wind_weather = coastdat.adapt_coastdat_weather_to_windpowerlib(
         weather, data_height)  # doctest: +SKIP
    eq_(int(feedin.feedin_windpowerlib(wind_weather, turbine).sum()), 2164)
    turbine = WindTurbine(**turbine)
    eq_(int(feedin.feedin_windpowerlib(wind_weather, turbine).sum()), 2164)


def feedin_pvlib_test():
    fn = os.path.join(os.path.dirname(__file__), os.pardir, 'tests',
                      'data', 'test_coastdat_weather.csv')
    coastdat_id = '1126088'
    weather = pd.read_csv(fn, header=[0, 1], index_col=[0],
                          date_parser=lambda idx: pd.to_datetime(idx, utc=True)
                          )[coastdat_id]
    c = coastdat.fetch_data_coordinates_by_id(coastdat_id)
    location = pvlib.location.Location(**getattr(c, '_asdict')())
    pv_weather = coastdat.adapt_coastdat_weather_to_pvlib(weather, location)

    sandia_modules = pvlib.pvsystem.retrieve_sam('sandiamod')
    sapm_inverters = pvlib.pvsystem.retrieve_sam('sandiainverter')
    pv = {
        'pv_set_name': 'M_LG290G3__I_ABB_MICRO_025_US208',
        'module_name': 'LG_LG290N1C_G3__2013_',
        'module_key': 'LG290G3',
        'inverter_name': 'ABB__MICRO_0_25_I_OUTD_US_208_208V__CEC_2014_',
        'surface_azimuth': 180,
        'surface_tilt': 35,
        'albedo': 0.2}
    pv['module_parameters'] = sandia_modules[pv['module_name']]
    pv['inverter_parameters'] = sapm_inverters[pv['inverter_name']]
    pv['p_peak'] = pv['module_parameters'].Impo * pv['module_parameters'].Vmpo

    eq_(int(feedin.feedin_pvlib(location, pv, pv_weather).sum()), 1025)
    eq_(int(feedin.feedin_pvlib(location, pv, pv_weather).sum()), 1025)


def feedin_pv_sets_tests():
    fn = os.path.join(os.path.dirname(__file__), os.pardir, 'tests',
                      'data', 'test_coastdat_weather.csv')
    pv_sets = feedin.create_pvlib_sets()
    coastdat_id = '1126088'
    weather = pd.read_csv(fn, header=[0, 1], index_col=[0],
                          date_parser=lambda idx: pd.to_datetime(idx, utc=True)
                          )[coastdat_id]
    c = coastdat.fetch_data_coordinates_by_id(coastdat_id)
    location = pvlib.location.Location(**getattr(c, '_asdict')())
    pv_weather = coastdat.adapt_coastdat_weather_to_pvlib(weather, location)
    s1 = pd.Series()
    for pv_key, pv_set in pv_sets.items():
        s1[pv_key] = int((
            feedin.feedin_pv_sets(pv_weather, location, pv_set).sum().mean()))
    s2 = pd.Series({
        'M_STP280S__I_GEPVb_5000_NA_240': 798,
        'M_BP2150S__I_P235HV_240': 722,
        'M_SF160S___I_ABB_MICRO_025_US208': 801,
        'M_LG290G3__I_ABB_MICRO_025_US208': 817})
    pd.testing.assert_series_equal(s1.sort_index(), s2.sort_index())
