import os
from matplotlib import pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from reegis import geometries


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

    # write figure to file
    fn = os.path.join(os.path.dirname(__file__),
                      os.pardir, os.pardir, 'docs', '_files',
                      'federal_states_region_plot.svg')
    plt.savefig(fn)
    # print(fs[['name', 'color', 'geometry']])
    plt.show()


if __name__ == "__main__":
    fig_federal_states_polygons()
