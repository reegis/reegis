# -*- coding: utf-8 -*-

"""Aggregate the number of inhabitants for a regions/polygons within Germany.

Copyright (c) 2016-2018 Uwe Krien <uwe.krien@rl-institut.de>

SPDX-License-Identifier: GPL-3.0-or-later
"""
__copyright__ = "Uwe Krien <uwe.krien@rl-institut.de>"
__license__ = "GPLv3"

import os
import logging

if not os.environ.get('READTHEDOCS') == 'True':
    import requests
    from shapely import wkb
    import pandas as pd
    import geopandas as gpd


def wkb2wkt(x):
    """Converts the binary postgis format to WKT such as 'POINT (12.5 53.1)'"""
    return wkb.loads(x, hex=True)


def oedb(oep_url, schema, table, query, geo_column, epsg):
    """Create a geoDataFrame from a oedb selection.

    Examples
    --------
    >>> basic_url = 'http://oep.iks.cs.ovgu.de/api/v0'
    >>> my_request = {
    ...     'schema': 'model_draft',
    ...     'table': 'ego_demand_hv_largescaleconsumer',
    ...     'geo_column': 'geom_centre',
    ...     'query': '',  # '?where=version=v0.4.5'
    ...     'epsg': 3035}
    >>> consumer = oedb(basic_url, **my_request)
    >>> int(pd.to_numeric(consumer['consumption']).sum())
    26181

    """
    full_url = '{url}/schema/{schema}/tables/{table}/rows/{query}'.format(
        url=oep_url, schema=schema, table=table, query=query)

    logging.info("Download data set from {0}".format(full_url))
    result = requests.get(full_url)
    logging.debug("Got results: {0}".format(result.status_code))
    logging.info("Convert results to geoDataFrame.")
    result_df = pd.DataFrame(result.json())
    result_df[geo_column] = result_df[geo_column].apply(wkb2wkt)
    crs = {'init': 'epsg:{0}'.format(epsg)}
    return gpd.GeoDataFrame(result_df, crs=crs, geometry=geo_column)


if __name__ == "__main__":
    pass
