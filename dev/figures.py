# -*- coding: utf-8 -*-

"""
Source code of the figures in the documentation.

SPDX-FileCopyrightText: 2016-2019 Uwe Krien <krien@uni-bremen.de>

SPDX-License-Identifier: MIT
"""

__copyright__ = "Uwe Krien <krien@uni-bremen.de>"
__license__ = "MIT"

import os
import pandas as pd
from matplotlib import pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from matplotlib import patches
from reegis import (
    geometries,
    powerplants,
    energy_balance,
    openego,
    bmwi,
    demand_elec,
)


def fig_federal_states_polygons():
    """
    Plot federal states and the exclusive economic zone of Germany as map.
    """
    ax = plt.figure(figsize=(9, 7)).add_subplot(1, 1, 1)

    # change for a better/worse resolution (
    simple = 0.02

    cmap = LinearSegmentedColormap.from_list(
        "mycmap", [(0, "#badd69"), (1, "#a5bfdd")], 2
    )

    fs = geometries.get_federal_states_polygon()

    # drop buffer region
    fs.drop("P0", axis=0, inplace=True)

    # dissolve offshore regions to one region
    fs["region"] = fs.index  # prevent index
    fs.loc[["O0", "N0", "N1"], "SN_L"] = "00"
    fs = fs.dissolve(by="SN_L")
    fs.loc["00", "region"] = "AW"
    fs.loc["00", "name"] = "Ausschließliche Wirtschaftszone"
    fs.set_index("region", inplace=True)  # write back index

    # simplify the geometry to make the resulting file smaller
    fs["geometry"] = fs["geometry"].simplify(simple)

    # set color column
    fs["color"] = 0
    fs.loc["AW", "color"] = 1

    # plot map
    fs.plot(ax=ax, cmap=cmap, column="color", edgecolor="#888888")

    # adjust plot
    plt.subplots_adjust(right=1, left=0, bottom=0, top=1)
    ax.set_axis_off()

    return "federal_states_region_plot"


def fig_powerplants():
    """
    Figure compares the results of the reegis 'get_powerplants_by_region' with
    statistical data of the Federal Network Agency (BNetzA).
    """
    plt.rcParams.update({"font.size": 14})
    geo = geometries.get_federal_states_polygon()

    my_name = "my_federal_states"  # doctest: +SKIP
    my_year = 2015  # doctest: +SKIP
    pp_reegis = powerplants.get_powerplants_by_region(geo, my_year, my_name)

    data_path = os.path.join(
        os.path.dirname(__file__), os.pardir, "data", "static"
    )

    fn_bnetza = os.path.join(data_path, "powerplants_bnetza_2015.csv")
    pp_bnetza = pd.read_csv(fn_bnetza, index_col=[0], skiprows=2, header=[0])

    ax = plt.figure(figsize=(9, 5)).add_subplot(1, 1, 1)

    see = "other renew."

    my_dict = {
        "Bioenergy": see,
        "Geothermal": see,
        "Hard coal": "coal",
        "Hydro": see,
        "Lignite": "coal",
        "Natural gas": "natural gas",
        "Nuclear": "nuclear",
        "Oil": "other fossil",
        "Other fossil fuels": "other fossil",
        "Other fuels": "other fossil",
        "Solar": "solar power",
        "Waste": "other fossil",
        "Wind": "wind power",
        "unknown from conventional": "other fossil",
    }

    my_dict2 = {
        "Biomasse": see,
        "Braunkohle": "coal",
        "Erdgas": "natural gas",
        "Kernenergie": "nuclear",
        "Laufwasser": see,
        "Solar": "solar power",
        "Sonstige (ne)": "other fossil",
        "Steinkohle": "coal",
        "Wind": "wind power",
        "Sonstige (ee)": see,
        "Öl": "other fossil",
    }

    my_colors = [
        "#6c3012",
        "#555555",
        "#db0b0b",
        "#501209",
        "#163e16",
        "#ffde32",
        "#335a8a",
    ]

    pp_reegis = (
        pp_reegis.capacity_2015.unstack().groupby(my_dict, axis=1).sum()
    )

    pp_reegis.loc["EEZ"] = (
        pp_reegis.loc["N0"] + pp_reegis.loc["N1"] + pp_reegis.loc["O0"]
    )

    pp_reegis.drop(["N0", "N1", "O0", "unknown", "P0"], inplace=True)

    pp_bnetza = pp_bnetza.groupby(my_dict2, axis=1).sum()

    ax = (
        pp_reegis.sort_index()
        .sort_index(1)
        .div(1000)
        .plot(
            kind="bar",
            stacked=True,
            position=1.1,
            width=0.3,
            legend=False,
            color=my_colors,
            ax=ax,
        )
    )
    pp_bnetza.sort_index().sort_index(1).div(1000).plot(
        kind="bar",
        stacked=True,
        position=-0.1,
        width=0.3,
        ax=ax,
        color=my_colors,
        alpha=0.9,
    )
    plt.xlabel("federal state / exclusive economic zone (EEZ)")
    plt.ylabel("installed capacity [GW]")
    plt.xlim(left=-0.5)
    plt.subplots_adjust(bottom=0.17, top=0.98, left=0.08, right=0.96)

    b_sum = pp_bnetza.sum() / 1000
    b_total = int(round(b_sum.sum()))
    b_ee_sum = int(round(b_sum.loc[["wind power", "solar power", see]].sum()))
    b_fs_sum = int(
        round(
            b_sum.loc[["natural gas", "coal", "nuclear", "other fossil"]].sum()
        )
    )
    r_sum = pp_reegis.sum() / 1000
    r_total = int(round(r_sum.sum()))
    r_ee_sum = int(round(r_sum.loc[["wind power", "solar power", see]].sum()))
    r_fs_sum = int(
        round(
            r_sum.loc[["natural gas", "coal", "nuclear", "other fossil"]].sum()
        )
    )

    text = {
        "reegis": (2.3, 42, "reegis"),
        "BNetzA": (3.9, 42, "BNetzA"),
        "b_sum1": (0, 39, "total"),
        "b_sum2": (2.5, 39, "{0}       {1}".format(r_total, b_total)),
        "b_fs": (0, 36, "fossil"),
        "b_fs2": (2.5, 36, " {0}         {1}".format(r_fs_sum, b_fs_sum)),
        "b_ee": (0, 33, "renewable"),
        "b_ee2": (2.5, 33, " {0}         {1}".format(r_ee_sum, b_ee_sum)),
    }

    for t, c in text.items():
        plt.text(c[0], c[1], c[2], size=14, ha="left", va="center")

    b = patches.Rectangle((-0.2, 31.8), 5.7, 12, color="#cccccc")
    ax.add_patch(b)
    ax.add_patch(patches.Shadow(b, -0.05, -0.2))
    plt.title("Capacity of power plants in 2014")
    plt.subplots_adjust(right=0.96, left=0.08, bottom=0.17, top=0.93)
    return "compare_power_plants_reegis_bnetza"


def fig_energy_balance_lignite():
    """
    Extraction of raw lignite in Germany over the years using the
    `energy_balance` module.
    """
    fuel = "lignite (raw)"
    eb = energy_balance.get_states_energy_balance()
    ax = plt.figure(figsize=(10, 5)).add_subplot(1, 1, 1)
    eb.loc[(slice(None), slice(None), "extraction"), fuel].groupby(
        level=0
    ).sum().plot(ax=ax)
    plt.title("Extraction of raw lignite in Germany")
    plt.xlabel("year")
    plt.ylabel("energy [TJ]")
    plt.ylim(bottom=-0.0001)
    return "energy_balance_lignite_extraction"


def fig_electricity_demand_by_state():
    """
    Comparison of two methods to get the electricity demand for the federal
    states of Germany. The reegis energy balance module and the reegis openego
    module. The openego module can be used for any region polygon.
    """
    plt.rcParams.update({"font.size": 14})
    ax = plt.figure(figsize=(9, 4)).add_subplot(1, 1, 1)
    eb = energy_balance.get_states_energy_balance(2014).swaplevel()
    total = eb.loc["Endenergieverbrauch", "electricity"].sum()
    elec_fs = eb.loc["Endenergieverbrauch", "electricity"]
    elec_fs.name = "energy balance"
    share = pd.DataFrame(elec_fs.div(total).mul(100))

    federal_states = geometries.get_federal_states_polygon()
    ego_demand = openego.get_ego_demand_by_region(
        federal_states, "federal_states", grouped=True
    )

    share["openego"] = ego_demand.div(ego_demand.sum()).mul(100)

    print(share)
    share.plot(kind="bar", ax=ax)

    share["diff"] = (share["energy balance"] - share["openego"]) / share[
        "energy balance"
    ]
    print(share)

    ax.set_ylabel("share [%]")
    t = (
        "Share of overall electricity demand from the reegis\n energy"
        " balance module and from the reegis openego module."
    )
    plt.title(t)
    plt.subplots_adjust(right=0.96, left=0.09, bottom=0.13, top=0.85)
    return "electricity_demand_by_state"


def fig_energy_demand_germany_bmwi():
    """
    Time series of the energy demand of Germany from 1991 to 2015.
    """
    df = pd.Series()
    ax = plt.figure(figsize=(9, 4)).add_subplot(1, 1, 1)
    for year in range(1991, 2016):
        print(year)
        df.loc[year] = bmwi.get_annual_electricity_demand_bmwi(year)

    df.plot(ax=ax)
    ax.set_ylabel("energy demand [TWh]")
    plt.ylim(0, 600)
    plt.title("Energy demand in Germany from 1991 to 2015")
    return "energy_demand_germany_bmwi"


def fig_electricity_profile_from_entsoe():
    """
    Electricity profile from entso-e scaled on the annual demand of three
    different federal states.
    """
    ax = plt.figure(figsize=(10, 4)).add_subplot(1, 1, 1)
    fs = geometries.get_federal_states_polygon()

    df = demand_elec.get_entsoe_profile_by_region(
        fs, 2014, "federal_states", "bmwi"
    )

    df[["NW", "NI", "MV"]].mul(1000).plot(ax=ax)
    plt.title("Demand profile for three federal states in 2014")
    ax.set_ylabel("electricity demand [GW]")
    ax.set_xlabel("hour of the year")

    box = ax.get_position()
    ax.set_position([box.x0, box.y0, box.width * 0.8, box.height])
    ax.legend(loc="upper left", bbox_to_anchor=(1, 0.5))

    plt.subplots_adjust(right=0.91, left=0.08, bottom=0.13, top=0.91)
    return "electricity_profile_from_entsoe"


def fig_scaled_electricity_profile():
    """
    Comparison of different methods to fetch the annual electricity demand
    to scale the entso-e profile.
    """
    ax = plt.figure(figsize=(8, 4)).add_subplot(1, 1, 1)
    fs = geometries.get_federal_states_polygon()
    p = pd.Series()
    p1 = demand_elec.get_entsoe_profile_by_region(fs, 2014, "test", "entsoe")
    p["entsoe"] = p1.sum().sum()

    p2 = demand_elec.get_entsoe_profile_by_region(fs, 2013, "test", "bmwi")
    p["bmwi"] = p2.sum().sum()

    p3 = demand_elec.get_entsoe_profile_by_region(fs, 2013, "test", "openego")
    p["openego"] = p3.sum().sum()

    p4 = demand_elec.get_entsoe_profile_by_region(fs, 2011, "test", 555555)
    p["user value"] = p4.sum().sum()

    p.plot(kind="bar", ax=ax)
    plt.xticks(rotation=0)
    ax.set_ylabel("energy demand [GWh]")
    plt.title("Energy demand of Germany to scale the overall demand.")
    plt.subplots_adjust(right=0.95, left=0.13, bottom=0.13, top=0.91)
    return "scaled_electricity_profile"


def plot(names=None, save=True, show=False):
    """
    Control the plottint process.

    Parameters
    ----------
    names : list
    save : bool
    show : bool

    """
    if names is None:
        names = [
            fig_powerplants,
            fig_federal_states_polygons,
            fig_energy_balance_lignite,
            fig_electricity_demand_by_state,
            fig_energy_demand_germany_bmwi,
            fig_electricity_profile_from_entsoe,
            fig_scaled_electricity_profile,
        ]

    for name in names:
        filename = name()

        # write figure to file
        fn = os.path.join(
            os.path.dirname(__file__),
            os.pardir,
            os.pardir,
            "docs",
            "_files",
            filename + ".svg",
        )

        if save is True:
            plt.savefig(fn)

        if show is True:
            plt.show()


if __name__ == "__main__":
    plot(show=True)
