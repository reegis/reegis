"""
Reegis geometry tools.

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
import geopandas as gpd
from shapely.wkt import loads as wkt_loads
from shapely.geometry import Point


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

    def load(self, path=None, filename=None, fullname=None, hdf_key=None):
        """Load csv-file into a DataFrame and a GeoDataFrame."""
        if hdf_key is None:
            self.load_csv(path, filename, fullname)
        else:
            self.load_hdf(path, filename, fullname, hdf_key)
        self.create_geo_df()
        return self

    def load_hdf(self, path=None, filename=None, fullname=None, key=None):
        if fullname is None:
            fullname = os.path.join(path, filename)
        self.df = pd.read_hdf(fullname, key, mode='r')

    def load_csv(self, path=None, filename=None, fullname=None):
        """Load csv-file into a DataFrame."""
        if fullname is None:
            fullname = os.path.join(path, filename)
        self.df = pd.read_csv(fullname)

        # Make the first column the index if all values are unique.
        first_col = self.df.columns[0]
        if not any(self.df[first_col].duplicated()):
            self.df.set_index(first_col, drop=True, inplace=True)

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
        return self

    def gdf2df(self):
        """Update DataFrame with the content of the GeoDataFrame.
        The geometry column will be converted to a WKT-string.
        """
        print("*******DO NOT USE IT!!!!!***************Use to_csv!!!!!")
        self.df = pd.DataFrame(self.gdf)
        self.df['geometry'] = self.df['geometry'].astype(str)

    def to_csv(self, *args, **kwargs):
        df = pd.DataFrame(self.gdf)
        df['geometry'] = df['geometry'].astype(str)
        df.to_csv(*args, **kwargs)

    def remove_invalid_geometries(self):
        if self.gdf is not None:
            logging.warning("Invalid geometries have been removed.")
            self.invalid = self.gdf.loc[~self.gdf.is_valid].copy()
            self.gdf = self.gdf.loc[self.gdf.is_valid]
        else:
            logging.error("No GeoDataFrame to remove invalid geometries from.")

    def plot(self, *args, **kwargs):
        self.gdf.plot(*args, **kwargs)


def spatial_join_with_buffer(geo1, geo2, jcol='index', name=None,
                             step=0.05, limit=1):
    """Add name of containing region to new column for all points.

    Parameters
    ----------
    geo1 : reegis_tools.geometries.Geometry
    geo2 : reegis_tools.geometries.Geometry
    jcol : str
    name : str
    step : float
    limit : float

    Returns
    -------
    geopandas.geoDataFrame

    """
    if jcol == 'index':
        jcol = 'index_right'

    logging.info("Doing spatial join with buffer.")

    # Spatial (left) join with the "within" operation.
    jgdf = gpd.sjoin(geo1.gdf, geo2.gdf, how='left', op='within')
    logging.info('Joined!')
    # jgdf.to_csv('/home/uwe/test.csv')

    diff_cols = set(jgdf.columns) - set(geo1.gdf) - {jcol}

    # Buffer all geometries that are not within any polygon
    bf = 0
    len_df = len(jgdf.loc[jgdf[jcol].isnull()])
    if len_df == 0:
        logging.info("Buffering not necessary.")
    else:
        logging.info("Buffering non-matching geometries...")
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
        tmp = tmp.set_geometry('buffer')

        # Try spatial join with "intersects" with buffered geometries.
        newj = gpd.sjoin(tmp, geo2.gdf, how='left', op='intersects')

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

    # Rename the column to a given name or the name of the Geometry object.
    if name is None:
        name = "_".join(geo2.name.split())

    jgdf = jgdf.rename(columns={jcol: name})
    jgdf[name] = jgdf[name].fillna('unknown')
    logging.info(
        "New column '{0}' added to GeoDataFrame.".format(name))
    return jgdf
