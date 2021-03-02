# -*- coding: utf-8 -*-

# -*- coding: utf-8 -*-

""" Download and prepare entsoe load profile from opsd data portal.

SPDX-FileCopyrightText: 2016-2021 Uwe Krien <krien@uni-bremen.de>

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


def read_original_timeseries_file(
    orig_csv_file=None, overwrite=False, version=None
):
    """Read timeseries file if it exists. Otherwise download it from opsd.
    """
    if version is None:
        version = cfg.get("entsoe", "timeseries_version")

    if orig_csv_file is None:
        orig_csv_file = os.path.join(
            cfg.get("paths", "entsoe"), cfg.get("entsoe", "original_file")
        ).format(version=version)
    readme = os.path.join(
        cfg.get("paths", "entsoe"), cfg.get("entsoe", "readme_file")
    ).format(version=version)
    json = os.path.join(
        cfg.get("paths", "entsoe"), cfg.get("entsoe", "json_file")
    ).format(version=version)

    if not os.path.isfile(orig_csv_file) or overwrite:
        req = requests.get(
            cfg.get("entsoe", "timeseries_data").format(version=version)
        )

        if not overwrite:
            logging.warning("File not found. Try to download it from server.")
        else:
            logging.warning(
                "Will download file from server and overwrite" "existing ones"
            )
        logging.warning("Check URL if download does not work.")
        with open(orig_csv_file, "wb") as fout:
            fout.write(req.content)
        logging.warning(
            "Downloaded from {0} and copied to '{1}'.".format(
                cfg.get("entsoe", "timeseries_data").format(version=version),
                orig_csv_file,
            )
        )
        req = requests.get(
            cfg.get("entsoe", "timeseries_readme").format(version=version)
        )
        with open(readme, "wb") as fout:
            fout.write(req.content)
        req = requests.get(
            cfg.get("entsoe", "timeseries_json").format(version=version)
        )
        with open(json, "wb") as fout:
            fout.write(req.content)
    logging.debug("Reading file: {0}".format(orig_csv_file))
    orig = pd.read_csv(
        orig_csv_file,
        index_col=[0],
        parse_dates=True,
        date_parser=lambda col: pd.to_datetime(col, utc=True),
    )
    orig = orig.tz_convert("Europe/Berlin")
    return orig


def prepare_de_file(filename=None, overwrite=False, version=None):
    """Convert demand file. CET index and Germany's load only."""
    if version is None:
        version = cfg.get("entsoe", "timeseries_version")
    if filename is None:
        filename = os.path.join(
            cfg.get("paths", "entsoe"),
            cfg.get("entsoe", "de_file").format(version=version),
        )
    if not os.path.isfile(filename) or overwrite:
        ts = read_original_timeseries_file(
            overwrite=overwrite, version=version
        )
        for col in ts.columns:
            if "DE" not in col:
                ts.drop(col, 1, inplace=True)

        ts.to_csv(filename)
    return filename


def split_timeseries_file(filename=None, overwrite=False, version=None):
    """Split table into load and renewables."""
    entsoe_ts = namedtuple("entsoe", ["load", "renewables"])
    logging.info("Splitting time series.")
    if version is None:
        version = cfg.get("entsoe", "timeseries_version")
    path_pattern = os.path.join(cfg.get("paths", "entsoe"), "{0}")
    if filename is None:
        filename = path_pattern.format(
            cfg.get("entsoe", "de_file").format(version=version)
        )

    if not os.path.isfile(filename) or overwrite:
        prepare_de_file(filename, overwrite, version)

    de_ts = pd.read_csv(
        filename.format(version=version),
        index_col="utc_timestamp",
        parse_dates=True,
        date_parser=lambda col: pd.to_datetime(col, utc=True),
    )
    de_ts.index = de_ts.index.tz_convert("Europe/Berlin")
    de_ts.index.rename("cet_timestamp", inplace=True)

    de_ts["DE_load_"] = de_ts["DE_load_actual_entsoe_transparency"]

    if "DE_load_actual_entsoe_power_statistics" in de_ts:
        berlin = pytz.timezone("Europe/Berlin")
        end_date = berlin.localize(datetime.datetime(2015, 1, 1, 0, 0, 0))
        de_ts.loc[de_ts.index < end_date, "DE_load_"] = de_ts.loc[
            de_ts.index < end_date, "DE_load_actual_entsoe_power_statistics"
        ]

    load = pd.DataFrame(
        de_ts[pd.notnull(de_ts["DE_load_"])]["DE_load_"], columns=["DE_load_"]
    )

    re_columns = [
        "DE_solar_capacity",
        "DE_solar_generation_actual",
        "DE_solar_profile",
        "DE_wind_capacity",
        "DE_wind_generation_actual",
        "DE_wind_profile",
        "DE_wind_offshore_capacity",
        "DE_wind_offshore_generation_actual",
        "DE_wind_offshore_profile",
        "DE_wind_onshore_capacity",
        "DE_wind_onshore_generation_actual",
        "DE_wind_onshore_profile",
    ]
    re_subset = [
        "DE_solar_capacity",
        "DE_solar_generation_actual",
        "DE_solar_profile",
        "DE_wind_capacity",
        "DE_wind_generation_actual",
        "DE_wind_profile",
    ]

    renewables = de_ts.dropna(subset=re_subset, how="any")[re_columns]

    return entsoe_ts(load=load, renewables=renewables)


def get_entsoe_load(year, version=None):
    """

    Parameters
    ----------
    year
    version

    Returns
    -------

    Examples
    --------
    >>> entsoe=get_entsoe_load(2015)
    >>> float(round(entsoe.sum()/1e6, 1))
    479.5
    """
    if version is None:
        version = cfg.get("entsoe", "timeseries_version")
    filename = os.path.join(
        cfg.get("paths", "entsoe"), cfg.get("entsoe", "load_file")
    )
    if not os.path.isfile(filename):
        load = split_timeseries_file(version=version).load
        load.to_hdf(filename.format(version=version), "entsoe")

    # Read entsoe time series for the given year
    f = datetime.datetime(year, 1, 1, 0)
    t = datetime.datetime(year, 12, 31, 23)
    f = f.astimezone(pytz.timezone("Europe/Berlin"))
    t = t.astimezone(pytz.timezone("Europe/Berlin"))
    logging.info("Read entsoe load series from {0} to {1}".format(f, t))
    df = pd.DataFrame(pd.read_hdf(filename.format(version=version), "entsoe"))
    return df.loc[f:t]


def get_filtered_file(name, url, version=None):
    # name += ".csv"
    fn = os.path.join(cfg.get("paths", "entsoe"), name + ".csv")
    if not os.path.isfile(fn):
        req = requests.get(url.format(version=version))
        with open(fn, "wb") as fout:
            fout.write(req.content)
    return pd.read_csv(fn)


def get_entsoe_renewable_data(file=None, version=None):
    """
    Load the default file for re time series or a specific file.

    Returns
    -------

    Examples
    --------
    >>> my_re=get_entsoe_renewable_data()
    >>> int(my_re['DE_solar_generation_actual'].sum())
    188160676
    """
    if version is None:
        version = cfg.get("entsoe", "timeseries_version")
    path_pattern = os.path.join(cfg.get("paths", "entsoe"), "{0}")
    if file is None:
        fn = path_pattern.format(
            cfg.get("entsoe", "renewables_file_csv").format(version=version)
        )
    else:
        fn = file.format(version=version)

    if not os.path.isfile(fn):
        if file is None:
            renewables = split_timeseries_file(version=version).renewables
            renewables.to_csv(fn)

    re = pd.read_csv(
        fn,
        index_col=[0],
        parse_dates=True,
        date_parser=lambda x: datetime.datetime.strptime(
            x.split("+")[0], "%Y-%m-%d %H:%M:%S"
        ),
    )
    return re


if __name__ == "__main__":
    pass
