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


def get_entsoe_profile_by_region(region, year, name, annual_demand=None):
    """

    Parameters
    ----------
    region
    year
    name
    annual_demand

    Returns
    -------

    Examples
    --------
    >>> fs = geometries.get_federal_states_polygon()
    >>> d1 = get_entsoe_profile_by_region(fs, 2014, 'federal_states'
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
    de_load_profile = entsoe.get_entsoe_load(2014).DE_load_

    load_profile = pd.DataFrame()

    annual_region = openego.get_ego_demand_by_region(
        region, name, grouped=True)

    share = annual_region.div(annual_region.sum())

    for region in region.index:
        if region not in share:
            share[region] = 0
        load_profile[region] = de_load_profile.multiply(float(share[region]))

    if annual_demand == 'bmwi':
        annual_demand = bmwi_data.get_annual_electricity_demand_bmwi(year)

    if annual_demand is not None:
        load_profile = load_profile.div(load_profile.sum().sum()).multiply(
            annual_demand)

    return load_profile


if __name__ == "__main__":
    pass
