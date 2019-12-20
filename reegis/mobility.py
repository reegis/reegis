# -*- coding: utf-8 -*-

"""Calculte the mobility demand.

SPDX-FileCopyrightText: 2016-2019 Uwe Krien <krien@uni-bremen.de>

SPDX-License-Identifier: MIT
"""
__copyright__ = "Uwe Krien <krien@uni-bremen.de>"
__license__ = "MIT"


import os
import pandas as pd
from collections import namedtuple

from reegis import geometries, config as cfg, tools, energy_balance


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
        .str.replace(":", "")
    )
    level0 = (
        df.columns.get_level_values(0)
        .str.replace("\n", " ")
        .str.replace("- ", "")
        .str.replace(":", "")
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


def create_grouped_table_kfz():
    """Group the kfz-table by main groups."""
    df = get_kba_table().kfz
    df.index = df.index.droplevel([0, 1])
    df.columns = [" ".join(col).strip() for col in df.columns.values]
    kfz_dict = cfg.get_dict("KFZ")
    for col in df.columns:
        df[col] = pd.to_numeric(df[col].replace("-", ""))
    df = df.groupby(by=kfz_dict, axis=1).sum()
    df["traction engine, general"] = (
        df["traction engine"]
        - df["traction engine, agriculture and forestry"]
    )
    df.drop("traction engine", axis=1, inplace=True)
    df.drop("ignore", axis=1, inplace=True)
    return df


def create_grouped_table_pkw():
    """Extract fuel groups of passenger cars"""
    df = get_kba_table().pkw
    df.index = df.index.droplevel([0, 1])
    df = df['Nach Kraftstoffarten']
    df = df.groupby(by=cfg.get_dict("PKW"), axis=1).sum()
    df.drop("ignore", axis=1, inplace=True)
    return df


def get_admin_by_region(region):
    """Allocate admin keys to the given regions."""
    fn = os.path.join(cfg.get("paths", "geometry"), "vg1000_geodata.geojson")
    vg = geometries.load(fullname=fn)
    vg.set_index("RS", inplace=True)

    reg2vg = geometries.spatial_join_with_buffer(
        vg.representative_point(), region, "fs", limit=0)

    return pd.DataFrame(reg2vg.drop("geometry", axis=1))


def get_grouped_kfz_by_region(region):
    """Get the main vehicle groups by region.

    Examples
    --------
    >>> fs = geometries.get_federal_states_polygon()
    >>> total = get_grouped_kfz_by_region(fs).sum()
    >>> int(total["passenger car"])
    47095784
    >>> int(total["lorry, > 7500"])
    295826
    """
    df = create_grouped_table_kfz()
    reg2vg = get_admin_by_region(region)
    df2reg = df.merge(reg2vg, left_index=True, right_index=True, how='left')
    df2reg['fs'] = df2reg['fs'].fillna('unknown')
    return df2reg.groupby('fs').sum()


def get_traffic_fuel_energy(year):
    """

    Parameters
    ----------
    year

    Returns
    -------

    Examples
    --------
    >>> fuel_energy = get_traffic_fuel_energy(2017)
    >>> int(fuel_energy["Ottokraftstoffe"])
    719580
    >>> fuel_share = fuel_energy.div(fuel_energy.sum()) * 100
    >>> round(fuel_share["Dieselkraftstoffe"], 1)
    62.7
    """
    fuel_energy = energy_balance.get_de_balance(year).loc["Straßenverkehr"]
    fuel_energy = fuel_energy[fuel_energy != 0]
    fuel_energy.drop(["primär (gesamt)", "sekundär (gesamt)", "Row",
                      "gesamt"], inplace=True)
    return fuel_energy


if __name__ == "__main__":
    pass
