# -*- coding: utf-8 -*-

"""Reegis geometry tools.

Copyright (c) 2016-2019 Uwe Krien <krien@uni-bremen.de>

SPDX-License-Identifier: MIT
"""
__copyright__ = "Uwe Krien <krien@uni-bremen.de>"
__license__ = "MIT"


# Python libraries
import os
import logging

# Internal libraries
from reegis import config as cfg

# External libraries
import pandas as pd
import geopandas as gpd
from shapely.wkt import loads as wkt_loads
from shapely.geometry import Point
from shapely.geometry.base import BaseGeometry


def get_federal_states_polygon():
    """
    Get a region set for the federal states of Germany.

    Examples
    --------
    >>> list(get_federal_states_polygon().iloc[0:4].index)
    ['HH', 'NI', 'MV', 'SH']
    """
    federal_states = load(
        cfg.get('paths', 'geometry'),
        cfg.get('geometry', 'federalstates_polygon'))
    return federal_states.set_index('iso')


def get_germany_with_awz_polygon():
    """
    Get the polygon of Germany with the exclusive economic zone of Germany in
    one polygon.

    Examples
    --------
    >>> get_germany_with_awz_polygon()['GEN'][0]
    'Deutschland mit AWZ'
    """
    return load(
        cfg.get('paths', 'geometry'),
        'germany_awz_polygon.geojson')


def load(path=None, filename=None, fullname=None, hdf_key=None,
         index_col=None, crs=None):
    """
    Load files with geographic information into a GeoDataFrame.

    Allowed types are csv, hdf, shp and geojson.
    """
    if fullname is None:
        fullname = os.path.join(path, filename)

    suffix = fullname.split('.')[-1]

    if suffix == 'csv':
        df = load_csv(fullname=fullname, index_col=index_col)
        gdf = create_geo_df(df, crs=crs)

    elif suffix == 'hdf' or suffix == 'h5':
        df = pd.DataFrame(load_hdf(fullname=fullname, key=hdf_key))
        gdf = create_geo_df(df, crs=crs)

    elif suffix == 'shp' or suffix == 'geojson':
        gdf = load_shp(fullname=fullname)
        if index_col is not None:
            gdf.set_index(index_col, inplace=True)

    else:
        raise ValueError("Cannot load file with a '{0}' extension.".format(
            suffix))

    return gdf


def load_shp(path=None, filename=None, fullname=None):
    """Load an `shp` file as GeoDataFrame."""
    if fullname is None:
        fullname = os.path.join(path, filename)
    return gpd.read_file(fullname)


def load_hdf(path=None, filename=None, fullname=None, key=None):
    """Load a `hdf` file."""
    if fullname is None:
        fullname = os.path.join(path, filename)
    return pd.read_hdf(fullname, key)


def load_csv(path=None, filename=None, fullname=None,
             index_col=None):
    """Load csv-file into a DataFrame."""
    if fullname is None:
        fullname = os.path.join(path, filename)
    df = pd.read_csv(fullname)

    # Make the first column the index if all values are unique.
    if index_col is None:
        first_col = df.columns[0]
        if not any(df[first_col].duplicated()):
            df.set_index(first_col, drop=True, inplace=True)
    else:
        df.set_index(index_col, drop=True, inplace=True)
    return df


def lat_lon2point(df):
    """Create shapely point object of latitude and longitude."""
    return Point(df['longitude'], df['latitude'])


def create_geo_df(df, wkt_column=None, lon_column=None, lat_column=None,
                  crs=None):
    """Convert pandas.DataFrame to geopandas.geoDataFrame"""
    if 'geom' in df:
        df = df.rename(columns={'geom': 'geometry'})

    if lon_column is not None:
        if lon_column not in df:
            raise ValueError("Cannot find column for longitude: {0}".format(
                lon_column))
        else:
            df.rename(columns={lon_column: 'longitude'}, inplace=True)

    if lat_column is not None:
        if lat_column not in df:
            raise ValueError("Cannot find column for latitude: {0}".format(
                lat_column))
        else:
            df.rename(columns={lat_column: 'latitude'}, inplace=True)

    if wkt_column is not None:
        df['geometry'] = df[wkt_column].apply(wkt_loads)

    elif 'geometry' not in df and 'longitude' in df and 'latitude' in df:

        df['geometry'] = df.apply(lat_lon2point, axis=1)

    elif 'geometry' not in df:
        msg = "Could not create GeoDataFrame. Missing geometries."
        raise ValueError(msg)
    elif isinstance(df.iloc[0]['geometry'], str):
        df['geometry'] = df['geometry'].apply(wkt_loads)
    elif isinstance(df.iloc[0]['geometry'], BaseGeometry):
        pass

    if crs is None:
        crs = {'init': 'epsg:4326'}

    gdf = gpd.GeoDataFrame(df, crs=crs, geometry='geometry')

    logging.debug("GeoDataFrame created.")

    return gdf


def remove_invalid_geometries(gdf):
    """Remove rows that do not have a valid geometry."""
    logging.warning("Invalid geometries have been removed.")
    invalid = gdf.loc[~gdf.is_valid].copy()
    if float(invalid['capacity'].sum()) > 0:
        logging.warning("Removed capacity due to invalid geometry: {0}".format(
            invalid['capacity'].sum()))
    return gdf.loc[gdf.is_valid]


def spatial_join_with_buffer(geo1, geo2, name, jcol='index', step=0.05,
                             limit=1):
    """Add name of containing region to new column for all points.

    Parameters
    ----------
    geo1 : geopandas.geoDataFrame
        Point layer.
    geo2 : geopandas.geoDataFrame
        Polygon layer.
    jcol : str
    name : str
        Name of the new column with the region names/identifiers.
    step : float
    limit : float

    Returns
    -------
    geopandas.geoDataFrame

    """
    if jcol == 'index':
        jcol = 'index_right'

    logging.info("Doing spatial join...")

    # Spatial (left) join with the "within" operation.
    jgdf = gpd.sjoin(geo1, geo2, how='left', op='within')
    logging.info('Joined!')

    diff_cols = set(jgdf.columns) - set(geo1) - {jcol}

    # Buffer all geometries that are not within any polygon
    bf = 0
    len_df = len(jgdf.loc[jgdf[jcol].isnull()])
    if len_df == 0:
        logging.info("Buffering not necessary.")
    elif limit == 0:
        logging.info("No buffering. Buffer-limit is 0.")
    else:
        msg = "Buffering {0} non-matching geometries ({1}%)..."
        logging.info(msg.format(len_df, round(len_df / len(jgdf) * 100, 1)))
    if len_df * 5 > len(jgdf) and limit > 0:
        msg = "{0} % non-matching geometries seems to be too high."
        logging.warning(msg.format(round(len_df / len(jgdf) * 100)))

    while len_df > 0 and bf < limit:
        # Increase the buffer by step.
        bf += step

        # Add the buffer to all rows that did not match.
        jgdf.loc[jgdf[jcol].isnull(), 'buffer'] = jgdf.loc[jgdf[
            jcol].isnull()].buffer(bf)

        # Create a temporary GeoDataFrame with the buffer as geometry
        tmp = jgdf.loc[jgdf[jcol].isnull()]
        del tmp[tmp.geometry.name]
        del tmp[jcol]
        if 'index_right' in tmp:
            del tmp['index_right']
        tmp = tmp.set_geometry('buffer')

        # Try spatial join with "intersects" with buffered geometries.
        newj = gpd.sjoin(tmp, geo2, how='left')

        # If new matches were found they were written to the original GeoDF.
        if len(newj.loc[newj[jcol].notnull() > 0]):
            # If two regions intersects with the buffer the first is taken.
            try:
                jgdf[jcol] = jgdf[jcol].fillna(newj[jcol])
            except ValueError:
                newj = newj[~newj.index.duplicated(keep='first')]
                jgdf[jcol] = jgdf[jcol].fillna(newj[jcol])
                logging.warning(
                    "Two matches found while buffering, first one taken.")
                logging.warning(
                    "Use smaller steps to avoid this behaviour.")
            # Calculate the number of non-matching geometries.
            len_df = len(jgdf.loc[jgdf[jcol].isnull()])
            logging.info(
                "Buffer: {0}, Remaining_length: {1}".format(bf,
                                                            len_df))
            if len_df == 0:
                logging.info("All geometries matched after buffering.")
        if bf == limit:
            logging.info("Stop buffering. Reached buffer limit.")

    # delete the temporary buffer column
    if 'buffer' in jgdf.columns:
        del jgdf['buffer']

    # Remove all columns but the join-id column (jcol) from the GeoDf.
    for col in diff_cols:
        del jgdf[col]

    jgdf = jgdf.rename(columns={jcol: name})
    jgdf[name] = jgdf[name].fillna('unknown')
    logging.info(
        "New column '{0}' added to GeoDataFrame.".format(name))
    return jgdf
