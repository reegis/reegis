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
import requests
from shapely import wkb

# External libraries
import pandas as pd
import geopandas as gpd

# Internal modules
import reegis_tools.config as cfg
import reegis_tools.geometries as geometries
from reegis_tools import oedb

import oemof.tools.logger as logger


def wkb2wkt(x):
    return wkb.loads(x, hex=True)


def download_oedb(oep_url, schema, table, query, fn):
    gdf = oedb.oedb(oep_url, schema, table, query, 'geom_centre', 3035)
    gdf = gdf.to_crs({'init': 'epsg:4326'})
    logging.info("Write data to {0}".format(fn))
    gdf.to_csv(fn)
    return fn


def get_ego_data():

    oep_url = 'http://oep.iks.cs.ovgu.de/api/v0'
    local_path = cfg.get('paths', 'ego')

    # Large scale consumer
    schema = 'model_draft'
    table = 'ego_demand_hv_largescaleconsumer'
    query = ''
    filename = os.path.join(local_path, 'ego_large_consumer.csv')
    if not os.path.isfile(filename):
        download_oedb(oep_url, schema, table, query, filename)
    large_consumer = pd.read_csv(filename, index_col=[0])

    # Load areas
    schema = 'demand'
    table = 'ego_dp_loadarea'
    query = '?where=version=v0.4.5'
    filename = os.path.join(local_path, 'ego_load_areas.csv')
    if not os.path.isfile(filename):
        download_oedb(oep_url, schema, table, query, filename)
    load_areas = pd.read_csv(filename, index_col=[0])

    load_areas.rename(columns={'sector_consumption_sum': 'consumption'},
                      inplace=True)

    load = pd.concat([load_areas[['consumption', 'geom_centre']],
                      large_consumer[['consumption', 'geom_centre']]])
    return load.rename(columns={'geom_centre': 'geom'})


def prepare_ego_demand(egofile):
    ego_demand = geometries.create_geo_df(get_ego_data())

    # Add column with name of the federal state (Bayern, Berlin,...)
    federal_states = geometries.load(
        cfg.get('paths', 'geometry'),
        cfg.get('geometry', 'federalstates_polygon'))

    # Add column with federal_states
    ego_demand = geometries.spatial_join_with_buffer(
        ego_demand, federal_states, 'federal_states')

    # Overwrite Geometry object with its DataFrame, because it is not
    # needed anymore.
    ego_demand = pd.DataFrame(ego_demand)

    ego_demand['geometry'] = ego_demand['geometry'].astype(str)

    # Write out file (hdf-format).
    ego_demand.to_hdf(egofile, 'demand')

    return ego_demand


def get_ego_demand(overwrite=False):
    egofile = os.path.join(cfg.get('paths', 'demand'),
                           cfg.get('open_ego', 'ego_file'))
    if os.path.isfile(egofile) and not overwrite:
        return pd.read_hdf(egofile, 'demand')
    else:
        return prepare_ego_demand(egofile)


if __name__ == "__main__":
    logger.define_logging()
    ego = get_ego_demand().groupby('federal_states').sum()['consumption']
    print(ego)
    print(ego.sum())
