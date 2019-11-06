# -*- coding: utf-8 -*-

"""Processing the openego map for the electricity demand.

Copyright (c) 2016-2019 Uwe Krien <krien@uni-bremen.de>

SPDX-License-Identifier: MIT
"""
__copyright__ = "Uwe Krien <krien@uni-bremen.de>"
__license__ = "MIT"


# Python libraries
import os
import logging
from shapely import wkb
import warnings

# External libraries
import pandas as pd

# Internal modules
from reegis import config as cfg
from reegis import geometries
from reegis import bmwi as bmwi_data
from reegis import oedb
from reegis import tools


def wkb2wkt(x):
    """Loads geometry from wkb."""
    return wkb.loads(x, hex=True)


def download_oedb(oep_url, schema, table, query, fn, overwrite=False):
    """Download map from oedb in WGS84 and store as csv file."""
    if not os.path.isfile(fn) or overwrite:
        gdf = oedb.oedb(oep_url, schema, table, query, 'geom_centre', 3035)
        gdf = gdf.to_crs({'init': 'epsg:4326'})
        logging.info("Write data to {0}".format(fn))
        gdf.to_csv(fn)
    else:
        logging.debug("File {0} exists. Nothing to download.".format(fn))
    return fn


def get_ego_data(osf=True, query='?where=version=v0.4.5'):
    """

    Parameters
    ----------
    osf : bool
        If True the file will be downloaded from the osf page instead of of
        selected from the database. You may not get the latest version.
        (default: False)
    query : str
        Database query to filter the data set.
        (default: '?where=version=v0.4.5')

    Returns
    -------

    Examples
    --------
    >>> from reegis import openego
    >>> # download from file (faster)
    >>> openego.get_ego_data()  # doctest: +SKIP
    >>> # download from oedb database (get latest updates, very slow)
    >>> openego.get_ego_data(osf=False)  # doctest: +SKIP
    """
    oep_url = 'http://oep.iks.cs.ovgu.de/api/v0'
    local_path = cfg.get('paths', 'ego')
    fn_large_consumer = os.path.join(
        local_path, cfg.get('open_ego', 'ego_large_consumers'))
    fn_load_areas = os.path.join(
        local_path, cfg.get('open_ego', 'ego_load_areas'))

    # Large scale consumer
    schema = 'model_draft'
    table = 'ego_demand_hv_largescaleconsumer'
    query_lsc = ''
    download_oedb(oep_url, schema, table, query_lsc, fn_large_consumer)
    large_consumer = pd.read_csv(fn_large_consumer, index_col=[0])

    msg = ("\nYou are going to download the load areas from file created "
           "2019-10-09.\nThis is much faster and useful for most users but you"
           " may find more actual data on the oedb database.\n"
           "Please check: https://openenergy-platform.org/dataedit/view/demand"
           "/ego_dp_loadarea \n"
           "Use 'openego.get_ego_data(osf=False)' to fetch data from oedb.\n")

    # Load areas
    if osf is True:
        warnings.warn(msg)
        url = cfg.get('open_ego', 'osf_url')
        tools.download_file(fn_load_areas, url)
        load_areas = pd.DataFrame(pd.read_csv(fn_load_areas, index_col=[0]))
    else:
        schema = 'demand'
        table = 'ego_dp_loadarea'
        download_oedb(oep_url, schema, table, query, fn_load_areas)
        load_areas = pd.DataFrame(pd.read_csv(fn_load_areas, index_col=[0]))

    load_areas.rename(columns={'sector_consumption_sum': 'consumption'},
                      inplace=True)

    load = pd.concat([load_areas[['consumption', 'geom_centre']],
                      large_consumer[['consumption', 'geom_centre']]])
    load = load.rename(columns={'geom_centre': 'geom'})

    return load.reset_index()


def get_ego_demand(filename=None, fn=None, overwrite=False):
    """

    Parameters
    ----------
    filename : str
    fn  : str
    overwrite : bool

    Returns
    -------
    pandas.DataFrame

    """
    if filename is None:
        filename = cfg.get('open_ego', 'ego_file')
    if fn is None:
        path = cfg.get('paths', 'demand')
        fn = os.path.join(path, filename)

    if os.path.isfile(fn) and not overwrite:
        return pd.DataFrame(pd.read_hdf(fn, 'demand'))
    else:
        load = get_ego_data(osf=True)
        load.to_hdf(fn, 'demand')
        return load


def get_ego_demand_by_region(regions, name, outfile=None, infile=None,
                             dump=False, grouped=False, overwrite=False):
    """
    Add the region id from a given region set to the openego demand table. This
    can be used to calculate the demand or the share of each region.

    Parameters
    ----------
    regions : GeoDataFrame
        A region set.
    name : str
        The name of the region set will be used as the name of the column in
        the openego GeoDataFrame and to distinguish result files.
    outfile : str (optional)
        It is possible to pass a filename (with path) where the results should
        be stored. Only valid if `dump` is True.
    infile : str (optional)
        It is possible to use a specific infile (with path) where the openego
        map is stored.
    dump : bool
        If dump is True the result will be returned and stored into a file.
        Otherwise the result is just returned. (default: False)
    grouped : bool
        If grouped is False the openego table with a region column is returned.
        Otherwise the map is grouped by the region column and the consumption
        column is summed up. (default: False)
    overwrite : bool

    Returns
    -------
    pandas.DataFrame or pandas.Series : A Series is returned if grouped is
        True.

    Notes
    -----
    The openego map may not be updated in the future so it might be necessary
    to scale the results to an overall demand.

    Examples
    --------
    >>> federal_states = geometries.get_federal_states_polygon()
    >>> bmwi_annual = bmwi_data.get_annual_electricity_demand_bmwi(
    ...    2015)  # doctest: +SKIP

    >>> ego_demand = get_ego_demand_by_region(
    ...     federal_states, 'federal_states', grouped=True)  # doctest: +SKIP

    >>> ego_demand.div(ego_demand.sum()).mul(bmwi_annual)  # doctest: +SKIP

    """
    if outfile is None:
        path = cfg.get('paths', 'demand')
        outfile = os.path.join(path, 'open_ego_demand_{0}.h5')
        outfile = outfile.format(name)

    if not os.path.isfile(outfile) or overwrite:
        ego_data = get_ego_demand(filename=infile)
        ego_demand = geometries.create_geo_df(ego_data)

        # Add column with regions
        ego_demand = geometries.spatial_join_with_buffer(
            ego_demand, regions, name)

        # Overwrite Geometry object with its DataFrame, because it is not
        # needed anymore.
        ego_demand = pd.DataFrame(ego_demand)

        ego_demand['geometry'] = ego_demand['geometry'].astype(str)

        # Write out file (hdf-format).
        if dump is True:
            ego_demand.to_hdf(outfile, 'demand')
    else:
        ego_demand = pd.DataFrame(pd.read_hdf(outfile, 'demand'))

    if grouped is True:
        return ego_demand.groupby(name)['consumption'].sum()
    else:
        return ego_demand


if __name__ == "__main__":
    pass
