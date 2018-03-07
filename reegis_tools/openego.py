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

# External libraries
import pandas as pd

# Internal modules
import reegis_tools.config as cfg
import reegis_tools.geometries as geometries


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
        ego_demand, federal_states)

    # Overwrite Geometry object with its DataFrame, because it is not
    # needed anymore.
    ego_demand = pd.DataFrame(ego_demand.gdf)

    # Delete the geometry column, because spatial grouping will be done
    # only with the region column.
    del ego_demand['geometry']

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
    pass
