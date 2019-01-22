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
from reegis import bmwi
from reegis import oedb

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
    load = load.rename(columns={'geom_centre': 'geom'})

    filename = cfg.get('open_ego', 'ego_file')
    path = cfg.get('paths', 'demand')
    fn = os.path.join(path, filename)
    load.to_hdf(fn, 'demand')
    return load


def get_ego_demand(filename=None, fn=None, overwrite=False):
    if filename is None:
        filename = cfg.get('open_ego', 'ego_file')
    if fn is None:
        path = cfg.get('paths', 'demand')
        fn = os.path.join(path, filename)

    if os.path.isfile(fn) and not overwrite:
        return pd.DataFrame(pd.read_hdf(fn, 'demand'))
    else:
        return get_ego_data()


def ego_demand_by_region(regions, name, outfile=None, dump=False):
    ego_data = get_ego_demand()

    ego_demand = geometries.create_geo_df(ego_data)

    # Add column with regions
    ego_demand = geometries.spatial_join_with_buffer(
        ego_demand, regions, name)

    # Overwrite Geometry object with its DataFrame, because it is not
    # needed anymore.
    ego_demand = pd.DataFrame(ego_demand)

    ego_demand['geometry'] = ego_demand['geometry'].astype(str)

    if outfile is not None:
        path = cfg.get('paths', 'demand')
        outfile = os.path.join(path, 'open_ego_demand_{0}.h5')

    # Write out file (hdf-format).
    if dump is True:
        ego_demand.to_hdf(outfile, 'demand')

    return ego_demand


def get_ego_demand_by_federal_states(year=None):
    federal_states = geometries.load(
        cfg.get('paths', 'geometry'),
        cfg.get('geometry', 'federalstates_polygon'))
    if year is None:
        return ego_demand_by_region(federal_states, 'federal_states')
    else:
        return get_ego_demand_bmwi_by_region(year, federal_states,
                                             'federal_states')


def get_ego_demand_bmwi_by_region(year, regions, name):
    demand = ego_demand_by_region(regions, name)
    summe = demand['consumption'].sum()
    annual = bmwi.get_annual_electricity_demand_bmwi(year)
    factor = annual * 1000 / summe
    demand['consumption'] = demand['consumption'].mul(factor)
    return demand


if __name__ == "__main__":
    logger.define_logging()
    my_demand = get_ego_demand_by_federal_states().groupby(
        'federal_states').sum()['consumption']
    print(my_demand.sum())
    print(bmwi.get_annual_electricity_demand_bmwi(2014) * 1000)
    print(get_ego_demand_by_federal_states(year=2014).sum()['consumption'])
