# -*- coding: utf-8 -*-

"""Processing a list of power plants in Germany.

Copyright (c) 2016-2018 Uwe Krien <uwe.krien@rl-institut.de>

SPDX-License-Identifier: GPL-3.0-or-later
"""
__copyright__ = "Uwe Krien <uwe.krien@rl-institut.de>"
__license__ = "GPLv3"


# Python libraries
import os
import logging

# External libraries
import pandas as pd
from workalendar.europe import Germany

# oemof libraries
from oemof.tools import logger
import demandlib.bdew as bdew

# internal modules
import reegis_tools.config as cfg
import reegis_tools.entsoe
import reegis_tools.bmwi
import reegis_tools.geometries
import reegis_tools.energy_balance
import reegis_tools.coastdat
import reegis_tools.openego


def heat_demand(year):
    eb = reegis_tools.energy_balance.get_states_balance(year)
    eb.sort_index(inplace=True)

    # get fraction of domestic and retail from the german energy balance
    share = reegis_tools.energy_balance.get_domestic_retail_share(year)

    # Use 0.5 for both sectors if no value is given
    share.fillna(0.5, inplace=True)

    # Divide domestic and retail by the value of the german energy balance if
    # the sum of domestic and retail does not equal the value given in the
    # local energy balance.
    check_value = True
    for state in eb.index.get_level_values(0).unique():
        for col in eb.columns:
            check = (eb.loc[(state, 'domestic'), col] +
                     eb.loc[(state, 'retail'), col] -
                     eb.loc[(state, 'domestic and retail'), col]).round()
            if check < 0:
                for sector in ['domestic', 'retail']:
                    eb.loc[(state, sector), col] = (
                        eb.loc[(state, 'domestic and retail'), col] *
                        share.loc[col, sector])

                check = (eb.loc[(state, 'domestic'), col] +
                         eb.loc[(state, 'retail'), col] -
                         eb.loc[(state, 'domestic and retail'), col]).round()

                if check < 0:
                    logging.error("In {0} the {1} sector results {2}".format(
                        state, col, check))
                    check_value = False
    if check_value:
        logging.debug("Divides 'domestic and retail' without errors.")

    # Reduce energy balance to the needed columns and group by fuel groups.
    eb = eb.loc[(slice(None), ['industrial', 'domestic', 'retail']), ]

    eb = eb.groupby(by=cfg.get_dict('FUEL_GROUPS_HEAT_DEMAND'), axis=1).sum()

    # Remove empty columns
    for col in eb.columns:
        if not (eb.loc[(slice(None), 'domestic'), col].sum() > 0 or
                eb.loc[(slice(None), 'retail'), col].sum() > 0 or
                eb.loc[(slice(None), 'industrial'), col].sum() > 0):
            del eb[col]

    # The use of electricity belongs to the electricity sector. It is possible
    # to connect it to the heating sector for future scenarios.
    del eb['electricity']
    del eb['total']  # if electricity is removed total is not correct anymore.

    # get fraction of mechanical energy use and subtract it from the balance to
    # get the use of heat only.
    share_mech = share_of_mechanical_energy_bmwi(year)
    for c in share_mech.columns:
        for i in share_mech.index:
            eb.loc[(slice(None), c), i] -= (
                eb.loc[(slice(None), c), i] * share_mech.loc[i, c])
    eb.sort_index(inplace=True)

    return eb


def share_of_mechanical_energy_bmwi(year):
    mech = pd.DataFrame()
    fs = reegis_tools.bmwi.read_bmwi_sheet_7('a')
    fs.sort_index(inplace=True)
    sector = 'Industrie'

    total = float(fs.loc[(sector, 'gesamt'), year])
    mech[sector] = fs.loc[(sector, 'mechanische Energie'), year].div(
        total).round(3)

    fs = reegis_tools.bmwi.read_bmwi_sheet_7('b')
    fs.sort_index(inplace=True)
    for sector in fs.index.get_level_values(0).unique():
        total = float(fs.loc[(sector, 'gesamt'), year])
        mech[sector] = fs.loc[(sector, 'mechanische Energie'), year].div(
            total).astype(float).round(3)
    mech.drop(' - davon Strom', inplace=True)
    mech.drop('mechanische Energie', inplace=True)
    ren_col = {
        'Industrie': 'industrial',
        'Gewerbe, Handel, Dienstleistungen ': 'retail',
        'private Haushalte': 'domestic', }
    ren_index = {
        ' - davon Öl': 'oil',
        ' - davon Gas': 'natural gas', }
    del mech.index.name
    mech.rename(columns=ren_col, inplace=True)
    mech.rename(index=ren_index, inplace=True)
    mech.fillna(0, inplace=True)
    return mech


def share_houses_flats(key=None):
    """

    Parameters
    ----------
    key str
        Valid keys are: 'total_area', 'avg_area', 'share_area', 'total_number',
         'share_number'.

    Returns
    -------
    dict or pd.DataFrame
    """
    size = pd.Series([1, 25, 50, 70, 90, 110, 130, 150, 170, 190, 210])
    infile = os.path.join(
        cfg.get('paths', 'data_de21'),
        cfg.get('general_sources', 'zensus_flats'))
    whg = pd.read_csv(infile, delimiter=';', index_col=[0], header=[0, 1],
                      skiprows=5)
    whg = whg.loc[whg['Insgesamt', 'Insgesamt'].notnull()]
    new_index = []
    states = cfg.get_dict('STATES')
    for i in whg.index:
        new_index.append(states[i[3:-13]])
    whg.index = new_index

    flat = {'total_area': pd.DataFrame(),
            'total_number': pd.DataFrame(),
            }
    for f in whg.columns.get_level_values(0).unique():
        df = pd.DataFrame(whg[f].values * size.values, columns=whg[f].columns,
                          index=whg.index)
        flat['total_area'][f] = df.sum(1) - df['Insgesamt']
        flat['total_number'][f] = df['Insgesamt']
    flat['total_area']['1 + 2 Wohnungen'] = (
        flat['total_area']['1 Wohnung'] + flat['total_area']['2 Wohnungen'])
    flat['total_number']['1 + 2 Wohnungen'] = (
        flat['total_number']['1 Wohnung'] +
        flat['total_number']['2 Wohnungen'])

    flat['avg_area'] = flat['total_area'].div(flat['total_number'])
    flat['share_area'] = (flat['total_area'].transpose().div(
        flat['total_area']['Insgesamt'])).transpose().round(3)
    flat['share_number'] = (flat['total_number'].transpose().div(
        flat['total_number']['Insgesamt'])).transpose().round(3)

    if key is None:
        return flat
    elif key in flat:
        return flat[key].sort_index()
    else:
        logging.warning(
            "'{0}' is an invalid key for function 'share_houses_flats'".format(
                key))
    return None


def get_heat_profile_from_demandlib(temperature, annual_demand, sector, year,
                                    build_class=1):
    cal = Germany()
    holidays = dict(cal.holidays(year))

    if 'efh' in sector:
        shlp_type = 'EFH'
    elif 'mfh' in sector:
        shlp_type = 'MFH'
    elif 'domestic' in sector:
        shlp_type = 'MFH'
    elif 'retail' in sector:
        shlp_type = 'ghd'
        build_class = 0
    elif 'industrial' in sector:
        shlp_type = 'ghd'
        build_class = 0
    else:
        raise AttributeError('"{0}" is an unknown sector.'.format(sector))
    return bdew.HeatBuilding(
        temperature.index, holidays=holidays, temperature=temperature,
        shlp_type=shlp_type, wind_class=0, building_class=build_class,
        annual_heat_demand=annual_demand, name=sector, ww_incl=True
        ).get_bdew_profile()


def get_heat_profiles_by_state(year, to_csv=False, divide_domestic=False,
                               state=None, weather_year=None):

    if weather_year is None:
        weather_year = year

    building_class = {}
    for (k, v) in cfg.get_dict('building_class').items():
        for s in v.split(', '):
            building_class[s] = int(k)

    demand_state = heat_demand(year).sort_index()

    if divide_domestic:
        house_flats = share_houses_flats('share_area')
        for state in demand_state.index.get_level_values(0).unique():
            dom = demand_state.loc[state, 'domestic']
            demand_state.loc[(state, 'domestic_efh'), ] = (
                dom * house_flats.loc[state, '1 + 2 Wohnungen'])
            demand_state.sort_index(0, inplace=True)
            dom = demand_state.loc[state, 'domestic']
            demand_state.loc[(state, 'domestic_mfh'), ] = (
                dom * house_flats.loc[state, '3 und mehr Wohnungen'])
            demand_state.sort_index(0, inplace=True)

        demand_state.sort_index(inplace=True)
        demand_state.drop('domestic', level=1, inplace=True)

    temperatures = reegis_tools.coastdat.federal_state_average_weather(
        weather_year, 'temp_air')

    temperatures = temperatures.tz_localize('UTC').tz_convert('Europe/Berlin')

    my_columns = pd.MultiIndex(levels=[[], [], []], labels=[[], [], []])
    heat_profiles = pd.DataFrame(columns=my_columns)

    if state is None:
        states = demand_state.index.get_level_values(0).unique()
    else:
        states = state

    # for region in demand_state.index.get_level_values(0).unique():
    for region in states:
        logging.info("Creating heat profile for {}".format(region))
        tmp = demand_state.loc[region].groupby(level=0).sum()
        temperature = temperatures[region] - 273
        for fuel in tmp.columns:
            logging.debug("{0} - {1} ({2})".format(
                region, fuel, building_class[region]))
            for sector in tmp.index:
                heat_profiles[(region, sector, fuel)] = (
                    get_heat_profile_from_demandlib(
                        temperature, tmp.loc[sector, fuel], sector, year,
                        building_class[region]))
    heat_profiles.sort_index(1, inplace=True)
    if to_csv:
        if weather_year is None:
            fn = os.path.join(
                cfg.get('paths', 'demand'),
                cfg.get('demand', 'heat_profile_state').format(year=year))
        else:
            fn = os.path.join(
                cfg.get('paths', 'demand'),
                cfg.get('demand', 'heat_profile_state_var').format(
                    year=year, weather_year=weather_year))
        heat_profiles.to_csv(fn)
    return heat_profiles


if __name__ == "__main__":
    logger.define_logging()
