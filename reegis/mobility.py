# -*- coding: utf-8 -*-

"""Calculte the mobility demand.

SPDX-FileCopyrightText: 2016-2019 Uwe Krien <krien@uni-bremen.de>

SPDX-License-Identifier: MIT
"""
__copyright__ = "Uwe Krien <krien@uni-bremen.de>"
__license__ = "MIT"

import logging
import os
from matplotlib import pyplot as plt
from collections import namedtuple

import requests
from shapely import wkb
import pandas as pd
import geopandas as gpd

from reegis import geometries, config as cfg, tools


# fn = os.path.join(cfg.get('paths', 'geometry'), 'vg1000_geodata.geojson')
# vg = geometries.load(fullname=fn)
# print(vg)


def get_pkw_table(filename):
    """

    Parameters
    ----------
    filename

    Returns
    -------

    """
    return {}


def get_kfz_table(filename):
    """

    Parameters
    ----------
    filename

    Returns
    -------

    """
    # Read table
    kfz = pd.read_excel(filename, 'Kfz_u_Kfz_Anh', skiprows=7,
                        header=[0, 1], skipfooter=4)

    # Drop empty column
    kfz = kfz.drop([('Unnamed: 0_level_0', 'Unnamed: 0_level_1')], axis=1)

    # Remove lines with subtotal
    idx2 = ('Unnamed: 2_level_0',
            'Regierungsbezirk')
    idx3 = ('Unnamed: 3_level_0',
            'Statistische Kennziffer und Zulassungsbezirk')
    kfz.loc[(kfz[('Unnamed: 1_level_0', 'Land')] == 'SONSTIGE'), idx2] = (
        "SONSTIGE")
    kfz.loc[(kfz[('Unnamed: 1_level_0', 'Land')] == 'SONSTIGE'), idx3] = (
        "00000 SONSTIGE")
    kfz = kfz.drop(kfz.loc[kfz[idx3].isnull()].index)
    kfz[kfz.columns[[0, 1, 2]]] = kfz[kfz.columns[[0, 1, 2]]].fillna(
        method='ffill')

    # Add column with name of subregion and remove name from index
    kfz[kfz.columns[2]] = kfz[kfz.columns[2]].str[:5]

    # set MultiIndex
    kfz.set_index(list(kfz.columns[[0, 1, 2]]), inplace=True)
    kfz.index = kfz.index.set_names(['state', 'region', 'subregion'])

    # Remove format-strings from column names
    level1 = (kfz.columns.get_level_values(1).
              str.replace("\n", " ").str.replace("- ", ""))
    level0 = (kfz.columns.get_level_values(0).
              str.replace("\n", " ").str.replace("- ", ""))
    kfz.columns = pd.MultiIndex.from_arrays([level0, level1])
    return kfz


def get_kba_table():
    """
    
    Returns
    -------

    """
    kba_table = namedtuple('kba_table', 'kfz pkw')
    kba_filename = os.path.join(cfg.get('paths', 'general'),
                                cfg.get('mobility', 'table_kba'))

    # Download table if it does not exit
    if not os.path.isfile(kba_filename):
        tools.download_file(kba_filename, cfg.get('mobility', 'url_kba'))

    return kba_table(kfz=get_kfz_table(kba_filename),
                     pkw=get_pkw_table(kba_filename))


print(get_kba_table().kfz.sum())
