# -*- coding: utf-8 -*-

# -*- coding: utf-8 -*-

""" Download and prepare entsoe load profile from opsd data portal.

Copyright (c) 2016-2018 Uwe Krien <uwe.krien@rl-institut.de>

SPDX-License-Identifier: GPL-3.0-or-later
"""
__copyright__ = "Uwe Krien <uwe.krien@rl-institut.de>"
__license__ = "GPLv3"


# Python libraries
import os
import logging
import datetime

# External packages
import requests
import pytz
import dateutil
import pandas as pd

# oemof packages
from oemof.tools import logger

# internal modules
import reegis.config as cfg


def read_original_timeseries_file(overwrite=False):
    """Read timeseries file if it exists. Otherwise download it from opsd.
    """
    version = cfg.get('entsoe', 'time_series_version')
    orig_csv_file = os.path.join(
        cfg.get('paths', 'entsoe'),
        cfg.get('entsoe', 'original_file')).format(version=version)
    readme = os.path.join(
        cfg.get('paths', 'entsoe'),
        cfg.get('entsoe', 'readme_file')).format(version=version)
    json = os.path.join(
        cfg.get('paths', 'entsoe'),
        cfg.get('entsoe', 'json_file')).format(version=version)

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

    orig = pd.read_csv(orig_csv_file, index_col=[0], parse_dates=True)
    orig = orig.tz_convert('Europe/Berlin')
    return orig


def prepare_de_file(overwrite=False):
    """Convert demand file. CET index and Germany's load only."""
    version = cfg.get('entsoe', 'time_series_version')
    de_file = os.path.join(
        cfg.get('paths', 'entsoe'),
        cfg.get('entsoe', 'de_file').format(version=version))
    if not os.path.isfile(de_file) or overwrite:
        ts = read_original_timeseries_file(overwrite)
        for col in ts.columns:
            if 'DE' not in col:
                ts.drop(col, 1, inplace=True)

        ts.to_csv(de_file)


def split_timeseries_file(overwrite=False, csv=False):
    logging.info("Splitting time series.")
    version = cfg.get('entsoe', 'time_series_version')
    path_pattern = os.path.join(cfg.get('paths', 'entsoe'), '{0}')
    de_file = path_pattern.format(cfg.get('entsoe', 'de_file').format(
        version=version))

    if not os.path.isfile(de_file) or overwrite:
        prepare_de_file(overwrite)

    de_ts = pd.read_csv(de_file, index_col='utc_timestamp', parse_dates=True,
                        date_parser=dateutil.parser.parse)

    berlin = pytz.timezone('Europe/Berlin')
    end_date = berlin.localize(datetime.datetime(2015, 1, 1, 0, 0, 0))

    de_ts.loc[de_ts.index < end_date, 'DE_load_'] = (
        de_ts.loc[de_ts.index < end_date, 'DE_load_entsoe_power_statistics'])
    de_ts.loc[de_ts.index >= end_date, 'DE_load_'] = (
        de_ts.loc[de_ts.index >= end_date, 'DE_load_entsoe_transparency'])

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

    if csv:
        load_file = path_pattern.format(
            cfg.get('entsoe', 'load_file_csv').format(version=version))
    else:
        load_file = path_pattern.format(
            cfg.get('entsoe', 'load_file').format(version=version))

    if not os.path.isfile(load_file) or overwrite:
        if csv:
            load.to_csv(load_file)
        else:
            load.to_hdf(load_file, 'entsoe')

    if csv:
        re_file = path_pattern.format(
            cfg.get('entsoe', 'renewables_file_csv').format(version=version))
    else:
        re_file = path_pattern.format(
            cfg.get('entsoe', 'renewables_file').format(version=version))
    if not os.path.isfile(re_file) or overwrite:
        if csv:
            renewables.to_csv(re_file)
        else:
            renewables.to_hdf(re_file, 're')


def prepare_entsoe_timeseries(overwrite=False):
    split_timeseries_file(overwrite)


def get_entsoe_load(year):
    filename = os.path.join(cfg.get('paths', 'entsoe'),
                            cfg.get('entsoe', 'load_file'))
    if not os.path.isfile(filename):
        prepare_entsoe_timeseries()

    # Read entsoe time series for the given year
    f = pd.datetime(year, 1, 1, 0)
    t = pd.datetime(year, 12, 31, 23)
    logging.info("Read entsoe load series from {0} to {1}".format(f, t))
    df = pd.DataFrame(pd.read_hdf(filename, 'entsoe'))
    return df.loc[f:t]


def get_entsoe_renewable_data(csv=False, overwrite=False):
    version = cfg.get('entsoe', 'time_series_version')
    path_pattern = os.path.join(cfg.get('paths', 'entsoe'), '{0}')
    if csv:
        fn = path_pattern.format(
            cfg.get('entsoe', 'renewables_file_csv').format(version=version))
    else:
        fn = path_pattern.format(
            cfg.get('entsoe', 'renewables_file').format(version=version))
    if not os.path.isfile(fn):
        split_timeseries_file(csv=csv)
    if csv:
        re = pd.read_csv(fn, index_col=[0], parse_dates=True)
    else:
        re = pd.DataFrame(pd.read_hdf(fn, 're'))
    print(re.index[0])
    return re


if __name__ == "__main__":
    logger.define_logging()
    print(get_entsoe_renewable_data())
    logging.info("Done!")
