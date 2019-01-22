# -*- coding: utf-8 -*-

"""Reegis geometry tools.

Copyright (c) 2016-2018 Uwe Krien <uwe.krien@rl-institut.de>

SPDX-License-Identifier: GPL-3.0-or-later
"""
__copyright__ = "Uwe Krien <uwe.krien@rl-institut.de>"
__license__ = "GPLv3"


# Python libraries
import os
import logging
import warnings

# External libraries
import pandas as pd
import geopandas as gpd
from shapely.wkt import loads as wkt_loads
from shapely.geometry import Point
from shapely.geometry.base import BaseGeometry


class Geometry:
    """Reegis geometry class.

    Attributes
    ----------
    name : str
    df = pandas.DataFrame
    gdf = geopandas.GeoDataFrame
    invalid = pandas.Dataframe
    lon_column : str
    lat_column :str

    """
    def __init__(self, name='no_name', df=None):
        self.name = name
        self.df = df
        self.gdf = None
        self.invalid = None
        self.lon_column = 'lon'
        self.lat_column = 'lat'

    def load(self, path=None, filename=None, fullname=None, hdf_key=None,
             index_col=None):
        """Load csv-file into a DataFrame and a GeoDataFrame."""
        if fullname is None:
            fullname = os.path.join(path, filename)

        if fullname[-4:] == '.csv':
            self.load_csv(fullname=fullname, index_col=index_col)

        elif fullname[-4:] == '.hdf':
            self.load_hdf(fullname=fullname, key=hdf_key)

        elif fullname[-4:] == '.shp':
            self.load_shp(fullname=fullname)

        else:
            raise ValueError("Cannot load file with a '{0}' extension.")

        self.create_geo_df()
        return self

    def load_shp(self, path=None, filename=None, fullname=None):
        if fullname is None:
            fullname = os.path.join(path, filename)
        self.df = gpd.read_file(fullname)

    def load_hdf(self, path=None, filename=None, fullname=None, key=None):
        if fullname is None:
            fullname = os.path.join(path, filename)
        self.df = pd.read_hdf(fullname, key, mode='r')

    def load_csv(self, path=None, filename=None, fullname=None,
                 index_col=None):
        """Load csv-file into a DataFrame."""
        if fullname is None:
            fullname = os.path.join(path, filename)
        self.df = pd.read_csv(fullname)

        # Make the first column the index if all values are unique.
        if index_col is None:
            first_col = self.df.columns[0]
            if not any(self.df[first_col].duplicated()):
                self.df.set_index(first_col, drop=True, inplace=True)
        else:
            self.df.set_index(index_col, drop=True, inplace=True)

    def lat_lon2point(self, df):
        """Create shapely point object of latitude and longitude."""
        return Point(df[self.lon_column], df[self.lat_column])

    def create_geo_df(self, wkt_column=None, keep_wkt=False,
                      lon_col=None, lat_col=None, update=False):
        """Convert pandas.DataFrame to geopandas.geoDataFrame"""
        if 'geom' in self.df:
            self.df = self.df.rename(columns={'geom': 'geometry'})
        if lon_col is not None:
            self.lon_column = lon_col
        if lat_col is not None:
            self.lat_column = lat_col
        if wkt_column is not None:
            self.df['geometry'] = self.df[wkt_column].apply(wkt_loads)
            if not keep_wkt and wkt_column != 'geometry':
                del self.df[wkt_column]
        elif ('geometry' not in self.df and self.lon_column in self.df and
                self.lat_column in self.df):
            self.df['geometry'] = self.df.apply(self.lat_lon2point, axis=1)
        elif isinstance(self.df.iloc[0]['geometry'], str):
            self.df['geometry'] = self.df['geometry'].apply(wkt_loads)
        # else:
            # msg = "Could not create GeoDataFrame {0}. Missing geometries."
            # logging.error(msg.format(self.name))
            # return None
        if self.gdf is None or update:
            self.gdf = gpd.GeoDataFrame(self.df, crs={'init': 'epsg:4326'},
                                        geometry='geometry')
            logging.info("GeoDataFrame for {0} created.".format(self.name))
        self.df = None
        return self

    def get_df(self, geo_as_str=True):
        df = pd.DataFrame(self.gdf)
        if geo_as_str:
            df['geometry'] = df['geometry'].astype(str)
        return df

    def remove_invalid_geometries(self):
        if self.gdf is not None:
            logging.warning("Invalid geometries have been removed.")
            self.invalid = self.gdf.loc[~self.gdf.is_valid].copy()
            self.gdf = self.gdf.loc[self.gdf.is_valid]
        else:
            logging.error("No GeoDataFrame to remove invalid geometries from.")

    def plot(self, *args, **kwargs):
        self.gdf.plot(*args, **kwargs)


def load(path=None, filename=None, fullname=None, hdf_key=None,
         index_col=None, crs=None):
    """Load csv-file into a DataFrame and a GeoDataFrame."""
    if fullname is None:
        fullname = os.path.join(path, filename)

    if fullname[-4:] == '.csv':
        df = load_csv(fullname=fullname, index_col=index_col)
        gdf = create_geo_df(df, crs=crs)

    elif fullname[-4:] == '.hdf':
        df = pd.DataFrame(load_hdf(fullname=fullname, key=hdf_key))
        gdf = create_geo_df(df, crs=crs)

    elif fullname[-4:] == '.shp':
        gdf = load_shp(fullname=fullname)

    else:
        raise ValueError("Cannot load file with a '{0}' extension.")

    return gdf


def load_shp(path=None, filename=None, fullname=None):
    if fullname is None:
        fullname = os.path.join(path, filename)
    return gpd.read_file(fullname)


def load_hdf(path=None, filename=None, fullname=None, key=None):
    if fullname is None:
        fullname = os.path.join(path, filename)
    return pd.read_hdf(fullname, key, mode='r')


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
            logging.error("Cannot find column for longitude: {0}".format(
                lon_column))
        else:
            df.rename(columns={lon_column: 'longitude'}, inplace=True)

    if lat_column is not None:
        if lat_column not in df:
            logging.error("Cannot find column for latitude: {0}".format(
                lat_column))
        else:
            df.rename(columns={lat_column: 'latitude'}, inplace=True)

    if wkt_column is not None:
        df['geometry'] = df[wkt_column].apply(wkt_loads)

    elif 'geometry' not in df and 'longitude' in df and 'latitude' in df:

        df['geometry'] = df.apply(lat_lon2point, axis=1)

    elif isinstance(df.iloc[0]['geometry'], str):
        df['geometry'] = df['geometry'].apply(wkt_loads)
    elif isinstance(df.iloc[0]['geometry'], BaseGeometry):
        pass
    else:
        msg = "Could not create GeoDataFrame. Missing geometries."
        logging.error(msg)
        return None

    if crs is None:
        crs = {'init': 'epsg:4326'}

    gdf = gpd.GeoDataFrame(df, crs=crs, geometry='geometry')

    logging.debug("GeoDataFrame created.")

    return gdf


def gdf2df(gdf, remove_geo=False):
    df = pd.DataFrame(gdf)
    if not remove_geo:
        df['geometry'] = df['geometry'].astype(str)
    else:
        del df['geometry']
    return df


def remove_invalid_geometries(gdf):
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
    geo1 : reegis.geometries.Geometry or geopandas.geoDataFrame
        Point layer.
    geo2 : reegis.geometries.Geometry or geopandas.geoDataFrame
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

    if isinstance(geo1, Geometry):
        geo1 = geo1.gdf

    if isinstance(geo2, Geometry):
        geo2 = geo2.gdf

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
        newj = gpd.sjoin(tmp, geo2, how='left', op='intersects')

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
