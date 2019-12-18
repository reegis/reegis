# -*- coding: utf-8 -*-

"""Calculte the mobility demand.

SPDX-FileCopyrightText: 2016-2019 Uwe Krien <krien@uni-bremen.de>

SPDX-License-Identifier: MIT
"""
__copyright__ = "Uwe Krien <krien@uni-bremen.de>"
__license__ = "MIT"

import os
try:
    from matplotlib import pyplot as plt
except ImportError:
    plt = None
from collections import namedtuple

import pandas as pd

from reegis import geometries, config as cfg, tools


def format_kba_table(filename, table):
    """

    Parameters
    ----------
    filename
    table

    Returns
    -------

    """

    # Read table
    df = pd.read_excel(filename, table, skiprows=7, header=[0, 1])

    # Drop empty column
    df = df.drop([("Unnamed: 0_level_0", "Unnamed: 0_level_1")], axis=1)

    idx1 = df.columns[0]
    idx2 = df.columns[1]
    idx3 = df.columns[2]

    # Remove lines with subtotal
    df.loc[(df[idx1] == "SONSTIGE"), idx2] = "SONSTIGE"
    df.loc[(df[idx1] == "SONSTIGE"), idx3] = "00000 SONSTIGE"
    df = df.drop(df.loc[df[idx3].isnull()].index)
    df[df.columns[[0, 1, 2]]] = df[df.columns[[0, 1, 2]]].fillna(
        method="ffill"
    )

    # Add column with name of subregion and remove name from index
    df[df.columns[2]] = df[df.columns[2]].str[:5]

    # set MultiIndex
    df.set_index(list(df.columns[[0, 1, 2]]), inplace=True)
    df.index = df.index.set_names(["state", "region", "subregion"])

    # Remove format-strings from column names
    level1 = (
        df.columns.get_level_values(1)
        .str.replace("\n", " ")
        .str.replace("- ", "")
    )
    level0 = (
        df.columns.get_level_values(0)
        .str.replace("\n", " ")
        .str.replace("- ", "")
    )
    df.columns = pd.MultiIndex.from_arrays([level0, level1])

    return df


def get_kba_table():
    """
    
    Returns
    -------

    """
    kba_table = namedtuple("kba_table", "kfz pkw")
    kba_filename = os.path.join(
        cfg.get("paths", "general"), cfg.get("mobility", "table_kba")
    )

    # Download table if it does not exit
    if not os.path.isfile(kba_filename):
        tools.download_file(kba_filename, cfg.get("mobility", "url_kba"))

    return kba_table(
        kfz=format_kba_table(kba_filename, "Kfz_u_Kfz_Anh"),
        pkw=format_kba_table(kba_filename, "Pkw"),
    )


def create_sum_table():
    pass


if __name__ == "__main__":
    df1 = get_kba_table().kfz
    df1.columns = [' '.join(col).strip() for col in df1.columns.values]
    for c in df1.columns:
        print(c)
    print(len(df1.columns))
    df1.index = df1.index.droplevel([0, 1])
    print(df1.index)
    fn = os.path.join(cfg.get("paths", "geometry"), "vg1000_geodata.geojson")
    vg = geometries.load(fullname=fn)
    vg.set_index("RS", inplace=True)
    neu = vg.merge(df1, left_index=True, right_index=True)
    print(neu.columns)
    fig, ax = plt.subplots(1, 1)
    col = "Personenkraftwagen  PKW-Dichte je 1.000  Einwohner"
    neu[col] = neu[col].astype(int)
    print(neu[col].max(), neu[col].min())
    neu.plot(column=col, ax=ax, legend=True, cmap='OrRd', vmax=500, vmin=400)
    plt.show()
