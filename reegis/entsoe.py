# -*- coding: utf-8 -*-

# -*- coding: utf-8 -*-

""" Download and prepare entsoe load profile from opsd data portal.

Copyright (c) 2016-2019 Uwe Krien <krien@uni-bremen.de>

SPDX-License-Identifier: MIT
"""
__copyright__ = "Uwe Krien <krien@uni-bremen.de>"
__license__ = "MIT"


# Python libraries
import os
import logging
import datetime
from collections import namedtuple

# internal modules
from reegis import config as cfg

# External packages
import pandas as pd
import requests
import pytz
import dateutil


def read_original_timeseries_file(orig_csv_file=None, overwrite=False):
    """Read timeseries file if it exists. Otherwise download it from opsd.
    """
    version = cfg.get('entsoe', 'timeseries_version')

    if orig_csv_file is None:
        orig_csv_file = os.path.join(
            cfg.get('paths', 'entsoe'),
            cfg.get('entsoe', 'original_file')).format(version=version)
    readme = os.path.join(
        cfg.get('paths', 'entsoe'),
        cfg.get('entsoe', 'readme_file')).format(version=version)
    json = os.path.join(
        cfg.get('paths', 'entsoe'),
        cfg.get('entsoe', 'json_file')).format(version=version)

    version = cfg.get('entsoe', 'timeseries_version')

    if not os.path.isfile(orig_csv_file) or overwrite:
        req = requests.get(
            cfg.get('entsoe', 'timeseries_data').format(version=version))

        if not overwrite:
            logging.warning("File not found. Try to download it from server.")
        else:
            logging.warning("Will download file from server and overwrite"
                            "existing ones")
        logging.warning("Check URL if download does not work.")
        with open(orig_csv_file, 'wb') as fout:
            fout.write(req.content)
        logging.warning("Downloaded from {0} and copied to '{1}'.".format(
            cfg.get('entsoe', 'timeseries_data').format(version=version),
            orig_csv_file))
        req = requests.get(
            cfg.get('entsoe', 'timeseries_readme').format(version=version))
        with open(readme, 'wb') as fout:
            fout.write(req.content)
        req = requests.get(
            cfg.get('entsoe', 'timeseries_json').format(version=version))
        with open(json, 'wb') as fout:
            fout.write(req.content)
    logging.debug("Reading file: {0}".format(orig_csv_file))
    orig = pd.read_csv(orig_csv_file, index_col=[0], parse_dates=True)
    orig = orig.tz_convert('Europe/Berlin')
    return orig


def prepare_de_file(filename=None, overwrite=False):
    """Convert demand file. CET index and Germany's load only."""
    version = cfg.get('entsoe', 'timeseries_version')
    if filename is None:
        filename = os.path.join(
            cfg.get('paths', 'entsoe'),
            cfg.get('entsoe', 'de_file').format(version=version))
    if not os.path.isfile(filename) or overwrite:
        ts = read_original_timeseries_file(overwrite=overwrite)
        for col in ts.columns:
            if 'DE' not in col:
                ts.drop(col, 1, inplace=True)

        ts.to_csv(filename)


def split_timeseries_file(filename=None, overwrite=False):
    """Split table into load and renewables."""
    entsoe_ts = namedtuple('entsoe', ['load', 'renewables'])
    logging.info("Splitting time series.")
    version = cfg.get('entsoe', 'timeseries_version')
    path_pattern = os.path.join(cfg.get('paths', 'entsoe'), '{0}')
    if filename is None:
        filename = path_pattern.format(cfg.get('entsoe', 'de_file').format(
            version=version))

    if not os.path.isfile(filename) or overwrite:
        prepare_de_file(filename, overwrite)

    de_ts = pd.read_csv(filename, index_col='utc_timestamp',
                        parse_dates=True, date_parser=dateutil.parser.parse)

    berlin = pytz.timezone('Europe/Berlin')
    end_date = berlin.localize(datetime.datetime(2015, 1, 1, 0, 0, 0))

    de_ts.loc[de_ts.index < end_date, 'DE_load_'] = (
        de_ts.loc[de_ts.index < end_date,
                  'DE_load_actual_entsoe_power_statistics'])
    de_ts.loc[de_ts.index >= end_date, 'DE_load_'] = (
        de_ts.loc[de_ts.index >= end_date,
                  'DE_load_actual_entsoe_transparency'])

    load = pd.DataFrame(de_ts[pd.notnull(de_ts['DE_load_'])]['DE_load_'],
                        columns=['DE_load_'])

    re_columns = [
        'DE_solar_capacity', 'DE_solar_generation_actual', 'DE_solar_profile',
        'DE_wind_capacity', 'DE_wind_generation_actual', 'DE_wind_profile',
        'DE_wind_offshore_capacity', 'DE_wind_offshore_generation_actual',
        'DE_wind_offshore_profile', 'DE_wind_onshore_capacity',
        'DE_wind_onshore_generation_actual', 'DE_wind_onshore_profile']
    re_subset = [
        'DE_solar_capacity', 'DE_solar_generation_actual', 'DE_solar_profile',
        'DE_wind_capacity', 'DE_wind_generation_actual', 'DE_wind_profile']

    renewables = de_ts.dropna(subset=re_subset, how='any')[re_columns]

    return entsoe_ts(load=load, renewables=renewables)


def get_entsoe_load(year):
    """

    Parameters
    ----------
    year

    Returns
    -------

    Examples
    --------
    >>> entsoe = get_entsoe_load(2015)
    >>> int(entsoe.sum())
    477924124
    """
    filename = os.path.join(cfg.get('paths', 'entsoe'),
                            cfg.get('entsoe', 'load_file'))
    if not os.path.isfile(filename):
        load = split_timeseries_file().load
        load.to_hdf(filename, 'entsoe')

    # Read entsoe time series for the given year
    f = pd.datetime(year, 1, 1, 0)
    t = pd.datetime(year, 12, 31, 23)
    logging.info("Read entsoe load series from {0} to {1}".format(f, t))
    df = pd.DataFrame(pd.read_hdf(filename, 'entsoe'))
    return df.loc[f:t]


def get_entsoe_renewable_data():
    """

    Returns
    -------

    Examples
    --------
    >>> re = get_entsoe_renewable_data()
    >>> int(re['DE_solar_generation_actual'].sum())
    237214558
    """
    version = cfg.get('entsoe', 'timeseries_version')
    path_pattern = os.path.join(cfg.get('paths', 'entsoe'), '{0}')
    fn = path_pattern.format(
       cfg.get('entsoe', 'renewables_file_csv').format(version=version))
    if not os.path.isfile(fn):
        renewables = split_timeseries_file().renewables
        renewables.to_csv(fn)
    re = pd.read_csv(fn, index_col=[0], parse_dates=True)
    return re


if __name__ == "__main__":
    pass
