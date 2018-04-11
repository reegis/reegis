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
import numpy as np

# oemof libraries
import oemof.tools.logger

# Internal modules
import reegis_tools.config as cfg
import reegis_tools.opsd as opsd
import reegis_tools.energy_balance as energy_balance
import reegis_tools.geometries as geo


def patch_offshore_wind(orig_df, columns):
    df = pd.DataFrame(columns=columns)

    offsh = pd.read_csv(
        os.path.join(cfg.get('paths', 'static_sources'),
                     cfg.get('static_sources', 'patch_offshore_wind')),
        header=[0, 1], index_col=[0])
    offsh = offsh.loc[offsh['reegis', 'com_year'].notnull(), 'reegis']
    for column in offsh.columns:
        df[column] = offsh[column]
    df['decom_year'] = 2050
    df['decom_month'] = 12
    df['energy_source_level_1'] = 'Renewable energy'
    df['energy_source_level_2'] = 'Wind'
    df['energy_source_level_3'] = 'Offshore'
    goffsh = geo.Geometry(name="Offshore wind patch", df=df)
    goffsh.create_geo_df()

    # Add column with region names of the model_region
    new_col = 'federal_states'
    if new_col in goffsh.gdf:
        del goffsh.gdf[new_col]
    federal_states = geo.Geometry(new_col)
    federal_states.load(cfg.get('paths', 'geometry'),
                        cfg.get('geometry', 'federalstates_polygon'))
    goffsh.gdf = geo.spatial_join_with_buffer(goffsh, federal_states)

    # Add column with coastdat id
    new_col = 'coastdat2'
    if new_col in goffsh.gdf:
        del goffsh.gdf[new_col]
    coastdat = geo.Geometry(new_col)
    coastdat.load(cfg.get('paths', 'geometry'),
                  cfg.get('coastdat', 'coastdatgrid_polygon'))
    goffsh.gdf = geo.spatial_join_with_buffer(goffsh, coastdat)
    offsh_df = goffsh.get_df()

    new_cap = offsh_df['capacity'].sum()
    old_cap = orig_df.loc[orig_df['technology'] == 'Offshore',
                          'capacity'].sum()

    # Remove Offshore technology from power plant table
    orig_df = orig_df.loc[orig_df['technology'] != 'Offshore']

    patched_df = pd.DataFrame(pd.concat([orig_df, offsh_df],
                                        ignore_index=True))
    logging.warning(
        "Offshore wind is patched. {0} MW were replaced by {1} MW".format(
            old_cap, new_cap))
    return patched_df


def pp_opsd2reegis(offshore_patch=True):
    """
    Adapt opsd power plants to a more generalised reegis API with a reduced
    number of columns

    Parameters
    ----------
    offshore_patch : bool
        Will overwrite the offshore wind power plants with own data set if set
        to True.

    Returns
    -------
    str : Filename of the stored file.
    """
    filename_in = os.path.join(cfg.get('paths', 'opsd'),
                               cfg.get('opsd', 'opsd_prepared'))
    filename_out = os.path.join(cfg.get('paths', 'powerplants'),
                                cfg.get('powerplants', 'reegis_pp'))

    keep_cols = {'decom_year', 'comment', 'chp', 'energy_source_level_1',
                 'thermal_capacity', 'com_year', 'com_month',
                 'chp_capacity_uba', 'energy_source_level_3', 'decom_month',
                 'geometry', 'energy_source_level_2', 'capacity', 'technology',
                 'federal_states', 'com_year', 'coastdat2', 'efficiency'}

    string_cols = ['chp', 'comment', 'energy_source_level_1',
                   'energy_source_level_2', 'energy_source_level_3',
                   'federal_states', 'geometry', 'technology']

    # Create opsd power plant tables if they do not exist.
    if not os.path.isfile(filename_in):
        msg = "File '{0}' does not exist. Will create it from source files."
        logging.debug(msg.format(filename_in))
        filename_in = opsd.opsd_power_plants()
    else:
        complete = True
        for cat in ['renewable', 'conventional']:
            try:
                pd.read_hdf(filename_in, cat, mode='r')
            except KeyError:
                msg = "File '{0}' exists but key '{1}' is not present."
                logging.debug(msg.format(filename_in, cat))
                complete = False
        if not complete:
            logging.debug("Will re-create file with all keys.")
            filename_in = opsd.opsd_power_plants(overwrite=True)
    #
    pp = {}
    for cat in ['renewable', 'conventional']:
        # Read opsd power plant tables
        pp[cat] = pd.read_hdf(filename_in, cat, mode='r')

        # Patch offshore wind energy with investigated data.
        if cat == 'renewable' and offshore_patch:
            pp[cat] = patch_offshore_wind(pp[cat], keep_cols)

        pp[cat] = pp[cat].drop(columns=set(pp[cat].columns) - keep_cols)

        # Replace 'nan' strings with nan values.
        pp[cat] = pp[cat].replace('nan', np.nan)

        # Remove lines with comments. Comments mark suspicious data.
        pp[cat] = pp[cat].loc[pp[cat].comment.isnull()]

        # Fill missing 'energy_source_level_1' values with 'unknown' and
        # the category from opsd.
        pp[cat]['energy_source_level_1'] = (
            pp[cat]['energy_source_level_1'].fillna(
                'unknown from {0}'.format(cat)))

        # Fill missing 'energy_source_level_2' values with values from
        # 'energy_source_level_1' column.
        pp[cat]['energy_source_level_2'] = (
            pp[cat]['energy_source_level_2'].fillna(
                pp[cat]['energy_source_level_1']))

    pp = pd.DataFrame(pd.concat([pp['renewable'], pp['conventional']],
                                ignore_index=True))

    # Merge 'chp_capacity_uba' into 'thermal_capacity' column.
    pp['thermal_capacity'] = pp['thermal_capacity'].fillna(
        pp['chp_capacity_uba'])
    del pp['chp_capacity_uba']

    # Remove storages (Speicher) from power plant table
    pp = pp.loc[pp['energy_source_level_2'] != 'Speicher']

    # Convert all values to strings in string-columns
    pp[string_cols] = pp[string_cols].astype(str)

    # Store power plant table to hdf5 file.
    pp.to_hdf(filename_out, 'pp', mode='w')

    logging.info("Reegis power plants based on opsd stored in {0}".format(
        filename_out))
    return filename_out


def add_capacity_by_year(year, pp=None, filename=None, key='pp'):
    if pp is None:
        pp = pd.read_hdf(filename, key, mode='r')
    
    filter_cap_col = 'capacity_{0}'.format(year)

    # Get all powerplants for the given year.
    c1 = (pp['com_year'] < year) & (pp['decom_year'] > year)
    pp.loc[c1, filter_cap_col] = pp.loc[c1, 'capacity']

    c2 = pp['com_year'] == year
    pp.loc[c2, filter_cap_col] = (pp.loc[c2, 'capacity'] *
                                  (12 - pp.loc[c2, 'com_month']) / 12)
    c3 = pp['decom_year'] == year
    pp.loc[c3, filter_cap_col] = (pp.loc[c3, 'capacity'] *
                                  pp.loc[c3, 'com_month'] / 12)
    return pp


def add_capacity_in(pp):
    """Add a column to the conventional power plants to make it possible to
    calculate an average efficiency for the summed up groups.
    """
    # Calculate the inflow capacity for power plants with an efficiency value.
    pp['capacity_in'] = pp['capacity'].div(pp['efficiency'])

    # Sum up the valid in/out capacities to calculate an average efficiency
    cap_valid = pp.loc[pp['efficiency'].notnull(), 'capacity'].sum()
    cap_in = pp.loc[pp['efficiency'].notnull(), 'capacity_in'].sum()

    # Set the average efficiency for missing efficiency values
    pp['efficiency'] = pp['efficiency'].fillna(
        cap_valid / cap_in)

    # Calculate the inflow for all power plants
    pp['capacity_in'] = pp['capacity'].div(pp['efficiency'])

    logging.info("'capacity_in' column added to power plant table.")
    return pp


def get_pp_by_year(year, capacity_in=False, overwrite_capacity=False):
    """

    Parameters
    ----------
    capacity_in : bool
        Set to True if a capactiy_in column is present.
    year : int
    overwrite_capacity : bool
        By default (False) a new column "capacity_<year>" is created. If set to
        True the old capacity column will be overwritten.

    Returns
    -------

    """
    filename = os.path.join(cfg.get('paths', 'powerplants'),
                            cfg.get('powerplants', 'reegis_pp'))
    logging.info("Get reegis power plants for {0}.".format(year))
    if not os.path.isfile(filename):
        msg = "File '{0}' does not exist. Will create it from reegis file."
        logging.debug(msg.format(filename))
        filename = pp_opsd2reegis()
    pp = pd.read_hdf(filename, 'pp', mode='r')

    filter_columns = ['capacity_{0}']

    if capacity_in:
        pp = add_capacity_in(pp)
        filter_columns.append('capacity_in_{0}')

    # Get all powerplants for the given year.
    # If com_month exist the power plants will be considered month-wise.
    # Otherwise the commission/decommission within the given year is not
    # considered.
    for fcol in filter_columns:
        filter_column = fcol.format(year)
        orig_column = fcol[:-4]
        c1 = (pp['com_year'] < year) & (pp['decom_year'] > year)
        pp.loc[c1, filter_column] = pp.loc[c1, orig_column]

        c2 = pp['com_year'] == year
        pp.loc[c2, filter_column] = (pp.loc[c2, orig_column] *
                                     (12 - pp.loc[c2, 'com_month']) / 12)
        c3 = pp['decom_year'] == year
        pp.loc[c3, filter_column] = (pp.loc[c3, orig_column] *
                                     pp.loc[c3, 'com_month'] / 12)

        if overwrite_capacity:
            pp[orig_column] = 0
            pp[orig_column] = pp[filter_column]
            del pp[filter_column]

    return pp


def calculate_chp_share_and_efficiency(eb):
    """Efficiciency and fuel share of combined heat and power plants (chp) and
    heat plants (hp) from conversion balance."""
    row_chp = 'Heizkraftwerke der allgemeinen Versorgung (nur KWK)'
    row_hp = 'Heizwerke'
    row_total = 'Umwandlungsausstoß insgesamt'

    regions = list(eb.index.get_level_values(0).unique())
    eta = {}
    rows = ['Heizkraftwerke der allgemeinen Versorgung (nur KWK)',
            'Heizwerke']

    for region in regions:
        eta[region] = {}
        in_chp = eb.loc[region, 'input', row_chp]
        in_hp = eb.loc[region, 'input', row_hp]
        elec_chp = eb.loc[(region, 'output', row_chp), 'electricity']
        heat_chp = eb.loc[(region, 'output', row_chp),
                          'district heating']
        heat_hp = eb.loc[(region, 'output', row_hp),
                         'district heating']
        heat_total = eb.loc[(region, 'output', row_total),
                            'district heating']
        end_total_heat = eb.loc[(region, 'usage', 'Endenergieverbrauch'),
                                'district heating']
        eta[region]['sys_heat'] = end_total_heat / heat_total

        eta[region]['hp'] = float(heat_hp / in_hp.total)
        eta[region]['heat_chp'] = heat_chp / in_chp.total
        eta[region]['elec_chp'] = elec_chp / in_chp.total

        eta[region]['fuel_share'] = eb.loc[region, 'input', rows].div(
            eb.loc[region, 'input', rows].total.sum(), axis=0)

    return eta


def get_chp_share_and_efficiency_states(year):
    conversion_blnc = energy_balance.get_conversion_balance(year)
    return calculate_chp_share_and_efficiency(conversion_blnc)


if __name__ == "__main__":
    oemof.tools.logger.define_logging()
    state = 'BE'

    pwp = get_pp_by_year(2014, overwrite_capacity=True)
    e_sources = (pwp.loc[
        (pwp.federal_states == state), 'energy_source_level_2']).unique()

    print(e_sources)

    for e_source in e_sources:
        cap = pwp.loc[
            (pwp.federal_states == state) &
            (pwp.energy_source_level_2 == e_source)].sum()['capacity']
        print(e_source, ':', round(cap))
    exit(0)
    gpp = geo.Geometry(name="Power plants Berlin", df=pwp)
    gpp.create_geo_df()
    gpp.gdf.to_file('/home/uwe/berlin_pp_temp.shp')
    exit(0)
    print(pwp.loc[pwp.federal_states == 'BE'].to_excel(
        '/home/uwe/berlin_pp_temp.xlsx'))

    # file_name = pp_opsd2reegis()
    file_name = '/home/uwe/express/reegis/data/powerplants/reegis_pp.h5'
    pwp = pd.read_hdf(file_name, 'pp')
    print(pwp.loc[pwp.federal_states == 'BE'].groupby(
        'energy_source_level_2').sum())
    exit(0)
    file_name = os.path.join(cfg.get('paths', 'powerplants'),
                             cfg.get('powerplants', 'reegis_pp'))
    dtf = pd.read_hdf(file_name, 'pp', mode='r')
    for col in dtf.columns:
        print(col, dtf[col].unique())
