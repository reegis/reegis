# -*- coding: utf-8 -*-

# -*- coding: utf-8 -*-

""" Download and prepare entsoe load profile from opsd data portal.

Copyright (c) 2016-2018 Uwe Krien <uwe.krien@rl-institut.de>

SPDX-License-Identifier: GPL-3.0-or-later
"""
__copyright__ = "Uwe Krien <uwe.krien@rl-institut.de>"
__license__ = "GPLv3"


# Python libraries
import logging

# External packages
import pandas as pd

# internal modules
import reegis.config as cfg
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

    """
    logging.debug("Get entsoe profile {0} for {1}".format(name, year))
    de_load_profile = entsoe.get_entsoe_load(2014).DE_load_

    load_profile = pd.DataFrame()

    annual_region = openego.get_ego_demand_by_region(year, region, name)

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


def get_electricity_profile_by_federal_states(year, profile=entsoe):
    federal_states = geometries.load(
        cfg.get('paths', 'geometry'),
        cfg.get('geometry', 'federalstates_polygon'))
    federal_states.set_index('iso', drop=True, inplace=True)
    return get_entsoe_profile_by_region(federal_states, 'federal_states', year)


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    print(get_electricity_profile_by_federal_states(2014)['BE'])
