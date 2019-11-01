import os
import pandas as pd
from matplotlib import pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from matplotlib import patches
from reegis import geometries, powerplants, energy_balance


def fig_federal_states_polygons():
    """Plot federal states as map."""
    ax = plt.figure(figsize=(9, 7)).add_subplot(1, 1, 1)

    # change for a better/worse resolution (
    simple = 0.02

    cmap = LinearSegmentedColormap.from_list(
        'mycmap', [(0, '#badd69'), (1, '#a5bfdd')], 2)

    fs = geometries.get_federal_states_polygon()

    # drop buffer region
    fs.drop('P0', axis=0, inplace=True)

    # dissolve offshore regions to one region
    fs['region'] = fs.index   # prevent index
    fs.loc[['O0', 'N0', 'N1'], 'SN_L'] = '00'
    fs = fs.dissolve(by='SN_L')
    fs.loc['00', 'region'] = 'AW'
    fs.loc['00', 'name'] = 'Ausschließliche Wirtschaftszone'
    fs.set_index('region', inplace=True)  # write back index

    # simplify the geometry to make the resulting file smaller
    fs['geometry'] = fs['geometry'].simplify(simple)

    # set color column
    fs['color'] = 0
    fs.loc['AW', 'color'] = 1

    # plot map
    fs.plot(ax=ax, cmap=cmap, column='color', edgecolor='#888888')

    # adjust plot
    plt.subplots_adjust(right=1, left=0, bottom=0, top=1)
    ax.set_axis_off()

    return 'federal_states_region_plot'


def fig_powerplants():
    plt.rcParams.update({'font.size': 14})
    geo = geometries.get_federal_states_polygon()

    my_name = 'my_federal_states'  # doctest: +SKIP
    my_year = 2015  # doctest: +SKIP
    pp_reegis = powerplants.get_powerplants_by_region(geo, my_year, my_name)

    data_path = os.path.join(os.path.dirname(__file__), os.pardir,
                             'data', 'static')

    fn_bnetza = os.path.join(data_path, 'powerplants_bnetza_2015.csv')
    pp_bnetza = pd.read_csv(fn_bnetza, index_col=[0], skiprows=2, header=[0])

    ax = plt.figure(figsize=(9, 5)).add_subplot(1, 1, 1)

    see = 'other renew.'

    my_dict = {
        'Bioenergy': see,
        'Geothermal': see,
        'Hard coal': 'coal',
        'Hydro': see,
        'Lignite': 'coal',
        'Natural gas': 'natural gas',
        'Nuclear': 'nuclear',
        'Oil': 'other fossil',
        'Other fossil fuels': 'other fossil',
        'Other fuels': 'other fossil',
        'Solar': 'solar power',
        'Waste': 'other fossil',
        'Wind': 'wind power',
        'unknown from conventional': 'other fossil'}

    my_dict2 = {
        'Biomasse': see,
        'Braunkohle': 'coal',
        'Erdgas': 'natural gas',
        'Kernenergie': 'nuclear',
        'Laufwasser': see,
        'Solar': 'solar power',
        'Sonstige (ne)': 'other fossil',
        'Steinkohle': 'coal',
        'Wind': 'wind power',
        'Sonstige (ee)': see,
        'Öl': 'other fossil'}

    my_colors = ['#6c3012', '#555555', '#db0b0b', '#501209', '#163e16',
                 '#ffde32', '#335a8a']

    # pp_reegis.capacity_2015.unstack().to_excel('/home/uwe/shp/wasser.xls')

    pp_reegis = pp_reegis.capacity_2015.unstack().groupby(
        my_dict, axis=1).sum()

    pp_reegis.loc['EEZ'] = (
            pp_reegis.loc['N0'] + pp_reegis.loc['N1'] + pp_reegis.loc['O0'])

    pp_reegis.drop(['N0', 'N1', 'O0', 'unknown', 'P0'], inplace=True)

    pp_bnetza = pp_bnetza.groupby(my_dict2, axis=1).sum()

    ax = pp_reegis.sort_index().sort_index(1).div(1000).plot(
        kind='bar', stacked=True, position=1.1, width=0.3, legend=False,
        color=my_colors, ax=ax)
    pp_bnetza.sort_index().sort_index(1).div(1000).plot(
        kind='bar', stacked=True, position=-0.1, width=0.3, ax=ax,
        color=my_colors, alpha=0.9)
    plt.xlabel('federal state / exclusive economic zone (EEZ)')
    plt.ylabel('installed capacity [GW]')
    plt.xlim(left=-0.5)
    plt.subplots_adjust(bottom=0.17, top=0.98, left=0.08, right=0.96)

    b_sum = pp_bnetza.sum()/1000
    b_total = int(round(b_sum.sum()))
    b_ee_sum = int(
        round(b_sum.loc[['wind power', 'solar power', see]].sum()))
    b_fs_sum = int(round(b_sum.loc[
        ['natural gas', 'coal', 'nuclear', 'other fossil']].sum()))
    r_sum = pp_reegis.sum()/1000
    r_total = int(round(r_sum.sum()))
    r_ee_sum = int(
        round(r_sum.loc[['wind power', 'solar power', see]].sum()))
    r_fs_sum = int(round(r_sum.loc[
        ['natural gas', 'coal', 'nuclear', 'other fossil']].sum()))

    text = {
        'reegis': (2.3, 42, 'reegis'),
        'BNetzA': (3.9, 42, 'BNetzA'),
        "b_sum1": (0, 39, "total"),
        "b_sum2": (2.5, 39, "{0}       {1}".format(r_total, b_total)),
        "b_fs": (0, 36, "fossil"),
        "b_fs2": (2.5, 36, " {0}         {1}".format(r_fs_sum, b_fs_sum)),
        "b_ee": (0, 33, "renewable"),
        "b_ee2": (2.5, 33, " {0}         {1}".format(r_ee_sum, b_ee_sum)),
      }

    for t, c in text.items():
        plt.text(c[0], c[1], c[2], size=14, ha="left", va="center")

    b = patches.Rectangle((-0.2, 31.8), 5.7, 12, color='#cccccc')
    ax.add_patch(b)
    ax.add_patch(patches.Shadow(b, -0.05, -0.2))
    return 'compare_power_plants_reegis_bnetza'


def fig_energy_balance_lignite():
    fuel = 'lignite (raw)'
    eb = energy_balance.get_states_energy_balance()
    ax = plt.figure(figsize=(10, 5)).add_subplot(1, 1, 1)
    eb.loc[(slice(None), slice(None), 'extraction'), fuel].groupby(
        level=0).sum().plot(ax=ax)
    plt.title("Extraction of raw lignite in Germany")
    plt.xlabel('year')
    plt.ylabel('energy [TJ]')
    plt.ylim(bottom=-0.0001)
    return 'energy_balance_lignite_extraction'


def plot(names=None, save=True, show=False):

    if names is None:
        names = [fig_powerplants,
                 fig_federal_states_polygons,
                 fig_energy_balance_lignite]

    for name in names:
        filename = name()

        # write figure to file
        fn = os.path.join(os.path.dirname(__file__),
                          os.pardir, os.pardir, 'docs', '_files',
                          filename + '.svg')

        if save is True:
            plt.savefig(fn)

        if show is True:
            plt.show()


if __name__ == "__main__":
    plot(show=True)
