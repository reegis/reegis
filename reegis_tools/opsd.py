"""
Download and process the opsd power plants for Germany.

Copyright (c) 2016-2018 Uwe Krien <uwe.krien@rl-institut.de>

SPDX-License-Identifier: GPL-3.0-or-later
"""
__copyright__ = "Uwe Krien <uwe.krien@rl-institut.de>"
__license__ = "GPLv3"


# Python libraries
import os
import logging
import datetime

# External libraries
import numpy as np
import pandas as pd
import pyproj
import requests
from shapely.wkt import loads as wkt_loads

# oemof libraries
from oemof.tools import logger

# Internal modules
import reegis_tools.config as cfg
import reegis_tools.geometries as geo


def convert_utm_code_opsd(df):
    # *** Convert utm if present ***
    utm_zones = list()
    # Get all utm zones.
    if 'utm_zone' in df:
        df_utm = df.loc[(df.lon.isnull()) & (df.utm_zone.notnull())]

        utm_zones = df_utm.utm_zone.unique()

    # Loop over utm zones and convert utm coordinates to latitude/longitude.
    for zone in utm_zones:
        my_utm = pyproj.Proj(
            "+proj=utm +zone={0},+north,+ellps=WGS84,".format(str(int(zone))) +
            "+datum=WGS84,+units=m,+no_defs")
        utm_df = df_utm.loc[df_utm.utm_zone == int(zone),
                            ('utm_east', 'utm_north')]
        coord = my_utm(utm_df.utm_east.values, utm_df.utm_north.values,
                       inverse=True)
        df.loc[(df.lon.isnull()) & (df.utm_zone == int(zone)), 'lat'] = (
            coord[1])
        df.loc[(df.lon.isnull()) & (df.utm_zone == int(zone)), 'lon'] = (
            coord[0])
    return df


def guess_coordinates_by_postcode_opsd(df):
    # *** Use postcode ***
    if 'postcode' in df:
        df_pstc = df.loc[(df.lon.isnull() & df.postcode.notnull())]
        if len(df_pstc) > 0:
            pstc = pd.read_csv(
                os.path.join(cfg.get('paths', 'geometry'),
                             cfg.get('geometry', 'postcode_polygon')),
                index_col='zip_code')
        for idx, val in df_pstc.iterrows():
            try:
                # If the postcode is not number the integer conversion will
                # raise a ValueError. Some postcode look like this '123XX'.
                # It would be possible to add the mayor regions to the postcode
                # map in order to search for the first two/three digits.
                postcode = int(val.postcode)
                if postcode in pstc.index:
                    df.loc[df.id == val.id, 'lon'] = wkt_loads(
                        pstc.loc[postcode].values[0]).centroid.x
                    df.loc[df.id == val.id, 'lat'] = wkt_loads(
                        pstc.loc[postcode].values[0]).centroid.y
                # Replace the last number with a zero and try again.
                elif round(postcode / 10) * 10 in pstc.index:
                    postcode = round(postcode / 10) * 10
                    df.loc[df.id == val.id, 'lon'] = wkt_loads(
                        pstc.loc[postcode].values[0]).centroid.x
                    df.loc[df.id == val.id, 'lat'] = wkt_loads(
                        pstc.loc[postcode].values[0]).centroid.y
                else:
                    logging.debug("Cannot find postcode {0}.".format(postcode))
            except ValueError:
                logging.debug("Cannot find postcode {0}.".format(val.postcode))
    return df


def guess_coordinates_by_spatial_names_opsd(df, fs_column, cap_col,
                                            total_cap, stat):
    # *** Use municipal_code and federal_state to define coordinates ***
    if fs_column in df:
        if 'municipality_code' in df:
            if df.municipality_code.dtype == str:
                df.loc[df.municipality_code == 'AWZ', fs_column] = 'AWZ_NS'
        if 'postcode' in df:
            df.loc[df.postcode == '000XX', fs_column] = 'AWZ'
        states = df.loc[df.lon.isnull()].groupby(
            fs_column).sum()[cap_col]
        logging.debug("Fraction of undefined capacity by federal state " +
                      "(percentage):")
        for (state, capacity) in states.iteritems():
            logging.debug("{0}: {1:.4f}".format(
                state, capacity / total_cap * 100))
            stat.loc[state, 'undefined_capacity'] = capacity

        # A simple table with the centroid of each federal state.
        f2c = pd.read_csv(
            os.path.join(cfg.get('paths', 'geometry'),
                         cfg.get('geometry', 'federalstates_centroid')),
            index_col='name')

        # Use the centroid of each federal state if the federal state is given.
        # This is not very precise and should not be used for a high fraction
        # of plants.
        f2c = f2c.applymap(wkt_loads).centroid
        for l in df.loc[(df.lon.isnull() & df[fs_column].notnull())].index:
            if df.loc[l, fs_column] in f2c.index:
                df.loc[l, 'lon'] = f2c[df.loc[l, fs_column]].x
                df.loc[l, 'lat'] = f2c[df.loc[l, fs_column]].y
    return df


def log_undefined_capacity(df, cap_col, total_cap, msg):
    logging.debug(msg)
    if len(df.loc[df.lon.isnull()]) == 0:
        undefined_cap = 0
    else:
        undefined_cap = df.loc[df.lon.isnull()][cap_col].sum()
    logging.info("{0} percent of capacity is undefined.".format(
        undefined_cap / total_cap * 100))
    return undefined_cap


def complete_opsd_geometries(df, cap_col, category, time=None,
                             fs_column='federal_state'):
    """
    Try different methods to fill missing coordinates.
    """

    if 'id' not in df:
        df['id'] = df.index
        no_id = True
    else:
        no_id = False

    if time is None:
        time = datetime.datetime.now()

    # Get index of incomplete rows.
    incomplete = df.lon.isnull()

    statistics = pd.DataFrame()

    # Calculate total capacity
    total_capacity = df[cap_col].sum()
    statistics.loc['original', 'undefined_capacity'] = log_undefined_capacity(
        df, cap_col, total_capacity,
        "IDs without coordinates found. Trying to fill the gaps.")

    df = convert_utm_code_opsd(df)
    statistics.loc['utm', 'undefined_capacity'] = log_undefined_capacity(
        df, cap_col, total_capacity,
        "Reduced undefined plants by utm conversion.")

    df = guess_coordinates_by_postcode_opsd(df)
    statistics.loc['postcode', 'undefined_capacity'] = log_undefined_capacity(
        df, cap_col, total_capacity, "Reduced undefined plants by postcode.")

    df = guess_coordinates_by_spatial_names_opsd(
        df, fs_column, cap_col, total_capacity, statistics)
    statistics.loc['name', 'undefined_capacity'] = log_undefined_capacity(
        df, cap_col, total_capacity,
        "Reduced undefined plants by federal_state centroid.")

    # Store table of undefined sets to csv-file
    if incomplete.any():
        df.loc[incomplete].to_csv(os.path.join(
            cfg.get('paths', 'messages'),
            '{0}_incomplete_geometries_before.csv'.format(category)))

    incomplete = df.lon.isnull()
    if incomplete.any():
        df.loc[incomplete].to_csv(os.path.join(
            cfg.get('paths', 'messages'),
            '{0}_incomplete_geometries_after.csv'.format(category)))
    logging.debug("Gaps stored to: {0}".format(cfg.get('paths', 'messages')))

    statistics['total_capacity'] = total_capacity
    statistics.to_csv(os.path.join(cfg.get('paths', 'messages'),
                                   'statistics_{0}_pp.csv'.format(category)))

    # Log information
    geo_check = not df.lon.isnull().any()
    if not geo_check:
        logging.warning("Plants with unknown geometry.")
    logging.info('Geometry check: {0}'.format(str(geo_check)))
    logging.info("Geometry supplemented: {0}".format(
        str(datetime.datetime.now() - time)))

    if no_id:
        del df['id']
    return df


def remove_cols(df, cols):
    """Safely remove columns from dict."""
    for key in cols:
        try:
            del df[key]
        except KeyError:
            pass
    return df


def load_original_opsd_file(category, overwrite):
    """Read file if exists."""

    orig_csv_file = os.path.join(
        cfg.get('paths', category),
        cfg.get('powerplants', 'original_file_pattern').format(cat=category))

    # Download non existing files. If you think that there are newer files you
    # have to set overwrite=True to overwrite existing with downloaded files.
    if not os.path.isfile(orig_csv_file) or overwrite:
        logging.warning("File not found. Try to download it from server.")
        logging.warning("Check URL if download does not work.")
        req = requests.get(cfg.get('url', '{0}_data'.format(category)))
        with open(orig_csv_file, 'wb') as fout:
            fout.write(req.content)
        logging.warning("Downloaded from {0} and copied to '{1}'.".format(
            cfg.get('url', '{0}_data'.format(category)), orig_csv_file))
        req = requests.get(cfg.get('url', '{0}_readme'.format(category)))
        with open(
                os.path.join(
                    cfg.get('paths', category),
                    cfg.get('powerplants', 'readme_file_pattern').format(
                        cat=category)), 'wb') as fout:
            fout.write(req.content)
        req = requests.get(cfg.get('url', '{0}_json'.format(category)))
        with open(os.path.join(
                cfg.get('paths', category),
                cfg.get('powerplants', 'json_file_pattern').format(
                    cat=category)), 'wb') as fout:
            fout.write(req.content)

    if category == 'renewable':
        df = pd.read_csv(orig_csv_file)
    elif category == 'conventional':
        df = pd.read_csv(orig_csv_file, index_col=[0])
    else:
        logging.error("Unknown category! Allowed: 'conventional, 'renewable'")
        df = None
    return df


def prepare_dates(df, date_cols, month):
    # Commission year from float or string
    if df[date_cols[0]].dtype == np.float64:
        df['com_year'] = df[date_cols[0]].fillna(0).astype(np.int64)
    else:
        df['com_year'] = pd.to_datetime(df[date_cols[0]].fillna(
            '1800-01-01')).dt.year

    # Decommission year from float or string
    if df[date_cols[1]].dtype == np.float64:
        df['decom_year'] = df[date_cols[1]].fillna(2050).astype(np.int64)
    else:
        df['decom_year'] = pd.to_datetime(df[date_cols[1]].fillna(
            '2050-12-31')).dt.year

    if month:
        df['com_month'] = pd.to_datetime(df[date_cols[0]].fillna(
            '1800-01-01')).dt.month
        df['decom_month'] = pd.to_datetime(df[date_cols[1]].fillna(
            '2050-12-31')).dt.month


def prepare_opsd_file(category, prepared_file_name, overwrite):
    # Load original opsd file
    df = load_original_opsd_file(category, overwrite)

    # Load original file and set differences between conventional and
    # renewable power plants.
    if category == 'renewable':
        capacity_column = 'electrical_capacity'
        remove_list = [
                'tso', 'dso', 'dso_id', 'eeg_id', 'bnetza_id', 'federal_state',
                'postcode', 'municipality_code', 'municipality', 'address',
                'address_number', 'utm_zone', 'utm_east', 'utm_north',
                'data_source']
        date_cols = ('commissioning_date', 'decommissioning_date')
        month = True

    elif category == 'conventional':
        capacity_column = 'capacity_net_bnetza'
        remove_list = None
        date_cols = ('commissioned', 'shutdown')
        month = False
    else:
        logging.error("Unknown category!")
        return None
        # This function is adapted to the OPSD data set structure and might not
        # work with other data sets. Set opsd=False to skip it.

    if len(df.loc[df.lon.isnull()]) > 0:
        df = complete_opsd_geometries(
            df, capacity_column, category, fs_column='state')
    else:
        logging.info("Skipped 'complete_opsd_geometries' function.")

        # Remove power plants with no capacity:
    if capacity_column is not None:
        number = len(df[df[capacity_column].isnull()])
        df = df[df[capacity_column].notnull()]
        if number > 0:
            msg = "{0} power plants were removed, because the capacity was 0."
            logging.warning(msg.format(number))

        # To save disc and RAM capacity unused column are removed.
    if remove_list is not None:
        df = remove_cols(df, remove_list)

    # Remove all power plants with other than a 'DE' country code.
    if 'country_codes' in df:
        country_codes = list(df.country_code.unique())
        country_codes.remove('DE')
        for c_code in country_codes:
            df.loc[df.country_code == c_code, 'region'] = c_code

    prepare_dates(df, date_cols, month)

    df.to_csv(prepared_file_name)
    return df


def load_opsd_file(category, overwrite, prepared=True):
    if prepared:
        prepared_file_name = os.path.join(
            cfg.get('paths', category),
            cfg.get('powerplants', 'prepared_csv_file_pattern').format(
                cat=category))
        if not os.path.isfile(prepared_file_name) or overwrite:
            df = prepare_opsd_file(category, prepared_file_name, overwrite)
        else:
            df = pd.read_csv(prepared_file_name)
    else:
        df = load_original_opsd_file(category, overwrite)
    return df


def create_patch_offshore_wind():
    offsh = pd.read_csv(
        os.path.join(cfg.get('paths', 'static'),
                     cfg.get('static_sources', 'patch_offshore_wind')),
        header=[0, 1], index_col=[0])

    # Convert commissioning to datetime column
    offsh['Wikipedia', 'commissioning'] = pd.to_datetime(
        offsh['Wikipedia', 'commissioning'])

    # Create GeoDataFrame
    offsh.columns = offsh.columns.droplevel()

    offsh['capacity'] = pd.to_numeric(offsh['capacity'])
    offsh['commissioning (planned)'] = offsh['commissioning (planned)'].apply(
        str)

    goffsh = geo.Geometry(name="Offshore wind patch", df=offsh)
    goffsh.create_geo_df()

    # Add column with region names of the model_region
    model_region = geo.Geometry('model region')
    model_region.load(cfg.get('paths', 'geometry'),
                      cfg.get('geometry', 'region_polygon'))
    goffsh.gdf = geo.spatial_join_with_buffer(goffsh, model_region)

    # Add column with coastdat id
    coastdat = geo.Geometry('coastdat2')
    coastdat.load(cfg.get('paths', 'geometry'),
                  cfg.get('geometry', 'coastdatgrid_polygon'))
    goffsh.gdf = geo.spatial_join_with_buffer(goffsh, coastdat)

    # Get year from commissioning date
    goffsh.gdf = goffsh.gdf.loc[goffsh.gdf.commissioning.notnull()]
    goffsh.gdf['year'] = goffsh.gdf.commissioning.map(lambda x: int(x.year))

    # Create DataFrame for grouping
    my_idx = pd.MultiIndex(levels=[[], [], []], labels=[[], [], []],
                           names=['year', 'region', 'coastdat'])
    df = pd.DataFrame(index=my_idx, columns=['capacity'])

    repp = goffsh.gdf.groupby(
        ['model_region', 'coastdat2', 'commissioning']).sum()['capacity [MW]']

    # group power plants
    for r in goffsh.gdf.model_region.unique():
        logging.info('{0}'.format(r))
        coastdat_ids = repp.loc[r].index.get_level_values(
                    0).unique()
        for ci in coastdat_ids:
            logging.debug('{0}: {1}'.format(r, ci))
            sub = repp.loc[(r, ci)]
            for y in range(1998, 2018):
                start = sub[
                    (sub.index.get_level_values(0) < pd.datetime(y, 1, 1))
                    ].sum()
                next_y = sub[
                    (sub.index.get_level_values(0) < pd.datetime(y + 1, 1,
                                                                 1))
                    ].sum()
                if next_y == start:
                    df.loc[(y, r, ci)] = next_y
                else:
                    cap = start
                    for m in range(11):
                        cap += (sub[
                                    (sub.index.get_level_values(0) <
                                     pd.datetime(y, m + 2, 1))].sum() - cap) * (
                                   (11 - m) / 12)
                    df.loc[(y, r, ci)] = cap

    # Write file
    filepath_pattern = os.path.join(cfg.get('paths', 'renewable'),
                                    cfg.get('', ''))
    df = df.sort_index()
    filepath = filepath_pattern.format(cat='patch_offshore')
    df.to_csv(filepath)


def patch_offshore_wind():
    """
    A patch file is used to replace the wind capacity of the regions DE19-DE21
    in the grouped-file.

    The old file will be stored with '.old'. The grouped-file will be replaced.

    """
    filepath_pattern = os.path.join(cfg.get('paths', 'renewable'),
                                    cfg.get('', 'pattern_grouped'))
    repp = pd.read_csv(filepath_pattern.format(cat='renewable'),
                       index_col=[0, 1, 2, 3])
    # repp.to_csv(filepath_pattern.format(cat='renewable') + '.old')
    offsh = pd.read_csv(filepath_pattern.format(cat='patch_offshore'),
                        index_col=[0, 1, 2])

    repp = repp.drop('DE21', level='region')
    repp = repp.drop('DE20', level='region')
    repp = repp.drop('DE19', level='region')

    for y in range(1990, 2018):
        try:
            regions = offsh.loc[y].index.get_level_values(0).unique()
        except KeyError:
            regions = []
        for r in regions:
            coastdat_ids = offsh.loc[y, r].index.get_level_values(0).unique()
            for cid in coastdat_ids:
                if offsh.loc[(y, r, cid), 'capacity'] > 0:
                    print(y, r, cid)
                    repp.loc[('Wind', y, r, cid), 'capacity'] = (
                        offsh.loc[(y, r, cid), 'capacity'])
    repp.sort_index(inplace=True)
    repp.to_csv(filepath_pattern.format(cat='renewable'))


if __name__ == "__main__":
    logger.define_logging()
    create_patch_offshore_wind()
