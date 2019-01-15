import requests
from shapely import wkb
import pandas as pd
import geopandas as gpd
import logging


def wkb2wkt(x):
    """Converts the binary postgis format to WKT such as 'POINT (12.5 53.1)'"""
    return wkb.loads(x, hex=True)


def oedb(oep_url, schema, table, query, geo_column, epsg):
    """Create a geoDataFrame from a oedb selection."""
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
    from matplotlib import pyplot as plt

    basic_url = 'http://oep.iks.cs.ovgu.de/api/v0'

    my_request = {
        'schema': 'boundaries',
        'table': 'bkg_vg250_1_sta',
        'geo_column': 'geom',
        'query': '',
        'epsg': 31467}
    ax = oedb(basic_url, **my_request).plot(color='#999999')

    my_request = {
        'schema': 'model_draft',
        'table': 'ego_demand_hv_largescaleconsumer',
        'geo_column': 'geom_centre',
        'query': '',  # '?where=version=v0.4.5'
        'epsg': 3035}
    oedb(basic_url, **my_request).to_crs({'init': 'epsg:31467'}).plot(ax=ax)

    plt.show()
