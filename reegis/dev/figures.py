import os
from matplotlib import pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from reegis import geometries


def fig_deflex_de22_polygons():
    ax = plt.figure(figsize=(9, 7)).add_subplot(1, 1, 1)

    # change for a better/worse resolution (
    simple = 0.02

    cmap = LinearSegmentedColormap.from_list(
        'mycmap', [(0.000000000, '#badd69'),
                   (0.5, '#dd5500'),
                   (1, '#a5bfdd')])

    fs = geometries.get_federal_states_polygon()
    fs.drop('P0', axis=0, inplace=True)
    fs['color'] = 0.5
    fs.loc[['O0', 'N0', 'N1'], 'color'] = 1
    fs.loc[['O0', 'N0', 'N1'], 'SN_L'] = '00'
    fs['region'] = fs.index
    fs = fs.dissolve(by='SN_L')
    fs.loc['00', 'region'] = 'AW'
    fs['geometry'] = fs['geometry'].simplify(simple)
    # fs.loc['awz'] = fs.loc['N0'].union(fs.loc['N1'])
    fs.plot(ax=ax, cmap=cmap, column='color', edgecolor='#888888')
    plt.subplots_adjust(right=1, left=0, bottom=0, top=1)

    ax.set_axis_off()
    fn = os.path.join(os.path.dirname(__file__),
                      os.pardir, os.pardir, 'docs', '_files',
                      'federal_states_region_plot.svg')
    plt.savefig(fn)
    plt.show()


fig_deflex_de22_polygons()
