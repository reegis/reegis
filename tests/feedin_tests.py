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


import os
import pandas as pd

from reegis import coastdat
from reegis import feedin
from reegis import config as cfg


def feedin_wind_sets():
    fn = os.path.join(os.path.dirname(__file__), os.pardir, 'tests',
                      'data', 'test_coastdat_weather.csv')
    wind_parameter_set = feedin.create_windpowerlib_sets()
    weather = pd.read_csv(fn, header=[0, 1])['1126088']
    data_height = cfg.get_dict('coastdat_data_height')
    wind_weather = coastdat.adapt_coastdat_weather_to_windpowerlib(
        weather, data_height)
    s1 = feedin.feedin_wind_sets(wind_weather, wind_parameter_set
                                 ).sum().sort_index()
    s2 = pd.Series({
        'ENERCON_82_hub138_2300': 1673.216046,
        'ENERCON_82_hub78_3000': 1048.678195,
        'ENERCON_82_hub98_2300': 1487.604336})
    pd.testing.assert_series_equal(s1, s2)




# def feedin_windpowerlib(weather, turbine, installed_capacity=1):
#     """Use the windpowerlib to generate normalised feedin time series.
#
#     Parameters
#     ----------
#     turbine : dict
#         Parameters of the wind turbine (hub height, diameter of the rotor,
#         identifier of the turbine to get cp-series, nominal power).
#     weather : pandas.DataFrame
#         Weather data set. See module header.
#     installed_capacity : float
#         Overall installed capacity for the given wind turbine. The installed
#         capacity is set to 1 by default for normalised time series.
#
#     Returns
#     -------
#     pandas.DataFrame
#
#     Examples
#     --------
#     >>> fn = os.path.join(os.path.dirname(__file__), os.pardir, 'tests',
#     ...                  'data', 'test_coastdat_weather.csv')
#     >>> weather = pd.read_csv(fn, header=[0, 1])['1126088']
#     >>> turbine = {
#     ...     'hub_height': 135,
#     ...     'rotor_diameter': 127,
#     ...     'name': 'E-141/4200',
#     ...     'nominal_power': 4200000,
#     ...     'fetch_curve': 'power_coefficient_curve'}
#     >>> data_height = cfg.get_dict('coastdat_data_height')
#     >>> wind_weather = coastdat.adapt_coastdat_weather_to_windpowerlib(
#     ...     weather, data_height)  # doctest: +SKIP
#     >>> int(feedin_windpowerlib(wind_weather, turbine).sum())  # doctest: +SKIP
#     1737