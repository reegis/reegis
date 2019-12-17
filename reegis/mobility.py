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


def get_pkw_table(filename):
    """

    Parameters
    ----------
    filename

    Returns
    -------

    """
    pkw = pd.read_excel(filename, 'Kfz_u_Kfz_Anh', skiprows=7,
                        header=[0, 1], skipfooter=4)
    pkw = pkw.drop([('Unnamed: 0_level_0', 'Unnamed: 0_level_1')], axis=1)
    print(pkw)
    exit(0)
    return {}


def format_kba_table(filename, table):
    """

    Parameters
    ----------
    filename
    table

    Returns
    -------

    """
    tc = {
        'Kfz_u_Kfz_Anh': {
            'idx1': ('Unnamed: 1_level_0', 'Land'),
            'idx2': ('Unnamed: 2_level_0', 'Regierungsbezirk'),
            'idx3': ('Unnamed: 3_level_0',
                     'Statistische Kennziffer und Zulassungsbezirk'), },
        'Pkw': {
            'idx1': ('Land\n\n', 'Unnamed: 1_level_1'),
            'idx2': ('Regierungsbezirk', 'Unnamed: 2_level_1'),
            'idx3': ('Statistische Kennziffer und Zulassungsbezirk',
                     'Unnamed: 3_level_1'), }}

    cn = tc[table]

    # Read table
    df = pd.read_excel(filename, table, skiprows=7,
                       header=[0, 1], skipfooter=4)

    # Drop empty column
    df = df.drop([('Unnamed: 0_level_0', 'Unnamed: 0_level_1')], axis=1)

    # Remove lines with subtotal
    df.loc[(df[cn['idx1']] == 'SONSTIGE'), cn['idx2']] = (
        "SONSTIGE")
    df.loc[(df[cn['idx1']] == 'SONSTIGE'), cn['idx3']] = (
        "00000 SONSTIGE")
    df = df.drop(df.loc[df[cn['idx3']].isnull()].index)
    df[df.columns[[0, 1, 2]]] = df[df.columns[[0, 1, 2]]].fillna(
        method='ffill')

    # Add column with name of subregion and remove name from index
    df[df.columns[2]] = df[df.columns[2]].str[:5]

    # set MultiIndex
    df.set_index(list(df.columns[[0, 1, 2]]), inplace=True)
    df.index = df.index.set_names(['state', 'region', 'subregion'])

    # Remove format-strings from column names
    level1 = (df.columns.get_level_values(1).
              str.replace("\n", " ").str.replace("- ", ""))
    level0 = (df.columns.get_level_values(0).
              str.replace("\n", " ").str.replace("- ", ""))
    df.columns = pd.MultiIndex.from_arrays([level0, level1])
    return df


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

    return kba_table(kfz=format_kba_table(kba_filename, 'Kfz_u_Kfz_Anh'),
                     pkw=format_kba_table(kba_filename, 'Pkw'))


df1 = get_kba_table().pkw.groupby(level=2).sum()
fn = os.path.join(cfg.get('paths', 'geometry'), 'vg1000_geodata.geojson')
vg = geometries.load(fullname=fn)
vg.set_index('RS', inplace=True)
neu = vg.merge(df1, left_index=True, right_index=True)
print(neu.sum())
neu.plot(column=('Insgesamt', 'Unnamed: 4_level_1'))
plt.show()
