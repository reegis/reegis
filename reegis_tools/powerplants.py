"""
Processing a list of power plants in Germany.

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
from oemof.tools import logger

# Internal modules
import reegis_tools.config as cfg
import reegis_tools.opsd as opsd
import reegis_tools.geometries as geo


def patch_offshore_wind(orig_df, columns):
    df = pd.DataFrame(columns=columns)

    offsh = pd.read_csv(
        os.path.join(cfg.get('paths', 'static_sources'),
                     cfg.get('static_sources', 'patch_offshore_wind')),
        header=[0, 1], index_col=[0])
    offsh = offsh.loc[offsh['reegis', 'com_year'].notnull(), 'reegis']
    for col in offsh.columns:
        df[col] = offsh[col]
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
                  cfg.get('geometry', 'coastdatgrid_polygon'))
    goffsh.gdf = geo.spatial_join_with_buffer(goffsh, coastdat)
    goffsh.gdf2df()

    new_cap = goffsh.df['capacity'].sum()
    old_cap = orig_df.loc[orig_df['technology'] == 'Offshore',
                          'capacity'].sum()

    # Remove Offshore technology from power plant table
    orig_df = orig_df.loc[orig_df['technology'] != 'Offshore']

    patched_df = pd.DataFrame(pd.concat([orig_df, goffsh.df],
                                        ignore_index=True))
    logging.warning(
        "Offshore wind is patched. {0} MW were replaced by {1} MW".format(
            old_cap, new_cap))
    return patched_df


def pp_opsd2reegis(offshore_patch=True):
    filename_in = os.path.join(cfg.get('paths', 'opsd'),
                               cfg.get('opsd', 'opsd_prepared'))
    filename_out = os.path.join(cfg.get('paths', 'powerplants'),
                                cfg.get('powerplants', 'reegis_pp'))

    keep_cols = {'decom_year', 'comment', 'chp', 'energy_source_level_1',
                 'thermal_capacity', 'com_year', 'com_month',
                 'chp_capacity_uba', 'energy_source_level_3', 'decom_month',
                 'geometry', 'energy_source_level_2', 'capacity',
                 'federal_states', 'com_year', 'coastdat2', 'efficiency'}

    string_cols = ['chp', 'comment', 'energy_source_level_1',
                   'energy_source_level_2', 'energy_source_level_3',
                   'federal_states', 'geometry']

    if not os.path.isfile(filename_in):
        filename_in = opsd.opsd_power_plants()

    pp = {}
    for cat in ['renewable', 'conventional']:
        pp[cat] = pd.read_hdf(filename_in, cat, mode='r')
        if cat == 'renewable' and offshore_patch:
            pp[cat] = patch_offshore_wind(pp[cat], keep_cols)
        pp[cat] = pp[cat].drop(columns=set(pp[cat].columns) - keep_cols)
        pp[cat] = pp[cat].replace('nan', np.nan)
        pp[cat] = pp[cat].loc[pp[cat].comment.isnull()]
        pp[cat]['energy_source_level_1'] = (
            pp[cat]['energy_source_level_1'].fillna(
                'unknown from {0}'.format(cat)))
        pp[cat]['energy_source_level_2'] = (
            pp[cat]['energy_source_level_2'].fillna(
                pp[cat]['energy_source_level_1']))

    pp = pd.DataFrame(pd.concat([pp['renewable'], pp['conventional']],
                                ignore_index=True))

    pp['thermal_capacity'] = pp['thermal_capacity'].fillna(
        pp['chp_capacity_uba'])
    del pp['chp_capacity_uba']

    pp[string_cols] = pp[string_cols].astype(str)
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


if __name__ == "__main__":
    logger.define_logging()
    pp_opsd2reegis()
