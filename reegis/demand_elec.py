# -*- coding: utf-8 -*-

""" Download and prepare entsoe load profile from opsd data portal.

SPDX-FileCopyrightText: 2016-2021 Uwe Krien <krien@uni-bremen.de>

SPDX-License-Identifier: MIT
"""
__copyright__ = "Uwe Krien <krien@uni-bremen.de>"
__license__ = "MIT"


import logging
import os

import pandas as pd
from demandlib import bdew, particular_profiles
from reegis import bmwi as bmwi_data
from reegis import entsoe
from reegis import geometries
from reegis import openego
from reegis import config as cfg
from workalendar.europe import Germany


def get_entsoe_profile_by_region(
    region, year, name, annual_demand, version=None
):
    """

    Parameters
    ----------
    region
    year
    name
    annual_demand : str or numeric
        A numeric annual value or a method to fetch the annual value.
        Valid methods are: bmwi, entsoe, openego
    version : str or None
        Version of the opsd file. If set to "None" the latest version is used.

    Returns
    -------
    pandas.DataFrame : A table with a time series for each region. The unit
        is MW for the internal methods or the same unit order as the input
        of the annual_demand parameter.
    Examples
    --------
    >>> my_fs=geometries.get_federal_states_polygon()
    >>> d1=get_entsoe_profile_by_region(my_fs, 2014, 'federal_states', 'entsoe'
    ...     )  # doctest: +SKIP
    >>> int(d1.sum().sum())  # doctest: +SKIP
    519757349
    >>> d2=get_entsoe_profile_by_region(my_fs, 2014, 'federal_states', 'bmwi'
    ...     )  # doctest: +SKIP
    >>> int(d2.sum().sum())  # doctest: +SKIP
    523988000
    >>> d3=get_entsoe_profile_by_region(my_fs, 2014, 'federal_states', 200000
    ...     )  # doctest: +SKIP
    >>> round(d3.sum().sum())  # doctest: +SKIP
    200000.0

    """
    logging.debug("Get entsoe profile {0} for {1}".format(name, year))

    profile = entsoe.get_entsoe_load(year, version=version)["DE_load_"]
    idx = profile.index
    profile.reset_index(drop=True, inplace=True)
    norm_profile = profile.div(profile.sum() / 1000000)
    ego_demand = openego.get_ego_demand_by_region(region, name, grouped=True)

    if annual_demand == "bmwi":
        annual_demand = (
            bmwi_data.get_annual_electricity_demand_bmwi(year) * 10 ** 6
        )
    elif annual_demand == "entsoe":
        annual_demand = profile.sum()
    elif annual_demand == "openego":
        annual_demand = ego_demand.sum() * 10 ** 3
    elif isinstance(annual_demand, (int, float)):
        pass
    else:
        msg = (
            "{0} of type {1} is not a valid input for 'annual_demand'.\n"
            "Use 'bmwi', 'entsoe' or a float/int value."
        )
        raise ValueError(msg.format(annual_demand, type(annual_demand)))

    demand_fs = (
        ego_demand.div(ego_demand.sum() / 1000).mul(annual_demand).div(1000)
    )

    df = (
        pd.DataFrame(
            [demand_fs.values] * len(norm_profile), columns=demand_fs.index
        )
        .mul(norm_profile, axis=0)
        .div(1000000)
    )
    return df.set_index(idx.tz_convert("Europe/Berlin"))


def get_open_ego_slp_profile_by_region(
    region,
    year,
    name,
    annual_demand=None,
    filename=None,
    dynamic_H0=True,
):
    """
    Create standardised load profiles (slp) for each region.

    Parameters
    ----------
    region : geopandas.geoDataFrame
        Regions set.
    year : int
        Year.
    name : str
        Name of the region set.
    annual_demand : float
        Annual demand for all regions.
    filename : str (optional)
        Filename of the output file.
    dynamic_H0 : bool (optional)
        Use the dynamic function of the H0. If you doubt, "True" might be the
        tight choice (default: True)

    Returns
    -------

    """
    ego_demand = openego.get_ego_demand_by_region(
        region, name, sectors=True, dump=True
    )

    # Add holidays
    cal = Germany()
    holidays = dict(cal.holidays(year))

    # Drop geometry column and group by region
    ego_demand.drop("geometry", inplace=True, axis=1)
    ego_demand_grouped = ego_demand.groupby(name).sum()

    if filename is None:
        path = cfg.get("paths", "demand")
        filename = os.path.join(path, "open_ego_slp_profile_{0}.csv").format(
            name
        )

    if not os.path.isfile(filename):
        regions = ego_demand_grouped.index
    else:
        regions = []

    # Create standardised load profiles (slp)
    fs_profile = pd.DataFrame()
    for region in regions:
        logging.info("Create SLP for {0}".format(region))
        annual_demand_type = ego_demand_grouped.loc[region]

        annual_electrical_demand_per_sector = {
            "g0": annual_demand_type.sector_consumption_retail,
            "h0": annual_demand_type.sector_consumption_residential,
            "l0": annual_demand_type.sector_consumption_agricultural,
            "i0": annual_demand_type.sector_consumption_industrial
            + annual_demand_type.sector_consumption_large_consumers,
        }
        e_slp = bdew.ElecSlp(year, holidays=holidays)

        elec_demand = e_slp.get_profile(
            annual_electrical_demand_per_sector, dyn_function_h0=dynamic_H0
        )

        # Add the slp for the industrial group
        ilp = particular_profiles.IndustrialLoadProfile(
            e_slp.date_time_index, holidays=holidays
        )

        elec_demand["i0"] = ilp.simple_profile(
            annual_electrical_demand_per_sector["i0"]
        )
        elec_demand = elec_demand.resample("H").mean()
        elec_demand.columns = pd.MultiIndex.from_product(
            [[region], elec_demand.columns]
        )
        fs_profile = pd.concat([fs_profile, elec_demand], axis=1)

    if not os.path.isfile(filename):
        fs_profile.set_index(fs_profile.index - pd.DateOffset(hours=1)).to_csv(
            filename
        )

    df = pd.read_csv(
        filename,
        index_col=[0],
        header=[0, 1],
        parse_dates=True,
        date_parser=lambda col: pd.to_datetime(col, utc=True),
    ).tz_convert("Europe/Berlin")

    if annual_demand is None:
        return df
    else:
        return df.mul(annual_demand / df.sum().sum())


if __name__ == "__main__":
    # from reegis import geometries
    from oemof.tools import logger

    logger.define_logging()
    fs = geometries.get_federal_states_polygon()
    print(
        get_open_ego_slp_profile_by_region(fs, 2014, "federal_states")
        .sum()
        .sum()
    )
    print(
        get_open_ego_slp_profile_by_region(
            fs, 2014, "federal_states", annual_demand=500000
        )
        .sum()
        .sum()
    )


if __name__ == "__main__":
    pass
