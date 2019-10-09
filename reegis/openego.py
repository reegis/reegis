# -*- coding: utf-8 -*-

""" This module is designed to download and prepare BMWI data.

Copyright (c) 2016-2018 Uwe Krien <uwe.krien@rl-institut.de>

SPDX-License-Identifier: GPL-3.0-or-later
"""
__copyright__ = "Uwe Krien <uwe.krien@rl-institut.de>"
__license__ = "GPLv3"


# Python libraries
import os
import logging
from shapely import wkb

# External libraries
import pandas as pd

# Internal modules
import reegis.config as cfg
import reegis.geometries as geometries
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


def get_ego_data(osf=False, query='?where=version=v0.4.5'):

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

    # Load areas
    if osf is True:
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
    if filename is None:
        filename = cfg.get('open_ego', 'ego_file')
    if fn is None:
        path = cfg.get('paths', 'demand')
        fn = os.path.join(path, filename)

    if os.path.isfile(fn) and not overwrite:
        return pd.DataFrame(pd.read_hdf(fn, 'demand'))
    else:
        load = get_ego_data()
        load.to_hdf(fn, 'demand')
        return load


def get_ego_demand_by_region(regions, name, outfile=None, infile=None,
                             dump=False, grouped=False, overwrite=False):
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


def get_ego_demand_by_federal_states(year=None, grouped=True):
    """CHANGE NAME OF FUNCTION BECAUSE OF SCALING"""
    federal_states = geometries.get_federal_states_polygon()
    bmwi_annual = bmwi_data.get_annual_electricity_demand_bmwi(year)

    ego_demand = get_ego_demand_by_region(
        federal_states, 'federal_states', grouped=grouped)

    return ego_demand.div(ego_demand.sum()).mul(bmwi_annual)


if __name__ == "__main__":
    pass
