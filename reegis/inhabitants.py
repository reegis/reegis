# -*- coding: utf-8 -*-

"""Aggregate the number of inhabitants for a regions/polygons within Germany.

Copyright (c) 2016-2018 Uwe Krien <uwe.krien@rl-institut.de>

SPDX-License-Identifier: GPL-3.0-or-later
"""
__copyright__ = "Uwe Krien <uwe.krien@rl-institut.de>"
__license__ = "GPLv3"


# Python libraries
import os
import zipfile
import shutil
import glob
import logging

if not os.environ.get('READTHEDOCS') == 'True':
    # External libraries
    import pandas as pd
    import geopandas as gpd

    # Internal modules
    import reegis.config as cfg
    import reegis.geometries
    import reegis.tools as tools


def get_ew_shp_file(year):
    if year < 2011:
        logging.error("Shapefile with inhabitants are available since 2011.")
        logging.error("Try to find another source to get older data sets.")
        raise AttributeError('Years < 2011 are not allowed in this function.')

    outshp = os.path.join(cfg.get('paths', 'inhabitants'),
                          'VG250_VWG_' + str(year) + '.shp')

    if not os.path.isfile(outshp):
        url = cfg.get('inhabitants', 'url_geodata_ew').format(year=year,
                                                              var1='{0}')
        filename_zip = os.path.join(cfg.get('paths', 'inhabitants'),
                                    cfg.get('inhabitants', 'vg250_ew_zip'))
        msg = tools.download_file(filename_zip, url.format('ebene'))
        if msg == 404:
            logging.warning("Wrong URL. Try again with different URL.")
            tools.download_file(
                filename_zip, url.format('ebenen'), overwrite=True)

        zip_ref = zipfile.ZipFile(filename_zip, 'r')
        zip_ref.extractall(cfg.get('paths', 'inhabitants'))
        zip_ref.close()
        subs = next(os.walk(cfg.get('paths', 'inhabitants')))[1]
        mysub = None
        for sub in subs:
            if 'vg250' in sub:
                mysub = sub
        pattern_path = list()

        pattern_path.append(os.path.join(cfg.get('paths', 'inhabitants'),
                                         mysub,
                                         'vg250-ew_ebenen',
                                         'VG250_VWG*'))
        pattern_path.append(os.path.join(cfg.get('paths', 'inhabitants'),
                                         mysub,
                                         'vg250-ew_ebenen',
                                         'vg250_vwg*'))
        pattern_path.append(os.path.join(cfg.get('paths', 'inhabitants'),
                                         mysub,
                                         'vg250_ebenen-historisch',
                                         'de{0}12'.format(str(year)[-2:]),
                                         'vg250_vwg*'))

        for pa_path in pattern_path:
            for file in glob.glob(pa_path):
                file_new = os.path.join(cfg.get('paths', 'inhabitants'),
                                        'VG250_VWG_' + str(year) + file[-4:])
                shutil.copyfile(file, file_new)

        shutil.rmtree(os.path.join(cfg.get('paths', 'inhabitants'), mysub))

        os.remove(filename_zip)


def get_ew_geometry(year, polygon=False):
    filename_shp = os.path.join(cfg.get('paths', 'inhabitants'),
                                'VG250_VWG_' + str(year) + '.shp')

    if not os.path.isfile(filename_shp):
        get_ew_shp_file(year)

    vwg = gpd.read_file(filename_shp)

    # replace polygon geometry by its centroid
    if polygon is False:
        vwg['geometry'] = vwg.representative_point()

    return vwg


def get_ew_by_region(year, geo, name):
    """

    Parameters
    ----------
    year
    geo
    name

    Returns
    -------
    pd.DataFrame

    Examples
    --------
    >>> geo = reegis.geometries.load(
    ...     cfg.get('paths', 'geometry'),
    ...     cfg.get('geometry', 'federalstates_polygon'))
    >>> name = 'federal_states'
    >>> get_ew_by_region(2014, geo, name=name).sum()  # doctest: +SKIP
    81197537
    """
    ew = get_ew_geometry(year)
    ew = reegis.geometries.spatial_join_with_buffer(
        ew, geo, name=name, step=0.005)
    return ew.groupby(name).sum()['EWZ']


def get_ew_by_federal_states(year):
    geo = reegis.geometries.load(
        cfg.get('paths', 'geometry'),
        cfg.get('geometry', 'federalstates_polygon'))
    geo.set_index('iso', drop=True, inplace=True)
    geo.drop(['N0', 'N1', 'O0', 'P0'], inplace=True)
    return get_ew_by_region(year, geo, name='federal_states')


if __name__ == "__main__":
    pass
