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


def complete_opsd_geometries(df, category, time=None,
                             fs_column='federal_state'):
    """
    Try different methods to fill missing coordinates.
    """
    cap_col = 'capacity'

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
        cfg.get('paths', 'opsd'),
        cfg.get('opsd', 'original_file_pattern').format(cat=category))

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
                    cfg.get('paths', 'opsd'),
                    cfg.get('opsd', 'readme_file_pattern').format(
                        cat=category)), 'wb') as fout:
            fout.write(req.content)
        req = requests.get(cfg.get('url', '{0}_json'.format(category)))
        with open(os.path.join(
                cfg.get('paths', 'opsd'),
                cfg.get('opsd', 'json_file_pattern').format(
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
        df['com_year'] = df[date_cols[0]].fillna(1800).astype(np.int64)
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
    else:
        df['com_month'] = 6
        df['decom_month'] = 6


def prepare_opsd_file(category, prepared_file_name, overwrite):
    # Load original opsd file
    df = load_original_opsd_file(category, overwrite)

    # Load original file and set differences between conventional and
    # renewable power plants.
    if category == 'renewable':
        # capacity_column = 'electrical_capacity'
        remove_list = [
                'tso', 'dso', 'dso_id', 'eeg_id', 'bnetza_id', 'federal_state',
                'postcode', 'municipality_code', 'municipality', 'address',
                'address_number', 'utm_zone', 'utm_east', 'utm_north',
                'data_source']
        date_cols = ('commissioning_date', 'decommissioning_date')
        month = True

    elif category == 'conventional':
        # capacity_column = 'capacity_net_bnetza'
        remove_list = None
        date_cols = ('commissioned', 'shutdown')
        month = False
    else:
        logging.error("Unknown category!")
        return None
        # This function is adapted to the OPSD data set structure and might not
        # work with other data sets. Set opsd=False to skip it.

    df = df.rename(columns={'electrical_capacity': 'capacity',
                            'capacity_net_bnetza': 'capacity',
                            'efficiency_estimate': 'efficiency'})

    if len(df.loc[df.lon.isnull()]) > 0:
        df = complete_opsd_geometries(df, category, fs_column='state')
    else:
        logging.info("Skipped 'complete_opsd_geometries' function.")

        # Remove power plants with no capacity:
    number = len(df[df['capacity'].isnull()])
    df = df[df['capacity'].notnull()]
    if number > 0:
        msg = "{0} power plants have been removed, because the capacity was 0."
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
            cfg.get('paths', 'opsd'),
            cfg.get('opsd', 'cleaned_csv_file_pattern').format(
                cat=category))
        if not os.path.isfile(prepared_file_name) or overwrite:
            df = prepare_opsd_file(category, prepared_file_name, overwrite)
        else:
            df = pd.read_csv(prepared_file_name, index_col=[0])
    else:
        df = load_original_opsd_file(category, overwrite)
    return df


def opsd_power_plants(overwrite=False, csv=False):
    """

    Parameters
    ----------
    csv
    overwrite

    Returns
    -------

    """
    strcols = {
        'conventional': [
            'name_bnetza', 'block_bnetza', 'name_uba', 'company', 'street',
            'postcode', 'city', 'state', 'country_code', 'fuel', 'technology',
            'chp', 'commissioned_original', 'status', 'type', 'eic_code_plant',
            'eic_code_block', 'efficiency_source', 'energy_source_level_1',
            'energy_source_level_2', 'energy_source_level_3', 'eeg',
            'network_node', 'voltage', 'network_operator', 'merge_comment',
            'geometry', 'federal_states'],
        'renewable': [
            'commissioning_date', 'decommissioning_date',
            'energy_source_level_1', 'energy_source_level_2',
            'energy_source_level_3', 'technology', 'voltage_level', 'comment',
            'geometry', 'federal_states']}

    if csv:
        opsd_file_name = os.path.join(
            cfg.get('paths', 'opsd'),
            cfg.get('opsd', 'opsd_prepared_csv_pattern'))
        hdf = None
    else:
        opsd_file_name = os.path.join(
            cfg.get('paths', 'opsd'), cfg.get('opsd', 'opsd_prepared'))
        if os.path.isfile(opsd_file_name) and not overwrite:
            hdf = None
        else:
            if os.path.isfile(opsd_file_name):
                os.remove(opsd_file_name)
            hdf = pd.HDFStore(opsd_file_name, mode='a')

    # If the power plant file does not exist, download and prepare it.
    for category in ['conventional', 'renewable']:
        # Define file and path pattern for power plant file.
        cleaned_file_name = os.path.join(
            cfg.get('paths', 'opsd'),
            cfg.get('opsd', 'cleaned_csv_file_pattern').format(
                cat=category))
        if csv:
            exist = os.path.isfile(opsd_file_name) and not overwrite
        else:
            exist = hdf is None

        if not exist:
            logging.info("Preparing {0} opsd power plants".format(category))
            df = load_opsd_file(category, overwrite, prepared=True)
            pp = geo.Geometry('{0} power plants'.format(category), df=df)
            pp = spatial_preparation_power_plants(pp)
            if csv:
                pp.df.to_csv(opsd_file_name)
            else:
                pp.df[strcols[category]] = pp.df[strcols[category]].astype(str)
                hdf[category] = pp.df
            logging.info("Opsd power plants stored to {0}".format(
                opsd_file_name))

        if os.path.isfile(cleaned_file_name):
            os.remove(cleaned_file_name)
    if hdf is not None:
        hdf.close()
    return opsd_file_name


def spatial_preparation_power_plants(pp):
    """Add spatial names to DataFrame. Three columns will be added to the
    power plant table:

    federal_states: The federal state of Germany
    model_region: The name of the model region defined by the user.
    coastdat: The id of the nearest coastdat weather data set.

    Parameters
    ----------
    pp : reegis_tools.Geometry
        An object containing Germany's power plants.

    Returns
    -------
    reegis_tools.Geometry

    """

    if pp.gdf is None:
        logging.info("Create GeoDataFrame from lat/lon.")
        pp.create_geo_df()

    logging.info("Remove invalid geometries")
    pp.remove_invalid_geometries()

    # Add column with name of the federal state (Bayern, Berlin,...)
    federal_states = geo.Geometry('federal states')
    federal_states.load(cfg.get('paths', 'geometry'),
                        cfg.get('geometry', 'federalstates_polygon'))
    pp.gdf = geo.spatial_join_with_buffer(pp, federal_states)

    # Add column with coastdat id
    coastdat = geo.Geometry('coastdat2')
    coastdat.load(cfg.get('paths', 'geometry'),
                  cfg.get('coastdat', 'coastdatgrid_polygon'))
    pp.gdf = geo.spatial_join_with_buffer(pp, coastdat)

    # Update DataFrame with the new content of the GeoDataFrame.
    pp.gdf2df()
    return pp


if __name__ == "__main__":
    logger.define_logging()
    opsd_power_plants(overwrite=False, csv=False)
