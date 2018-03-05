# -*- coding: utf-8 -*-

"""Code snippets without context.

Copyright (c) 2016-2018 Uwe Krien <uwe.krien@rl-institut.de>

SPDX-License-Identifier: GPL-3.0-or-later
"""
__copyright__ = "Uwe Krien <uwe.krien@rl-institut.de>"
__license__ = "GPLv3"


# Python libraries
import os
import calendar

# External libraries
import pandas as pd
import geopandas as gpd
from matplotlib import pyplot as plt
from shapely.geometry import Point

# oemof packages
from oemof.tools import logger

# internal modules
import reegis_tools.config as cfg


def lat_lon2point(df):
    """Create shapely point object of latitude and longitude."""
    return Point(df['lon'], df['lat'])


def geo_csv_from_shp(shapefile, outfile, id_col, tmp_file='tmp.csv'):
    tmp = gpd.read_file(shapefile)
    tmp.to_csv(tmp_file)
    tmp = pd.read_csv(tmp_file)
    new = pd.DataFrame()
    new['gid'] = tmp[id_col]
    # # Special column manipulations
    # new['gid'] = new['gid'].apply(lambda x: x.replace('Ã¼', 'ü'))
    # new['region'] = new['gid'].apply(lambda x: x.split('_')[1])
    # new['state'] = new['gid'].apply(lambda x: x.split('_')[0])
    new['geom'] = tmp['geometry']
    new.set_index('gid', inplace=True)
    new.to_csv(outfile)
    os.remove(tmp_file)


def energy_balance2repo():
    chiba = '/home/uwe/chiba/'
    source_path = 'Promotion/Statstik/Energiebilanzen/Endenergiebilanz'
    csv_path = cfg.get('paths', 'static_sources')
    filenames = ['energybalance_DE_2012_to_2014.xlsx',
                 'energybalance_states_2012_to_2014.xlsx',
                 'sum_table_fuel_groups.xlsx',
                 'sum_table_sectors.xlsx']
    for filename in filenames:
        if 'sum' in filename:
            idx = [0, 1]
        else:
            idx = [0, 1, 2]
        excelfile = os.path.join(chiba, source_path, filename)
        csvfile = os.path.join(csv_path, filename.replace('.xlsx', '.csv'))
        excel2csv(excelfile, csvfile, index_col=idx)


def excel2csv(excel_file, csv_file, **kwargs):
    df = pd.read_excel(excel_file, **kwargs)
    df.to_csv(csv_file)


def sorter():
    b_path = '/home/uwe/express/reegis/data/feedin/solar/'
    lg_path = b_path + 'M_LG290G3__I_ABB_MICRO_025_US208/'
    sf_path = b_path + 'M_SF160S___I_ABB_MICRO_025_US208/'
    pattern = "{0}_feedin_coastdat_de_normalised_solar.h5"
    full = os.path.join(b_path, pattern)
    full_new_lg = os.path.join(lg_path, pattern)
    full_new_sf = os.path.join(sf_path, pattern)
    for year in range(1999, 2015):
        if os.path.isfile(full.format(year)):
            print(full.format(year))
            print(year, calendar.isleap(year))
            if calendar.isleap(year):
                n = 8784
            else:
                n = 8760
            f = pd.HDFStore(full.format(year), mode='r')
            new_lg = pd.HDFStore(full_new_lg.format(year), mode='w')
            new_sf = pd.HDFStore(full_new_sf.format(year), mode='w')
            for key in f.keys():
                ls_lg = list()
                ls_sf = list()
                for col in f[key].columns:
                    if 'LG' in col:
                        ls_lg.append(col)
                    elif 'SF' in col:
                        ls_sf.append(col)
                    else:
                        print(col)
                        print('Oh noo!')
                        exit(0)
                new_lg[key] = f[key][ls_lg][:n]
                new_sf[key] = f[key][ls_sf][:n]

            f.close()
            new_lg.close()
            new_sf.close()


def plz2ireg():
    geopath = '/home/uwe/git_local/reegis-hp/reegis_hp/de21/data/geometries/'
    geofile = 'postcode_polygons.csv'
    plzgeo = pd.read_csv(os.path.join(geopath, geofile), index_col='zip_code',
                         squeeze=True)
    iregpath = '/home/uwe/'
    iregfile = 'plzIreg.csv'
    plzireg = pd.read_csv(os.path.join(iregpath, iregfile), index_col='plz',
                          squeeze=True)
    plzireg = plzireg.groupby(plzireg.index).first()
    ireggeo = pd.DataFrame(pd.concat([plzgeo, plzireg], axis=1))
    ireggeo.to_csv(os.path.join(iregpath, 'ireg_geo.csv'))
    import geoplot
    ireggeo = ireggeo[ireggeo['geom'].notnull()]
    ireggeo['geom'] = geoplot.postgis2shapely(ireggeo.geom)
    geoireg = gpd.GeoDataFrame(ireggeo, crs='epsg:4326', geometry='geom')
    geoireg.to_file(os.path.join(iregpath, 'ireg_geo.shp'))
    # import plots
    # plots.plot_geocsv('/home/uwe/ireg_geo.csv', [0], labels=False)
    exit(0)


def testerich():
    spath = '/home/uwe/chiba/Promotion/Kraftwerke und Speicher/'
    sfile = 'Pumpspeicher_in_Deutschland.csv'
    storage = pd.read_csv(os.path.join(spath, sfile), header=[0, 1])
    storage.sort_index(1, inplace=True)
    print(storage)
    print(storage['ZFES', 'energy'].sum())
    print(storage['Wikipedia', 'energy'].sum())


def decode_wiki_geo_string(gstr):
    replist = [('°', ';'), ('′', ';'), ('″', ';'), ('N.', ''), ('O', ''),
               ('\xa0', ''), (' ', '')]
    if isinstance(gstr, str):
        for rep in replist:
            gstr = gstr.replace(rep[0], rep[1])
        gstr = gstr.split(';')
        lat = float(gstr[0]) + float(gstr[1]) / 60 + float(gstr[2]) / 3600
        lon = float(gstr[3]) + float(gstr[4]) / 60 + float(gstr[5]) / 3600
    else:
        lat = None
        lon = None
    return lat, lon


def offshore():
    spath = '/home/uwe/chiba/Promotion/Kraftwerke und Speicher/'
    sfile = 'offshore_windparks_prepared.csv'
    offsh = pd.read_csv(os.path.join(spath, sfile), header=[0, 1],
                        index_col=[0])
    print(offsh)
    # offsh['Wikipedia', 'geom'] = offsh['Wikipedia', 'geom_str'].apply(
    #     decode_wiki_geo_string)
    # offsh[[('Wikipedia', 'latitude'), ('Wikipedia', 'longitude')]] = offsh[
    #     'Wikipedia', 'geom'].apply(pd.Series)
    # offsh.to_csv(os.path.join(spath, 'offshore_windparks_prepared.csv'))


def bmwe():
    spath = '/home/uwe/chiba/Promotion/Kraftwerke und Speicher/'
    sfile1 = 'installation_bmwe.csv'
    sfile2 = 'strom_bmwe.csv'
    # sfile3 = 'hydro.csv'
    inst = pd.read_csv(os.path.join(spath, sfile1), index_col=[0]).astype(
        float)
    strom = pd.read_csv(os.path.join(spath, sfile2), index_col=[0]).astype(
        float)
    # hydro = pd.read_csv(os.path.join(spath, sfile3), index_col=[0],
    #                     squeeze=True).astype(float)
    cols = pd.MultiIndex(levels=[[], []], labels=[[], []],
                         names=['type', 'value'])
    df = pd.DataFrame(index=inst.index, columns=cols)
    for col in inst.columns:
        df[col, 'capacity'] = inst[col]
        df[col, 'energy'] = strom[col]
    df.to_csv('/home/uwe/git_local/reegis-hp/reegis_hp/de21/data/static/'
              'energy_capacity_bmwi_readme.csv')


def prices():
    # from matplotlib import pyplot as plt
    spath = '/home/uwe/git_local/reegis-hp/reegis_hp/de21/data/static/'
    sfile = 'commodity_sources_prices.csv'
    price = pd.read_csv(os.path.join(spath, sfile),
                        index_col=[0], header=[0, 1])
    print(price)
    price['Erdgas'].plot()
    plt.show()


def load_energiebilanzen():
    spath = '/home/uwe/chiba/Promotion/Energiebilanzen/2014/'
    # sfile = 'Energiebilanz RheinlandPfalz 2014.xlsx'
    sfile = 'Energiebilanz BadenWuerttemberg2014.xls'
    filename = os.path.join(spath, sfile)
    header = pd.read_excel(filename, 0, index=[0, 1, 2, 3, 4], header=None
                           ).iloc[:3, 5:].ffill(axis=1)

    eb = pd.read_excel(filename, 0, skiprows=3, index_col=[0, 1, 2, 3, 4],
                       skip_footer=2)
    eb.columns = pd.MultiIndex.from_arrays(header.values)
    # print(eb)
    # print(eb.loc[pd.IndexSlice[
    #     'ENDENERGIEVERBRAUCH',
    #     :,
    #     :,
    #     84]].transpose())
    eb.sort_index(0, inplace=True)
    eb.sort_index(1, inplace=True)
    #
    print(eb.loc[(slice(None), slice(None), slice(None), 84), 'Braunkohlen'])
    # print(eb.columns)


if __name__ == "__main__":
    # plot_geocsv(os.path.join('geometries', 'federal_states.csv'),
    #             idx_col='iso',
    #             coord_file='data_basic/label_federal_state.csv')
    # plot_geocsv('/home/uwe/geo.csv', idx_col='gid')
    logger.define_logging()
    energy_balance2repo()
    # offshore()
    # load_energiebilanzen()
    # create_intersection_table()
    # prices()
    exit(0)
    plz2ireg()
    # sorter()
    # fetch_coastdat2_year_from_db()
