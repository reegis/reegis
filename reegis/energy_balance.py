# -*- coding: utf-8 -*-

"""Prepare parts of the energy balance of Germany and its federal states.

Copyright (c) 2016-2019 Uwe Krien <krien@uni-bremen.de>

SPDX-License-Identifier: MIT
"""
__copyright__ = "Uwe Krien <krien@uni-bremen.de>"
__license__ = "MIT"


# Python libraries
import os
import logging

# Internal modules
from reegis import config as cfg
from reegis import inhabitants
from reegis import geometries

# External packages
import pandas as pd
import requests


def get_eb_index_translation_dict():
    dic = cfg.get_dict('EB_INDEX_TRANSLATION')
    dic_keys = list(dic.keys())
    for key in dic_keys:
        for keyword in ['Umw-Einsatz', 'Umw-Ausstoß', 'Umw-Verbrauch']:
            if keyword in key:
                value = dic.pop(key)
                key = key.replace(keyword, keyword + ':')
                dic[key] = value
        if dic[key] == '':
            value = key
            value = value.replace('Umw-Einsatz', 'transformation input')
            value = value.replace('Umw-Ausstoß', 'transformation output')
            value = value.replace('Umw-Verbrauch', 'transformation demand')
            dic[key] = value
    return dic


def get_de_balance(year):
    """Download and return energy balance of germany for a given year."""
    url = cfg.get('energy_balance', 'url_energy_balance_germany')
    req = requests.get(url.format(year=str(year)[-2:], suffix='xls'))

    if int(req.headers['Content-length']) > 0:
        fn_de = os.path.join(
            cfg.get('paths', 'energy_balance'),
            cfg.get('energy_balance', 'energy_balance_de_original')
        ).format(year=year, suffix='xls')
        with open(fn_de, 'wb') as fout:
            fout.write(req.content)
    else:
        req = requests.get(url.format(year=str(year)[-2:], suffix='xlsx'))
        if int(req.headers['Content-length']) > 0:
            fn_de = os.path.join(
                cfg.get('paths', 'energy_balance'),
                cfg.get('energy_balance', 'energy_balance_de_original')
            ).format(year=year, suffix='xlsx')
            with open(fn_de, 'wb') as fout:
                fout.write(req.content)
        else:
            raise ValueError("No file received. Check url.")
    fn_h = os.path.join(
        cfg.get('paths', 'static_sources'),
        'energy_balance_header_germany.csv')
    head = pd.read_csv(fn_h, header=[0]).columns

    df = pd.read_excel(fn_de, 'tj', index_col=[0], skiprows=6)
    df.columns = head[1:]
    return df


def get_de_usage_balance(year, grouped=False):
    """

    Parameters
    ----------
    year
    grouped

    Returns
    -------

    Examples
    --------
    >>> df = get_de_usage_balance(2015, True)
    >>> df.loc['total', 'total']
    8898093
    """
    df = get_de_balance(year)
    df['Braunkohle (sonstige)'] += df['Hartbraunkohle']
    df.drop(['Hartbraunkohle', 'primär (gesamt)', 'sekundär (gesamt)', 'Row'],
            axis=1, inplace=True)
    df = df.rename(columns=cfg.get_dict('COLUMN_TRANSLATION'))
    df = df.rename(cfg.get_dict('SECTOR'))
    df = df.loc[set(cfg.get_dict('SECTOR_OLD').values())]
    if grouped:
        df = df.groupby(by=cfg.get_dict('FUEL_GROUPS'), axis=1).sum()
    return df


def get_domestic_retail_share(year, grouped=False):
    """

    Parameters
    ----------
    year
    grouped

    Returns
    -------

    Examples
    --------
    >>> df = get_domestic_retail_share(2014, True)
    >>> df.loc['district heating', 'domestic']
    0.73
    """
    deb = get_de_usage_balance(year=year, grouped=grouped)
    deb.sort_index(1, inplace=True)

    # deb = deb.groupby(level=[1]).sum()

    share = pd.DataFrame()
    share['domestic'] = (deb.loc['domestic'] /
                         deb.loc['domestic and retail']
                         ).round(2)
    share['retail'] = (deb.loc['retail'] /
                       deb.loc['domestic and retail']).round(2).transpose()
    return share


def get_states_energy_balance(year=None):
    """
    Get the energy balance for a given year. The input file is the csv-file
    downloaded from:
    https://www.lak-energiebilanzen.de/eingabe-dynamisch/?a=e900

    Parameters
    ----------
    year : int or None
        If year is None all possible years will be returned.

    Returns
    -------
    pandas.DataFrame

    Notes
    -----
    Translation of the index is incomplete.

    Examples
    --------
    >>> eb = get_states_energy_balance(2012)
    >>> eb.loc[(['BB', 'NW'], 'extraction'), 'lignite (raw)'].round(1)
    BB  extraction    316931.2
    NW  extraction    927025.0
    Name: lignite (raw), dtype: float64
    >>> eb = get_states_energy_balance()
    >>> eb.loc[([2012, 2013], ['BB', 'NW'], 'extraction'), 'lignite (raw)'
    ...     ].round(1).sort_index()
    2012  BB  extraction    316931.2
          NW  extraction    927025.0
    2013  BB  extraction    318703.2
          NW  extraction    894546.0
    Name: lignite (raw), dtype: float64
    """
    header_fn = os.path.join(
        cfg.get('paths', 'static_sources'),
        cfg.get('energy_balance', 'energy_balance_header'))
    header = pd.read_csv(header_fn)

    if os.path.sep not in cfg.get('energy_balance', 'energy_balance_states'):
        fn = os.path.join(cfg.get('paths', 'static_sources'),
                          cfg.get('energy_balance', 'energy_balance_states'))
    else:
        fn = cfg.get('energy_balance', 'energy_balance_states')

    eb = pd.read_csv(fn, sep=';', skiprows=4, index_col=[0, 1, 2],
                     skipfooter=10, engine='python')
    eb.columns = header.columns
    codes = {
        'Baden-Württemberg': 'BW',
        'Bayern': 'BY',
        'Berlin': 'BE',
        'Brandenburg': 'BB',
        'Bremen': 'HB',
        'Hamburg': 'HH',
        'Hessen': 'HE',
        'Mecklenburg-Vorpommern': 'MV',
        'Niedersachsen': 'NI',
        'Nordrhein-Westfalen': 'NW',
        'Rheinland-Pfalz': 'RP',
        'Saarland': 'SL',
        'Sachsen': 'SN',
        'Sachsen-Anhalt': 'ST',
        'Schleswig-Holstein': 'SH',
        'Thüringen': 'TH'}

    fs_list = [codes[x] for x in eb.index.get_level_values(0).unique()]
    eb.index.set_levels(fs_list, level=0, inplace=True)
    eb = eb.fillna(0)
    eb.drop(['Anmerkung', 'Stand'], axis=1, inplace=True)
    eb = eb.swaplevel(0, 1)
    eb.index = eb.index.rename(['', '', ''])
    eb = eb.rename(columns=cfg.get_dict('COLUMN_TRANSLATION'))
    eb = eb.rename(index=get_eb_index_translation_dict(), level=2)
    if year is not None:
        eb = eb.loc[year]
    return eb


def get_usage_balance(year, grouped=False):
    """
    Get the usage part of the energy balance.

    Parameters
    ----------
    year : int
        Year of the energy balance.
    grouped : bool
        If set to True the fuels will be grouped to main groups like hard coal
        or lignite.

    Returns
    -------
    pandas.DataFrame

    Examples
    --------
    >>> year = 2013
    >>> cb = get_usage_balance(year)
    >>> total = cb.pop('total')
    >>> int((cb.loc['BE'].sum(axis=1) - total.loc['BE']).sum())
    0
    >>> int((cb.loc['ST'].sum(axis=1) - total.loc['ST']).sum())
    -8952
    >>> int((cb.loc['BY'].sum(axis=1) - total.loc['BY']).sum())
    -17731
    >>> cb = get_usage_balance(year)
    >>> cb = fix_usage_balance(cb, year)
    >>> total = cb.pop('total')
    >>> int((cb.loc['BE'].sum(axis=1) - total.loc['BE']).sum())
    0
    >>> int((cb.loc['ST'].sum(axis=1) - total.loc['ST']).sum())
    0
    >>> int((cb.loc['BY'].sum(axis=1) - total.loc['BY']).sum())
    0
    """
    eb = get_states_energy_balance(year)
    eb = eb.loc[
        (slice(None), list(cfg.get_dict('SECTOR').keys())), slice(None)]
    eb = eb.rename(index=cfg.get_dict('SECTOR'), level=1)
    if grouped:
        eb = eb.groupby(by=cfg.get_dict('FUEL_GROUPS'), axis=1).sum()
    return eb


def fix_usage_balance(eb, year):
    """
    Fixes the energy balances after analysing them. This is done manually.
    """
    if year not in [2012, 2013, 2014]:
        raise ValueError("You cannot edit the balance for year {0}.".format(
            year))
    # ******************************************************************
    # Bavaria (Bayern) - Missing coal values
    # Difference between fuel sum and LAK table
    missing = {2012: 10529, 2013: 8995, 2014: 9398}

    fix = missing[year]
    # the missing value is added to 'hard coal raw' even though it is not
    # specified which hard coal product is missing.
    eb.loc[('BY', 'total'), 'hard coal (raw)'] = fix

    # There is a small amount specified in the 'domestic and retail'
    # sector.
    dom_retail = eb.loc[('BY', 'domestic and retail'),
                        'hard coal (raw)']

    # The rest of the total hard coal consumption comes from the industrial
    # sector.
    eb.loc[('BY', 'industrial'), 'hard coal (raw)'] = fix - dom_retail

    # ******************************************************************
    # Berlin (Berlin) - corrected values for domestic gas and electricity
    # In new publications (e.g. LAK table) these values have changed. The newer
    # values will be used.
    if year == 2013 or year == 2012:
        electricity = {2012: 9150, 2013: 7095}
        gas = {2012: -27883, 2013: -13317}
        total = {2012: -18733, 2013: -6222}
        for row in ['total', 'domestic and retail', 'retail']:
            eb.loc[('BE', row), 'electricity'] += electricity[year]
            eb.loc[('BE', row), 'natural gas'] += gas[year]
            eb.loc[('BE', row), 'total'] += total[year]

    # ******************************************************************
    # Saxony-Anhalt (Sachsen Anhalt) - missing values for hard coal, oil and
    # other depending on the year. Due to a lack of information the
    # difference
    # will be halved between the sectors.
    missing = {2012: 5233, 2013: 4396, 2014: 3048}

    if year == 2012:
        fix = missing[year]
        # the missing value is added to 'hard coal raw' even though it is not
        # specified which hard coal product is missing.
        eb.loc[('ST', 'industrial'), 'other'] += fix / 2
        eb.loc[('ST', 'industrial'), 'hard coal (raw)'] += fix / 2

        # There is a small amount specified in the 'domestic and retail'
        # sector.
        dom_retail_hc = eb.loc[('ST', 'domestic and retail'),
                               'hard coal (raw)']

        # The rest of the total hard coal consumption comes from the industrial
        # sector.
        eb.loc[('ST', 'total'), 'other'] += fix / 2
        eb.loc[('ST', 'total'), 'hard coal (raw)'] += fix / 2 + dom_retail_hc

    if year == 2013:
        fix = missing[year]
        # the missing value is added to 'hard coal raw' even though it is not
        # specified which hard coal product is missing.
        eb.loc[('ST', 'industrial'), 'mineral oil products'] += fix / 2
        eb.loc[('ST', 'industrial'), 'hard coal (raw)'] += fix / 2

        # There is a small amount specified in the 'domestic and retail'
        # sector.
        dom_retail_hc = eb.loc[('ST', 'domestic and retail'),
                               'hard coal (raw)']
        dom_retail_oil = eb.loc[('ST', 'domestic and retail'),
                                'mineral oil products']
        # The rest of the total hard coal consumption comes from the industrial
        # sector.
        eb.loc[('ST', 'total'), 'mineral oil products'] += fix / 2 + (
            dom_retail_oil)
        eb.loc[('ST', 'total'), 'hard coal (raw)'] += fix / 2 + dom_retail_hc

    if year == 2014:
        fix = missing[year]
        # the missing value is added to 'hard coal raw' even though it is not
        # specified which hard coal product is missing.
        eb.loc[('ST', 'industrial'), 'mineral oil products'] += fix / 2
        eb.loc[('ST', 'industrial'), 'hard coal (coke)'] += fix / 2

        # There is a small amount specified in the 'domestic and retail'
        # sector.
        dom_retail = eb.loc[('ST', 'domestic and retail'),
                            'mineral oil products']

        # The rest of the total hard coal consumption comes from the industrial
        # sector.
        eb.loc[('ST', 'total'), 'mineral oil products'] += fix / 2 + dom_retail
        eb.loc[('ST', 'total'), 'hard coal (coke)'] += fix / 2

    return eb


def get_transformation_balance(year):
    """
    Reshape the energy balance and return the transformation part as a
    MultiIndex
    DataFrame.

    Parameters
    ----------
    year : int

    Returns
    -------
    pandas.DataFrame

    Examples
    --------
    >>> year = 2014
    >>> ub = get_transformation_balance(year)
    >>> int(ub.loc[('BB', 'input', 'Heizwerke'), 'total'])
    0
    >>> ub = fix_transformation_balance(ub)
    >>> int(ub.loc[('BB', 'input', 'Heizwerke'), 'total'])
    5347
    """
    eb = get_states_energy_balance(year)
    eb = eb.groupby(by=cfg.get_dict('FUEL_GROUPS'), axis=1).sum()
    my_index = pd.MultiIndex(levels=[[], [], []], codes=[[], [], []])
    cb = pd.DataFrame(index=my_index, columns=eb.columns)

    for i in eb.iterrows():
        if 'transformation input:' in i[0][1]:
            cb.loc[i[0][0], 'input', i[0][1].replace(
                'transformation input: ', '')] = i[1]
        elif 'transformation output:' in i[0][1]:
            cb.loc[i[0][0], 'output', i[0][1].replace(
                'transformation output: ', '')] = i[1]
        elif 'Primär' in i[0][1]:
            cb.loc[i[0][0], 'primary', i[0][1]] = i[1]
        elif 'Energieangebot' in i[0][1]:
            cb.loc[i[0][0], 'tender', i[0][1]] = i[1]
        elif 'Endenergieverbrauch' in i[0][1]:
            cb.loc[i[0][0], 'usage', i[0][1]] = i[1]
    cb.sort_index(inplace=True)
    return cb


def check_transformation_balance(years=None, balance=None, path=None):
    """
    Checks the balance of the transformation balance. If the difference is
    greater than 5 the name of the region and the difference will be printed.
    If a path is given wrong balances will be stored as an excel sheet in this
    path. One excel table for each year will be created.

    Parameters
    ----------
    years : list
        List of years to check.
    balance : pandas.DataFrame (optional)
        A valid transformation balance to check.
    path : str
        A directory where the regions

    Examples
    --------
    >>> check_transformation_balance([2014])
    2014 - BB: 460589
    2014 - BW: 706972
    2014 - BY: 2288252
    2014 - MV: 19242
    2014 - NI: 705997
    2014 - SH: 377561
    2014 - ST: 51495
    >>> ub = get_transformation_balance(2014)
    >>> ub = check_transformation_balance(balance=ub)
    nn - BB: 460589
    nn - BW: 706972
    nn - BY: 2288252
    nn - MV: 19242
    nn - NI: 705997
    nn - SH: 377561
    nn - ST: 51495
    """
    if balance is not None:
        years = ['nn']
        cb = balance
        cb_orig = cb.copy()
    else:
        cb = None
        cb_orig = None

    writer = None
    fn = None

    for year in years:
        if balance is None:
            cb = get_transformation_balance(int(year))
            cb_orig = cb.copy()
        if path is not None:
            fn = os.path.join(path, 'check_{0}.xls'.format(year))
            writer = pd.ExcelWriter(fn)
        total = cb.pop('total')
        for region in cb.index.get_level_values(0).unique():
            value = (cb.loc[region].sum(axis=1) - total.loc[region]).sum()
            if abs(value) > 5:
                if path is not None:
                    cb_orig.loc[region].to_excel(writer, region)
                else:
                    print('{0} - {1}: {2}'.format(
                        year, region, int(abs(value))))
        if path is not None:
            writer.save()
            logging.info("File saved to {0}".format(fn))
    if balance is not None:
        return cb_orig
    else:
        return None


def fix_transformation_balance(eb):
    """
    This is a fix after a manual analysis of the energy balances.

    Use with care and check the results.,
    """
    # *********** BB ********************************************************
    # BB: Total input calculated by total output
    # BB: Gas input calculated by total input - sum input without gas.
    eb.loc['BB', 'input', 'Heizwerke']['total'] = (
        eb.loc['BB', 'output', 'Heizwerke']['total'] * 0.9
    )
    total = eb.loc['BB', 'input', 'Heizwerke']['total']
    eb.loc['BB', 'input', 'Heizwerke']['gas'] = (
            total - eb.loc['BB', 'input', 'Heizwerke'].sum() + total)

    # *********** BY ********************************************************
    # BY: The missing fuel for CHP is assumed to be hard coal.
    kwk_row = 'Heizkraftwerke der allgemeinen Versorgung (nur KWK)'
    total = eb.loc['BY', 'input', kwk_row]['total']
    eb.loc['BY', 'input', kwk_row]['hard coal'] = (
        total - eb.loc['BY', 'input', kwk_row].sum() + total)

    # BY: The missing fuel for heat plants is assumed to be natural gas.
    total = eb.loc['BY', 'input', 'Heizwerke']['total']
    eb.loc['BY', 'input', 'Heizwerke']['gas'] = (
            total - eb.loc['BY', 'input', 'Heizwerke'].sum() + total)
    return eb


def get_transformation_balance_by_region(
        regions, year, name='region', fix=False):
    """
    Get the transformation part of the energy balance for a given region set.
    The values will be recalculated by the number of inhabitants.

    Parameters
    ----------
    year : int
    regions : GeoDataFrame
    name : str
    fix : bool

    Returns
    -------
    pandas.DataFrame

    Examples
    --------
    >>> cb_orig = get_transformation_balance(2014)
    >>> regions = geometries.load(
    ...     cfg.get('paths', 'geometry'),
    ...     cfg.get('geometry', 'de21_polygons'))
    >>> cb = get_transformation_balance_by_region(regions, 2014, 'de21')
    >>> int(cb.sum()['electricity']) == int(cb_orig.sum()['electricity'])
    True
    """
    cb = get_transformation_balance(year)
    if fix is True:
        cb = fix_transformation_balance(cb)
    # create empty DataFrame to take the transformation balance for the regions
    my_index = pd.MultiIndex(levels=[[], [], []], codes=[[], [], []])
    cb_new = pd.DataFrame(index=my_index, columns=cb.columns)

    # Use the number of inhabitants to reshape the balance to the new regions
    logging.debug(
        "Fetching inhabitants table to reshape the transformation balance.")
    ew = inhabitants.get_share_of_federal_states_by_region(year, regions, name)

    # Loop over the deflex regions
    for region in sorted(ew.index.get_level_values(0).unique()):
        # Get all states that intersects with the current deflex-region
        states = ew.loc[region].index

        # Sum up the fraction of each state-table to get the new region table
        for idx in cb.loc[states[0]].index:
            cb_new.loc[region, idx[0], idx[1]] = 0
            for state in states:
                share = ew.loc[region, state]
                cb_new.loc[region, idx[0], idx[1]] += (
                    cb.loc[state, idx[0], idx[1]] * float(share))

    return cb_new


if __name__ == "__main__":
    pass
