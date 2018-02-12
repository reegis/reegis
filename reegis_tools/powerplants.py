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


def pp_opsd2reegis():
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

    logging.info("Opsd power plants with de21 region stored in {0}".format(
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
