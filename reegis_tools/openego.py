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

# Internal modules
import reegis_tools.config as cfg
import reegis_tools.geometries as geometries

import oemof.tools.logger as logger


def download_ego_data():

    oep_url = 'http://oep.iks.cs.ovgu.de/api/v0'

    local_path = cfg.get('paths', 'ego')

    # Large scale consumer
    schema = 'model_draft'
    table = 'ego_demand_hv_largescaleconsumer'
    query = ''
    full_url = '{url}/schema/{schema}/tables/{table}/rows/{query}'.format(
        url=oep_url, schema=schema, table=table, query=query)
    logging.info("Download data set from {0}".format(full_url))
    result = requests.get(full_url)
    logging.info("Got results: {0}".format(result.status_code))
    result_df = pd.DataFrame(result.json())
    fn = os.path.join(local_path, 'ego_large_consumer.csv')
    logging.info("Write data to {0}".format(fn))
    result_df.to_csv(fn)

    # Load areas
    schema = 'demand'
    table = 'ego_dp_loadarea'
    query = '?where=version=v0.4.5'
    full_url = '{url}/schema/{schema}/tables/{table}/rows/{query}'.format(
        url=oep_url, schema=schema, table=table, query=query)
    logging.info("Download data set from {0}".format(full_url))
    result = requests.get(full_url)
    logging.info("Got results: {0}".format(result.status_code))
    result_df = pd.DataFrame(result.json())
    fn = os.path.join(local_path, 'ego_load_areas.csv')
    logging.info("Write data to {0}".format(fn))
    result_df.to_csv(fn)


def prepare_ego_demand(egofile):
    ego_demand = geometries.Geometry(name='ego demand')
    ego_demand.load_csv(cfg.get('paths', 'static_sources'),
                        cfg.get('open_ego', 'ego_input_file'))
    ego_demand.create_geo_df(wkt_column='st_astext')

    # Add column with name of the federal state (Bayern, Berlin,...)
    federal_states = geometries.Geometry('federal states')
    federal_states.load(cfg.get('paths', 'geometry'),
                        cfg.get('geometry', 'federalstates_polygon'))

    # Add column with federal_states
    ego_demand.gdf = geometries.spatial_join_with_buffer(
        ego_demand, federal_states, 'federal_states')

    # Overwrite Geometry object with its DataFrame, because it is not
    # needed anymore.
    ego_demand = pd.DataFrame(ego_demand.gdf)

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
    download_ego_data()
    ego = get_ego_demand().groupby('federal_states').sum()[
        'sector_consumption_sum']
    print(ego)
