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


def create_deflex_slp_profile(region, year, annual, profile='entsoe'):

    demand_deflex = prepare_ego_demand()

    cal = Germany()
    holidays = dict(cal.holidays(year))

    deflex_profile = pd.DataFrame()

    for region in demand_deflex.index:
        annual_demand = demand_deflex.loc[region]

        annual_electrical_demand_per_sector = {
            'g0': annual_demand.sector_consumption_retail,
            'h0': annual_demand.sector_consumption_residential,
            'l0': annual_demand.sector_consumption_agricultural,
            'i0': annual_demand.sector_consumption_industrial}
        e_slp = bdew.ElecSlp(year, holidays=holidays)

        elec_demand = e_slp.get_profile(
            annual_electrical_demand_per_sector)

        # Add the slp for the industrial group
        ilp = profiles.IndustrialLoadProfile(e_slp.date_time_index,
                                             holidays=holidays)

        elec_demand['i0'] = ilp.simple_profile(
            annual_electrical_demand_per_sector['i0'])

        deflex_profile[region] = elec_demand.sum(1).resample('H').mean()
    deflex_profile.to_csv(outfile)


def get_slp_profile_by_region(region, year, annual, profile='entsoe'):
    outfile = os.path.join(
        cfg.get('paths', 'demand'),
        cfg.get('demand', 'ego_profile_pattern').format(
            year=year, map=cfg.get('init', 'map')))
    if not os.path.isfile(outfile) or overwrite:
        create_deflex_slp_profile(year, outfile)

    deflex_profile = pd.read_csv(
        outfile, index_col=[0], parse_dates=True,
        date_parser=lambda col: pd.to_datetime(col, utc=True)).multiply(
        1000)

    if annual_demand is not None:
        deflex_profile = deflex_profile.div(deflex_profile.sum().sum()
                                            ).multiply(annual_demand)

    return deflex_profile


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
