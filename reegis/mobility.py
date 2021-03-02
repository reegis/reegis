# -*- coding: utf-8 -*-

"""Calculate the mobility demand.

SPDX-FileCopyrightText: 2016-2021 Uwe Krien <krien@uni-bremen.de>

SPDX-License-Identifier: MIT
"""
__copyright__ = "Uwe Krien <krien@uni-bremen.de>"
__license__ = "MIT"


import os
import pandas as pd
from collections import namedtuple

from reegis import geometries, config as cfg, tools, energy_balance


def format_kba_table(filename, sheet):
    """
    Clean the layout of the table.

    The tables are made for human readability and not for automatic processing.
    Lines with subtotals and format-strings of the column names are removed.
    A valid MultiIndex is created to make it easier to filter the table by the
    index.

    Parameters
    ----------
    filename : str
        Path and name of the excel file.
    sheet : str
        Name of the sheet of the excel table.

    Returns
    -------
    pandas.DataFrame

    """

    # Read table
    df = pd.read_excel(filename, sheet, skiprows=7, header=[0, 1])

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
    Get the "kfz" table for all vehicles and the "pkw" table for more
    statistics about passenger cars.

    Returns
    -------
    namedtuple

    Examples
    --------
    >>> table = get_kba_table()
    >>> kfz = table.kfz
    >>> print(type(kfz))
    <class 'pandas.core.frame.DataFrame'>
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


def get_mileage_table():
    """
    Download mileage table from the KBA (Kraftfahrtbundesamt) and store it
    locally.
    """
    url = (
        "https://www.kba.de/SharedDocs/Publikationen/DE/Statistik/"
        "Kraftverkehr/VK/2018/vk_2018_xlsx.xlsx?__blob=publicationFile&v=22"
    )

    mileage_filename = os.path.join(
        cfg.get("paths", "general"), "mileage_table_kba.xlsx"
    )

    # Download table if it does not exit
    if not os.path.isfile(mileage_filename):
        tools.download_file(mileage_filename, url)
    return mileage_filename


def get_sheet_from_mileage_table(sheet):
    """Load given sheet from the mileage file."""
    fn = get_mileage_table()
    df = pd.read_excel(
        fn, sheet, skiprows=7, index_col=[0, 1, 2], skipfooter=9
    )
    df.index = df.index.droplevel(0).set_names(["", ""])

    return df.drop(
        df.loc[pd.IndexSlice[slice(None), "Insgesamt"], slice(None)].index
    )


def get_mileage_by_type_and_fuel(year=2018):
    """
    Get mileage by type and fuel from mileage table and other sources.

    See mobility.ini file for more information.
    """
    # get km per year and type
    total = (
        get_sheet_from_mileage_table("VK 1.1")
        .loc["Jahresfahrleistung in 1.000 km", str(year)]
        .mul(1000)
    )
    passenger = (
        get_sheet_from_mileage_table("VK 1.7")
        .loc["Jahresfahrleistung in 1.000 km", str(year)]
        .mul(1000)
    )
    small_trucks = (
        get_sheet_from_mileage_table("VK 1.17")
        .loc["Jahresfahrleistung in 1.000 km", str(year)]
        .mul(1000)
    )
    medium_trucks = (
        get_sheet_from_mileage_table("VK 1.20")
        .loc["Jahresfahrleistung in 1.000 km", str(year)]
        .mul(1000)
    )
    big_trucks_diesel = (
        get_sheet_from_mileage_table("VK 1.23")
        .loc["Jahresfahrleistung in 1.000 km", str(year)]
        .mul(1000)
        .sum()
    )
    df = pd.DataFrame(index=total.index, columns=["diesel", "petrol", "other"])

    vt_dict = cfg.get_dict("vehicle_types_dictionary")
    df.rename(vt_dict, axis=0, inplace=True)
    total.rename(vt_dict, axis=0, inplace=True)

    dc = cfg.get_dict("fuel_dictionary")

    # add km by fuel for passenger cars
    df.loc["passenger car"] = passenger.rename(dc, axis=0)

    # add km by fuel for small trucks (<= 3.5 tons)
    df.loc["small truck (max. 3.5 tons)"] = small_trucks.rename(dc, axis=0)

    # add km by fuel for medium trucks (3.5 < weight <= 7.5 tons)
    df.loc["medium truck (3.5 to 7.5 tons)"] = medium_trucks.rename(dc, axis=0)

    # add km by fuel for big trucks (> 7.5 tons)
    # assuming that non-diesel engines are 50% petrol and 50% other
    n = "big truck (over 7.5 tons)"
    df.loc[n, "diesel"] = big_trucks_diesel
    df.loc[n, ["petrol", "other"]] = (total[n] - big_trucks_diesel) / 2

    fuel_share = pd.DataFrame(
        cfg.get_dict_list("fuel share"), index=["diesel", "petrol", "other"]
    ).astype(float)

    for col in fuel_share.columns:
        df.loc[col] = fuel_share[col].mul(total[col])

    return df


def create_grouped_table_kfz():
    """Group the kfz-table by main groups."""
    df = get_kba_table().kfz
    df.index = df.index.droplevel([0, 1])
    df.columns = [" ".join(col).strip() for col in df.columns]
    kfz_dict = cfg.get_dict("KFZ")
    for col in df.columns:
        df[col] = pd.to_numeric(df[col].replace("-", ""))
    df = df.groupby(by=kfz_dict, axis=1).sum()
    df["traction engine, general"] = (
        df["traction engine"] - df["traction engine, agriculture and forestry"]
    )
    df.drop("traction engine", axis=1, inplace=True)
    df.drop("ignore", axis=1, inplace=True)
    return df


def create_grouped_table_pkw():
    """
    Extract fuel groups of passenger cars

    Examples
    --------
    >>> pkw = create_grouped_table_pkw()
    >>> pkw['petrol'].sum()
    31031021.0
    >>> pkw['diesel'].sum()
    15153364.0
    """
    df = get_kba_table().pkw
    df.index = df.index.droplevel([0, 1])
    df = df["Nach Kraftstoffarten"]
    df = df.groupby(by=cfg.get_dict("PKW"), axis=1).sum()
    df.drop("ignore", axis=1, inplace=True)
    return df


def get_admin_by_region(region):
    """
    Allocate admin keys to the given regions.

    Parameters
    ----------
    region : geopandas.GeoDataFrame

    Returns
    -------
    pd.DataFrame
    """
    fn = os.path.join(cfg.get("paths", "geometry"), "vg1000_geodata.geojson")
    vg = geometries.load(fullname=fn)
    vg.set_index("RS", inplace=True)

    reg2vg = geometries.spatial_join_with_buffer(
        vg.representative_point(), region, "fs", limit=0
    )

    return pd.DataFrame(reg2vg.drop("geometry", axis=1))


def get_grouped_kfz_by_region(region):
    """
    Get the main vehicle groups by region.

    Parameters
    ----------
    region : geopandas.GeoDataFrame

    Returns
    -------
    pd.DataFrame

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
    df2reg = df.merge(reg2vg, left_index=True, right_index=True, how="left")
    df2reg["fs"] = df2reg["fs"].fillna("unknown")
    return df2reg.groupby("fs").sum()


def get_traffic_fuel_energy(year):
    """

    Parameters
    ----------
    year : int

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
    fuel_energy.drop(
        ["primär (gesamt)", "sekundär (gesamt)", "Row", "gesamt"], inplace=True
    )
    return fuel_energy


def calculate_mobility_energy_use(year):
    """

    Parameters
    ----------
    year

    Returns
    -------

    Examples
    --------
    >>> mobility_balance = get_traffic_fuel_energy(2017)
    >>> energy_use = calculate_mobility_energy_use(2017)
    >>> p = "Petrol usage [TJ]"
    >>> d = "Diesel usage [TJ]"
    >>> o = "Overall fuel usage [TJ]"
    >>> print(p, "(energy balance):", int(mobility_balance["Ottokraftstoffe"]))
    Petrol usage [TJ] (energy balance): 719580
    >>> print(p, "(calculated):", int(energy_use["petrol"].sum()))
    Petrol usage [TJ] (calculated): 803603
    >>> print(d, "(energy balance):",
    ...     int(mobility_balance["Dieselkraftstoffe"]))
    Diesel usage [TJ] (energy balance): 1425424
    >>> print(d, "(calculated):", int(energy_use["diesel"].sum()))
    Diesel usage [TJ] (calculated): 1636199
    >>> print(o, "(energy balance):", int(mobility_balance.sum()))
    Overall fuel usage [TJ] (energy balance): 2275143
    >>> print(o, "(calculated):", int(energy_use.sum().sum()))
    Overall fuel usage [TJ] (calculated): 2439803
    """
    # fetch table of mileage by fuel and vehicle type
    mileage = get_mileage_by_type_and_fuel(year)

    # fetch table of specific demand by fuel and vehicle type (from 2011)
    spec_demand = (
        pd.DataFrame(
            cfg.get_dict_list("fuel consumption"),
            index=["diesel", "petrol", "other"],
        )
        .astype(float)
        .transpose()
    )

    # fetch the energy content of the different fuel types
    energy_content = pd.Series(cfg.get_dict("energy_per_liter"))[
        ["diesel", "petrol", "other"]
    ]

    return mileage.mul(spec_demand).mul(energy_content) / 10 ** 6


if __name__ == "__main__":
    pass
