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
import reegis.config as cfg
import reegis.entsoe
import reegis.bmwi
import reegis.geometries
import reegis.energy_balance
import reegis.coastdat
import reegis.openego
import reegis.inhabitants


def heat_demand(year):
    """
    Fetch heat demand per sector from the federal states energy balances.

    Parameters
    ----------
    year

    Returns
    -------
    pandas.DataFrame
    """
    eb = reegis.energy_balance.get_states_balance(year)
    eb.sort_index(inplace=True)

    # get fraction of domestic and retail from the german energy balance
    share = reegis.energy_balance.get_domestic_retail_share(year)

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
    """
    Get share of mechanical energy from the overall energy use per sector.

    Parameters
    ----------
    year : int

    Returns
    -------
    pandas.DataFrame

    Examples
    --------
    >>> share_of_mechanical_energy_bmwi(2014).loc['oil', 'retail']
    0.078

    """
    mech = pd.DataFrame()
    fs = reegis.bmwi.read_bmwi_sheet_7('a')
    fs.sort_index(inplace=True)
    sector = 'Industrie'

    total = float(fs.loc[(sector, 'gesamt'), year])
    mech[sector] = fs.loc[(sector, 'mechanische Energie'), year].div(
        total).round(3)

    fs = reegis.bmwi.read_bmwi_sheet_7('b')
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


def get_heat_profile_from_demandlib(temperature, annual_demand, sector, year,
                                    build_class=1):
    """
    Create an hourly load profile from the annual demand using the demandlib.

    Parameters
    ----------
    temperature : pandas.Series
    annual_demand : float
    sector : str
    year : int
    build_class : int

    Returns
    -------
    pandas.DataFrame

    Examples
    --------
    >>> temperature = pd.Series(list(range(50)), index=pd.date_range(
    ...     '2014-05-03 12:00', periods=50, freq='h'))
    >>> temperature = 10 + temperature * 0.1
    >>> hp = get_heat_profile_from_demandlib(
    ...     temperature, 5345, 'retail', 2014)
    >>> round(hp.sum())
    5276.0
    """
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


def get_heat_profiles_by_federal_state(year, to_csv=None, state=None,
                                       weather_year=None):
    """
    Get heat profiles by state, sector and fuel. Use the pandas `groupby`
    method to group the results.

    The unit of the resulting data is TJ.

    Parameters
    ----------
    year : int
        Year of the demand data set.
    to_csv : str
        Path to the csv file.
    state : list or None
        List of abbreviations of federal states. If None a table with all
        federal states will be returned. Valid values are: BB, BE, BW, BY, HB,
        HE, HH, MV, NI, NW, RP, SH, SL, SN, ST, TH
    weather_year : int or None
        Can be used if the year of the weather data differs from the year of
        the demand data. If None the year parameter will be used. Use with
        care, because the demand data may include implicit weather effects.

    Returns
    -------
    pd.DataFrame

    Examples
    --------
    >>> fn = os.path.join(os.path.expanduser('~'), 'fsh.csv')
    >>> hp = get_heat_profiles_by_federal_state(2014, state=['BE', 'BB'],
    ...                                 to_csv=fn)
    >>> round(hp.groupby(level=[0], axis=1).sum().sum().loc['BE'], 1)
    112950.7
    >>> round(hp.groupby(level=[2], axis=1).sum().sum().loc['lignite'], 1)
    6017.0
    >>> hp_MWh = hp.div(0.0036)
    >>> round(hp_MWh.groupby(level=[2], axis=1).sum().sum().loc['lignite'], 1)
    1671392.1
    """

    if weather_year is None:
        weather_year = year

    building_class = {}
    for (k, v) in cfg.get_dict('building_class').items():
        for s in v.split(', '):
            building_class[s] = int(k)

    demand_state = heat_demand(year).sort_index()

    temperatures = reegis.coastdat.federal_state_average_weather(
        weather_year, 'temp_air')

    temperatures = temperatures.tz_convert('Europe/Berlin')

    my_columns = pd.MultiIndex(levels=[[], [], []], codes=[[], [], []])
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

    if to_csv is not None:
        heat_profiles.to_csv(to_csv)
    return heat_profiles


def get_heat_profiles_by_region(year, regions, name='region', from_csv=None,
                                to_csv=None, weather_year=None):
    """
    Get heat profiles for any region devided by sector and fuel. Use the
    pandas `groupby` method to group the results.

    The unit of the resulting data is TJ.

    Parameters
    ----------
    year : int
        Year of the demand data set.
    regions : geopandas.geoDataFrame
        A table with region geometries and there id as index.
    name : str
        Name of the regions set.
    from_csv : str
        Path to the file of the demand state profiles.
    to_csv : str
        Path with filename of the output file.
    weather_year : int or None
        Can be used if the year of the weather data differs from the year of
        the demand data. If None the year parameter will be used. Use with
        care, because the demand data may include implicit weather effects.

    Returns
    -------
    pd.DataFrame

    Examples
    --------
    >>> fn = os.path.join(os.path.expanduser('~'), 'fsh.csv')
    >>> regions = reegis.geometries.load(
    ...     cfg.get('paths', 'geometry'),
    ...     'region_polygons_de21_vg.csv')
    >>> hp1 = get_heat_profiles_by_region(2014, regions, from_csv=fn)
    """
    if weather_year is None:
        weather_year = year

    # Get demand by federal state
    if from_csv is None:
        from_csv = os.path.join(
            cfg.get('paths', 'demand'),
            cfg.get('demand', 'heat_profile_state_var').format(
                year=year, weather_year=weather_year))
    if not os.path.isfile(from_csv):
        get_heat_profiles_by_federal_state(
            year, to_csv=from_csv, weather_year=weather_year)
    demand_state = pd.read_csv(from_csv, index_col=[0], header=[0, 1, 2])

    # Create empty MulitIndex DataFrame to take the results
    four_level_columns = pd.MultiIndex(levels=[[], [], [], []],
                                       codes=[[], [], [], []])
    demand_region = pd.DataFrame(index=demand_state.index,
                                 columns=four_level_columns)

    # Get inhabitants for federal states and the given regions
    fs_geo = reegis.geometries.get_federal_states_polygon()
    ew = reegis.inhabitants.get_ew_by_multi_regions(
        year, [regions, fs_geo], name=[name, 'federal_states'])
    ew = ew[ew != 0]

    # Calculate the share of the federal states within the regions.
    fs_sum = ew.groupby(level=1).sum().copy()
    for reg in ew.index.get_level_values(0).unique():
        for fs in ew.loc[reg].index:
            ew.loc[reg, fs] = ew.loc[reg, fs] / fs_sum[fs]

    # Use the inhabitants to recalculate the demand from federal states to
    # the given regions.
    for i in ew.items():
        state = i[0][1]
        region = i[0][0]
        share = i[1]
        if state in demand_state.columns.get_level_values(0).unique():
            for sector in demand_state[state].columns.get_level_values(
                    0).unique():
                for fuel in demand_state[state, sector].columns:
                    demand_region[
                        region, fuel, sector, state] = (
                            demand_state[state, sector, fuel] * share)
    demand_region.sort_index(1, inplace=True)
    demand_region = demand_region.groupby(level=[0, 1, 2], axis=1).sum()

    if to_csv is not None:
        demand_region.to_csv(to_csv)

    return demand_region


if __name__ == "__main__":
    logger.define_logging()
