# -*- coding: utf-8 -*-

"""Prepare parts of the energy balance of Germany and its federal states.

Copyright (c) 2016-2018 Uwe Krien <uwe.krien@rl-institut.de>

SPDX-License-Identifier: GPL-3.0-or-later
"""
__copyright__ = "Uwe Krien <uwe.krien@rl-institut.de>"
__license__ = "GPLv3"


# Python libraries
import os
import logging

# External packages
import pandas as pd

# oemof packages
from oemof.tools import logger

# internal modules
import reegis_tools.config as cfg


def check_balance(orig, ebfile):
    logging.info('Analyse the energy balances')

    years = [2012, 2013, 2014]
    # energy balance
    file_type = ebfile.split('.')[1]
    if file_type == 'xlsx' or file_type == 'xls':
        eb = pd.read_excel(ebfile, index_col=[0, 1, 2]).fillna(0)
    elif file_type == 'csv':
        eb = pd.read_csv(ebfile, index_col=[0, 1, 2]).fillna(0)
    else:
        logging.error('.{0} is an invalid suffix.'.format(file_type))
        logging.error('Cannot load {0}'.format(ebfile))
        eb = None
        exit(0)
    eb.rename(columns=cfg.get_dict('COLUMN_TRANSLATION'), inplace=True)
    eb.sort_index(0, inplace=True)
    eb = eb.apply(lambda x: pd.to_numeric(x, errors='coerce')).fillna(0)
    eb = eb.groupby(by=cfg.get_dict('FUEL_GROUPS'), axis=1).sum()

    # sum table (fuel)
    ftfile = os.path.join(cfg.get('paths', 'static_sources'),
                          'sum_table_fuel_groups.xlsx')
    ft = pd.read_excel(ftfile)
    states = cfg.get_dict('STATES')
    ft['Bundesland'] = ft['Bundesland'].apply(lambda x: states[x])
    ft.set_index(['Jahr', 'Bundesland'], inplace=True)
    ft.rename(columns=cfg.get_dict('SUM_COLUMNS'), inplace=True)
    ft.sort_index(inplace=True)

    # sum table (sector)
    stfile = os.path.join(cfg.get('paths', 'static_sources'),
                          'sum_table_sectors.xlsx')

    st = pd.read_excel(stfile)
    st['Bundesland'] = st['Bundesland'].apply(lambda x: states[x])
    st.set_index(['Jahr', 'Bundesland'], inplace=True)
    st.rename(columns=cfg.get_dict('SECTOR_SHORT'), inplace=True)
    st.sort_index(inplace=True)
    del st['Anm.']

    if orig:
        outfile = os.path.join(cfg.get('paths', 'messages'),
                               'energy_balance_check_original.xlsx')
    else:
        outfile = os.path.join(cfg.get('paths', 'messages'),
                               'energy_balance_check_edited.xlsx')

    writer = pd.ExcelWriter(outfile)

    for year in years:
        # Compare sum of fuel groups with LAK-table
        endenergie_check = pd.DataFrame()
        for col in ft.columns:
            ft_piece = ft.loc[(year, slice(None)), col]
            ft_piece.index = ft_piece.index.droplevel([0])
            ft_piece = ft_piece.apply(lambda x: pd.to_numeric(x,
                                                              errors='coerce'))
            try:
                eb_piece = eb.loc[(year, slice(None), 'Endenergieverbrauch'),
                                  col]
            except KeyError:
                eb_piece = eb.loc[(year, slice(None), 'total'), col]
            eb_piece.index = eb_piece.index.droplevel([0, 2])
            endenergie_check[col] = ft_piece-eb_piece.round()

        endenergie_check['check'] = (endenergie_check.sum(1) -
                                     2 * endenergie_check['total'])
        endenergie_check.loc['all'] = endenergie_check.sum()
        endenergie_check.to_excel(writer, 'fuel_groups_{0}'.format(year),
                                  freeze_panes=(1, 1))

        # Compare subtotal of transport, industrial and domestic and retail
        # with the total of end-energy
        endenergie_summe = pd.DataFrame()

        if orig:
            main_cat = [
                'Haushalte, Gewerbe, Handel, Dienstleistungen,'
                ' übrige Verbraucher', 'Verkehr insgesamt',
                'Gewinngung und verarbeitendes Gewerbe']
            total = 'Endenergieverbrauch'
        else:
            main_cat = [
                    'domestic and retail', 'transport',
                    'industrial']
            total = 'total'
        for state in eb.index.get_level_values(1).unique():
            try:
                tmp = pd.DataFrame()
                n = 0
                for idx in main_cat:
                    n += 1
                    tmp[state, n] = eb.loc[year, state, idx]
                tmp = (tmp.sum(1) - eb.loc[year, state, total]
                       ).round()

                endenergie_summe[state] = tmp
            except KeyError:
                endenergie_summe[state] = None
        endenergie_summe.transpose().to_excel(
            writer, 'internal sum check {0}'.format(year), freeze_panes=(1, 1))

        # Compare sum of sector groups with LAK-table
        eb_fuel = (eb[['hard coal',  'lignite',  'oil',  'gas', 're',
                       'electricity', 'district heating', 'other']])

        eb_fuel = eb_fuel.sum(1)
        eb_sector = eb_fuel.round().unstack()
        eb_sector.rename(columns=cfg.get_dict('SECTOR_SHORT'), inplace=True)
        eb_sector.rename(columns=cfg.get_dict('SECTOR_SHORT_EN'), inplace=True)
        try:
            del eb_sector['ghd']
            del eb_sector['dom']
        except KeyError:
            del eb_sector['retail']
            del eb_sector['domestic']
        eb_sector = eb_sector.sort_index(1).loc[year]

        st_year = st.sort_index(1).loc[year]
        st_year.index = st_year.index
        st_year = st_year.apply(
            lambda x: pd.to_numeric(x, errors='coerce')).fillna(0)
        (eb_sector.astype(int) - st_year.astype(int)).to_excel(
            writer, 'sector_groups_{0}'.format(year), freeze_panes=(1, 1))

        # Compare the sum of the columns with the "total" column.
        sum_check_hrz = pd.DataFrame()
        for row in eb.index.get_level_values(2).unique():
            eb.sort_index(0, inplace=True)
            summe = (eb.loc[(year, slice(None), row)]).sum(1)
            ges = (eb.loc[(year, slice(None), row), 'total'])

            tmp_check = round(summe - 2 * ges)
            tmp_check.index = tmp_check.index.droplevel(0)
            tmp_check.index = tmp_check.index.droplevel(1)
            sum_check_hrz[row] = tmp_check
        sum_check_hrz.to_excel(
                writer, 'sum_check_hrz_{0}'.format(year), freeze_panes=(1, 1))

        # Check states
        for state, abr in states.items():
            if abr not in eb.loc[year].index.get_level_values(0).unique():
                logging.warning(
                    '{0} ({1}) not present in the {2} balance.'.format(
                        state, abr, year))

    writer.save()


def edit_balance():
    """Fixes the energy balances after analysing them. This is done manually.
    """

    # Read energy balance table
    ebfile = os.path.join(cfg.get('paths', 'static_sources'),
                          cfg.get('energy_balance', 'energiebilanzen_laender'))
    eb = pd.read_excel(ebfile, index_col=[0, 1, 2]).fillna(0)
    eb.rename(columns=cfg.get_dict('COLUMN_TRANSLATION'), inplace=True)
    eb.sort_index(0, inplace=True)
    eb = eb.apply(lambda x: pd.to_numeric(x, errors='coerce')).fillna(0)

    new_index_values = list()
    sector = cfg.get_dict('SECTOR')
    for value in eb.index.get_level_values(2):
        new_index_values.append(sector[value])
    eb.index.set_levels(new_index_values, level=2, inplace=True)

    # ************************************************************************
    # Bavaria (Bayern) - Missing coal values
    # Difference between fuel sum and LAK table
    missing = {2012: 10529, 2013: 8995}
    for y in [2012, 2013]:
        fix = missing[y]
        # the missing value is added to 'hard coal raw' even though it is not
        # specified which hard coal product is missing.
        eb.loc[(y, 'BY', 'total'), 'hard coal (raw)'] = fix

        # There is a small amount specified in the 'domestic and retail'
        # sector.
        dom_retail = eb.loc[(y, 'BY', 'domestic and retail'),
                            'hard coal (raw)']

        # The rest of the total hard coal consumption comes from the industrial
        # sector.
        eb.loc[(y, 'BY', 'industrial'), 'hard coal (raw)'] = fix - dom_retail

    # ************************************************************************
    # Berlin (Berlin) - corrected values for domestic gas and electricity
    # In new publications (e.g. LAK table) these values have changed. The newer
    # values will be used.
    electricity = {2012: 9150, 2013: 7095}
    gas = {2012: -27883, 2013: -13317}
    total = {2012: -18733, 2013: -6223}
    for row in ['total', 'domestic and retail', 'retail']:
        for y in [2012, 2013]:
            eb.loc[(y, 'BE', row), 'electricity'] += electricity[y]
            eb.loc[(y, 'BE', row), 'natural gas'] += gas[y]
            eb.loc[(y, 'BE', row), 'total'] += total[y]

    # ************************************************************************
    # Saxony-Anhalt (Sachsen Anhalt) - missing values for hard coal, oil and
    # other depending on the year. Due to a lack of information the difference
    # will be halved between the sectors.
    missing = {2012: 5233, 2013: 4396, 2014: 3048}

    y = 2012
    fix = missing[y]
    # the missing value is added to 'hard coal raw' even though it is not
    # specified which hard coal product is missing.
    eb.loc[(y, 'ST', 'industrial'), 'waste (fossil)'] += fix / 2
    eb.loc[(y, 'ST', 'industrial'), 'hard coal (raw)'] += fix / 2

    # There is a small amount specified in the 'domestic and retail' sector.
    dom_retail_hc = eb.loc[(y, 'ST', 'domestic and retail'), 'hard coal (raw)']

    # The rest of the total hard coal consumption comes from the industrial
    # sector.
    eb.loc[(y, 'ST', 'total'), 'waste (fossil)'] += fix / 2
    eb.loc[(y, 'ST', 'total'), 'hard coal (raw)'] += fix / 2 + dom_retail_hc

    y = 2013
    fix = missing[y]
    # the missing value is added to 'hard coal raw' even though it is not
    # specified which hard coal product is missing.
    eb.loc[(y, 'ST', 'industrial'), 'mineral oil products'] += fix / 2
    eb.loc[(y, 'ST', 'industrial'), 'hard coal (raw)'] += fix / 2

    # There is a small amount specified in the 'domestic and retail' sector.
    dom_retail_hc = eb.loc[(y, 'ST', 'domestic and retail'), 'hard coal (raw)']
    dom_retail_oil = eb.loc[(y, 'ST', 'domestic and retail'),
                            'mineral oil products']
    # The rest of the total hard coal consumption comes from the industrial
    # sector.
    eb.loc[(y, 'ST', 'total'), 'mineral oil products'] += fix / 2 + (
        dom_retail_oil)
    eb.loc[(y, 'ST', 'total'), 'hard coal (raw)'] += fix / 2 + dom_retail_hc

    y = 2014
    fix = missing[y]
    # the missing value is added to 'hard coal raw' even though it is not
    # specified which hard coal product is missing.
    eb.loc[(y, 'ST', 'industrial'), 'mineral oil products'] += fix / 2
    eb.loc[(y, 'ST', 'industrial'), 'hard coal (coke)'] += fix / 2

    # There is a small amount specified in the 'domestic and retail' sector.
    dom_retail = eb.loc[(y, 'ST', 'domestic and retail'),
                        'mineral oil products']

    # The rest of the total hard coal consumption comes from the industrial
    # sector.
    eb.loc[(y, 'ST', 'total'), 'mineral oil products'] += fix / 2 + dom_retail
    eb.loc[(y, 'ST', 'total'), 'hard coal (coke)'] += fix / 2

    # ************************************************************************
    # Write results to table
    fname = os.path.join(cfg.get('paths', 'energy_balance'),
                         cfg.get('energy_balance', 'energy_balance_edited'))
    eb.to_csv(fname)
    return fname


def get_de_balance(year=None, grouped=False):
    fname_de = os.path.join(
        cfg.get('paths', 'static_sources'),
        cfg.get('energy_balance', 'energy_balance_de_original'))
    deb = pd.read_excel(fname_de, index_col=[0, 1, 2]).fillna(0)
    deb.rename(columns=cfg.get_dict('COLUMN_TRANSLATION'), inplace=True)
    deb.sort_index(0, inplace=True)
    deb = deb.apply(lambda x: pd.to_numeric(x, errors='coerce')).fillna(0)

    new_index_values = list()
    sector = cfg.get_dict('SECTOR')
    for value in deb.index.get_level_values(2):
        new_index_values.append(sector[value])
    deb.index.set_levels(new_index_values, level=2, inplace=True)

    if grouped:
        deb = deb.groupby(by=cfg.get_dict('FUEL_GROUPS'), axis=1).sum()
    deb.index = deb.index.set_names(['year', 'state', 'sector'])
    deb.sort_index(0, inplace=True)
    if year is not None:
        deb = deb.loc[year]
    return deb


def get_domestic_retail_share(year, grouped=False):
    deb = get_de_balance(year=year, grouped=grouped)
    deb.sort_index(1, inplace=True)

    deb = deb.groupby(level=[1]).sum()

    share = pd.DataFrame()
    share['domestic'] = (deb.loc['domestic'] /
                         deb.loc['domestic and retail']
                         ).round(2)
    share['retail'] = (deb.loc['retail'] /
                       deb.loc['domestic and retail']).round(2).transpose()
    return share


def get_states_balance(year=None, grouped=False, overwrite=False):
    fname = os.path.join(cfg.get('paths', 'energy_balance'),
                         cfg.get('energy_balance', 'energy_balance_edited'))
    if not os.path.isfile(fname) or overwrite:
        edit_balance()
    eb = pd.read_csv(fname, index_col=[0, 1, 2])
    if grouped:
        eb = eb.groupby(by=cfg.get_dict('FUEL_GROUPS'), axis=1).sum()
    eb.index = eb.index.set_names(['year', 'state', 'sector'])

    if year is not None:
        eb = eb.loc[year]

    return eb


if __name__ == "__main__":
    logger.define_logging()
    fn = os.path.join(cfg.get('paths', 'static_sources'),
                      cfg.get('energy_balance', 'energiebilanzen_laender'))
    check_balance(orig=True, ebfile=fn)
    fn = edit_balance()
    check_balance(orig=False, ebfile=fn)
    # print(get_de_balance(year=None, grouped=False).columns)
    # print(get_states_balance(2012, overwrite=True))
    # print(get_domestic_retail_share(2012))
