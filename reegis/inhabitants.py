# -*- coding: utf-8 -*-

"""Aggregate the number of inhabitants for a regions/polygons within Germany.

Copyright (c) 2016-2019 Uwe Krien <krien@uni-bremen.de>

SPDX-License-Identifier: MIT
"""
__copyright__ = "Uwe Krien <krien@uni-bremen.de>"
__license__ = "MIT"


# Python libraries
import os
import zipfile
import shutil
import glob
import logging

# External libraries
import geopandas as gpd

# Internal modules
from reegis import config as cfg
from reegis import geometries
from reegis import tools


def get_ew_shp_file(year):
    """

    Parameters
    ----------
    year

    Returns
    -------

    Examples
    --------
    >>> print(get_ew_shp_file(2014)[-35:])
    data/inhabitants/VG250_VWG_2014.shp
    """
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

        zip_ref = zipfile.ZipFile(filename_zip)
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
    return outshp


def get_ew_geometry(year, polygon=False):
    """Get a map with the number of inhabitants."""
    filename_shp = os.path.join(cfg.get('paths', 'inhabitants'),
                                'VG250_VWG_' + str(year) + '.shp')

    if not os.path.isfile(filename_shp):
        get_ew_shp_file(year)

    vwg = gpd.read_file(filename_shp)

    # replace polygon geometry by its centroid
    if polygon is False:
        vwg['geometry'] = vwg.representative_point()

    return vwg


def get_inhabitants_by_region(year, geo, name):
    """
    Get inhabitants for the given region polygons.

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
    >>> geo = geometries.get_federal_states_polygon()
    >>> get_inhabitants_by_region(2014, geo, name='federal_states').sum()
    81197537
    """
    ew = get_ew_geometry(year)
    ew = geometries.spatial_join_with_buffer(
        ew, geo, name=name, step=0.005)

    return ew.groupby(name).sum()['EWZ']


def get_inhabitants_by_multi_regions(year, geo, name):
    """
    Get a MultiIndex table with the inhabitants from all given geometry sets.

    Parameters
    ----------
    year : int
    geo : tuple or list
    name : tuple or list

    Returns
    -------

    Examples
    --------
    >>> geo1 = geometries.load(
    ...     cfg.get('paths', 'geometry'),
    ...     cfg.get('geometry', 'de21_polygons'), index_col='region')
    >>> geo2 = geometries.get_federal_states_polygon()
    >>> inh = get_inhabitants_by_multi_regions(
    ...     2014, [geo1, geo2], ['de21', 'fs'])
    >>> inh.loc['DE01']['BB']
    1811137
    >>> inh.loc['DE01']['BE']
    3469849

    """
    ew = get_ew_geometry(year)
    n = 0
    for geo_one in geo:
        ew = geometries.spatial_join_with_buffer(
            ew, geo_one, name=name[n], step=0.005)
        n += 1

    return ew.groupby(name).sum()['EWZ']


def get_share_of_federal_states_by_region(year, regions, name):
    """

    Parameters
    ----------
    year : int
    regions : tuple or list
    name : tuple or list

    Returns
    -------

    Examples
    --------
    >>> regions = geometries.load(
    ...     cfg.get('paths', 'geometry'),
    ...     cfg.get('geometry', 'de21_polygons'), index_col='region')
    >>> inh = get_share_of_federal_states_by_region(2014, regions, 'de21')
    >>> round(inh.loc['DE01']['BB'], 2)
    0.74
    >>> round(inh.loc['DE01']['BE'], 2)
    1.0
    """
    # Get inhabitants for federal states and the given regions
    fs_geo = geometries.get_federal_states_polygon()
    ew = get_inhabitants_by_multi_regions(
        year, [regions, fs_geo], name=[name, 'federal_states'])
    ew = ew[ew != 0]

    # Calculate the share of the federal states within the regions.
    fs_sum = ew.groupby(level=1).sum().copy()
    for reg in ew.index.get_level_values(0).unique():
        for fs in ew.loc[reg].index:
            ew.loc[reg, fs] = ew.loc[reg, fs] / fs_sum[fs]
    return ew


def get_ew_by_federal_states(year):
    """Get the inhabitants per federal state for a given year."""
    geo = geometries.load(
        cfg.get('paths', 'geometry'),
        cfg.get('geometry', 'federalstates_polygon'))
    geo.set_index('iso', drop=True, inplace=True)
    geo.drop(['N0', 'N1', 'O0', 'P0'], inplace=True)
    return get_inhabitants_by_region(year, geo, name='federal_states')


if __name__ == "__main__":
    pass
