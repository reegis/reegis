# -*- coding: utf-8 -*-

""" Download and prepare entsoe load profile from opsd data portal.

Copyright (c) 2016-2019 Uwe Krien <krien@uni-bremen.de>

SPDX-License-Identifier: MIT
"""
__copyright__ = "Uwe Krien <krien@uni-bremen.de>"
__license__ = "MIT"


# Python libraries
import logging

# External packages
import pandas as pd

# internal modules
from reegis import entsoe
from reegis import geometries
from reegis import openego
from reegis import bmwi as bmwi_data


def get_entsoe_profile_by_region(region, year, name, annual_demand):
    """

    Parameters
    ----------
    region
    year
    name
    annual_demand : str or numeric
        A numeric annual value or a method to fetch the annual value.
        Valid methods are: bmwi, entsoe, openego

    Returns
    -------
    pandas.DataFrame : A table with a time series for each region. The unit
        will be GW/GWh for the internal methods or the same unit as the input
        of the annual_demand parameter.
    Examples
    --------
    >>> fs = geometries.get_federal_states_polygon()
    >>> d1 = get_entsoe_profile_by_region(fs, 2014, 'federal_states', 'entsoe'
    ...     )  # doctest: +SKIP
    >>> int(d1.sum().sum())  # doctest: +SKIP
    519757349
    >>> d2 = get_entsoe_profile_by_region(fs, 2014, 'federal_states', 'bmwi'
    ...     )  # doctest: +SKIP
    >>> int(d2.sum().sum())  # doctest: +SKIP
    523
    >>> d3 = get_entsoe_profile_by_region(fs, 2014, 'federal_states', 200
    ...     )  # doctest: +SKIP
    >>> round(d3.sum().sum())  # doctest: +SKIP
    200.0

    """
    logging.debug("Get entsoe profile {0} for {1}".format(name, year))

    profile = entsoe.get_entsoe_load(year).reset_index(drop=True)['DE_load_']
    norm_profile = profile.div(profile.sum())
    ego_demand = openego.get_ego_demand_by_region(region, name, grouped=True)

    if annual_demand == 'bmwi':
        annual_demand = (bmwi_data.get_annual_electricity_demand_bmwi(year) *
                         1000)
    elif annual_demand == 'entsoe':
        annual_demand = profile.sum() / 1000
    elif annual_demand == 'openego':
        annual_demand = ego_demand.sum()
    elif isinstance(annual_demand, (int, float)):
        pass
    else:
        msg = ("{0} of type {1} is not a valid input for 'annual_demand'.\n"
               "Use 'bmwi', 'entsoe' or a float/int value.")
        raise ValueError(msg.format(annual_demand, type(annual_demand)))

    demand_fs = ego_demand.div(ego_demand.sum()).mul(annual_demand)

    return pd.DataFrame([demand_fs.values] * len(norm_profile),
                        columns=demand_fs.index).mul(norm_profile, axis=0)


if __name__ == "__main__":
    pass
