# -*- coding: utf-8 -*-

""" This module is designed for the use with the coastdat2 weather data set
of the Helmholtz-Zentrum Geesthacht.

A description of the coastdat2 data set can be found here:
https://www.earth-syst-sci-data.net/6/147/2014/

Copyright (c) 2016-2018 Uwe Krien <uwe.krien@rl-institut.de>

SPDX-License-Identifier: GPL-3.0-or-later
"""
__copyright__ = "Uwe Krien <uwe.krien@rl-institut.de>"
__license__ = "GPLv3"

# Python libraries
import os
import datetime
import logging
import requests
import shutil
import configparser
import calendar

# External libraries
import pandas as pd
import pvlib
import shapely.wkt as wkt

# oemof libraries
from oemof.tools import logger

# Internal modules
import reegis_tools.tools as tools
import reegis_tools.feedin as feedin
import reegis_tools.config as cfg

# Optional: database tool.
try:
    import oemof.db.coastdat as coastdat
    import oemof.db as db
    from sqlalchemy import exc
except ImportError:
    coastdat = None
    db = None
    exc = None


def get_coastdat_data(year, filename):
    try:
        ini_key = 'coastdat{0}'.format(year)
        url = cfg.get('weather', ini_key)
        # tools.download_file(filename, url, overwrite=False)
    except configparser.NoOptionError:
        logging.error("No url found to download coastdat2 data for {0}".format(
            year))
        url = None

    if url is not None:
        response = requests.get(url, stream=True)
        if response.status_code == 200:
            logging.info("Downloading the coastdat2 file of {0}...".format(
                year))
            with open(filename, 'wb') as f:
                shutil.copyfileobj(response.raw, f)


def adapt_coastdat_weather_to_pvlib(w, loc):
    """

    Parameters
    ----------
    w : pandas.DataFrame
        Coastdat2 weather data set.
    loc : pvlib.location.Location
        The coordinates of the weather data point.

    Returns
    -------
    pandas.DataFrame : Adapted weather data set.
    """
    w['temp_air'] = w.temp_air - 273.15
    w['ghi'] = w.dirhi + w.dhi
    clearskydni = loc.get_clearsky(w.index).dni
    w['dni'] = pvlib.irradiance.dni(
        w['ghi'], w['dhi'], pvlib.solarposition.get_solarposition(
            w.index, loc.latitude, loc.longitude).zenith,
        clearsky_dni=clearskydni, clearsky_tolerance=1.1)
    return w


def normalised_feedin_for_each_data_set(year, wind=True, solar=True,
                                        overwrite=False):
    """
    Loop over all weather data sets (regions) and calculate a normalised time
    series for each data set with the given parameters of the power plants.

    This file could be more elegant and shorter but it will be rewritten soon
    with the new feedinlib features.

    year : int
        The year of the weather data set to use.
    wind : boolean
        Set to True if you want to create wind feed-in time series.
    solar : boolean
        Set to True if you want to create solar feed-in time series.

    Returns
    -------

    """
    # Get coordinates of the coastdat data points.
    data_points = pd.read_csv(
        os.path.join(cfg.get('paths', 'geometry'),
                     cfg.get('weather', 'grid_centroid')),
        index_col='gid')

    # Open coastdat-weather data hdf5 file for the given year or try to
    # download it if the file is not found.
    weather_file_name = os.path.join(
        cfg.get('paths', 'weather'),
        cfg.get('weather', 'file_pattern').format(year=year))
    if not os.path.isfile(weather_file_name):
        get_coastdat_data(year, weather_file_name)

    weather = pd.HDFStore(weather_file_name, mode='r')

    # Fetch coastdat data heights from ini file.
    data_height = cfg.get_dict('coastdat_data_height')

    # Create basic file and path pattern for the resulting files
    coastdat_path = os.path.join(cfg.get('paths_pattern', 'coastdat'))
    feedin_file = os.path.join(coastdat_path,
                               cfg.get('feedin', 'file_pattern'))

    # Fetch coastdat region-keys from weather file.
    key_file = os.path.join(coastdat_path, 'coastdat_keys.csv')
    if not os.path.isfile(key_file):
        coastdat_keys = weather.keys()
        pd.Series(coastdat_keys).to_csv(key_file)
    else:
        coastdat_keys = pd.read_csv(key_file, index_col=[0],
                                    squeeze=True, header=None)

    txt_create = "Creating normalised {0} feedin time series for {1}."
    hdf = {'wind': {}, 'solar': {}}
    if solar:
        logging.info(txt_create.format('solar', year))
        # Add directory if not present
        os.makedirs(coastdat_path.format(year=year, type='solar'),
                    exist_ok=True)
        # Create the pv-sets defined in the solar.ini
        pv_sets = feedin.create_pvlib_sets()

        # Open a file for each main set (subsets are stored in columns)
        for pv_key, pv_set in pv_sets.items():
            filename = feedin_file.format(
                type='solar', year=year, set_name=pv_key)
            if not os.path.isfile(filename) or overwrite:
                hdf['solar'][pv_key] = pd.HDFStore(filename, mode='w')
    else:
        pv_sets = {}

    if wind:
        logging.info(txt_create.format('wind', year))
        # Add directory if not present
        os.makedirs(coastdat_path.format(year=year, type='wind'),
                    exist_ok=True)
        # Create the pv-sets defined in the wind.ini
        wind_sets = feedin.create_windpowerlib_sets()
        # Open a file for each main set (subsets are stored in columns)
        for wind_key, wind_set in wind_sets.items():
            filename = feedin_file.format(
                type='wind', year=year, set_name=wind_key)
            if not os.path.isfile(filename) or overwrite:
                hdf['wind'][wind_key] = pd.HDFStore(filename, mode='w')
    else:
        wind_sets = {}

    # Define basic variables for time logging
    remain = len(coastdat_keys)
    done = 0
    start = datetime.datetime.now()

    # Loop over all regions
    for coastdat_key in coastdat_keys:
        # Get weather data set for one location
        local_weather = weather[coastdat_key]

        # Adapt the coastdat weather format to the needs of pvlib.
        # The expression "len(list(hdf['solar'].keys()))" returns the number
        # of open hdf5 files. If no file is open, there is nothing to do.
        if solar and len(list(hdf['solar'].keys())) > 0:
            # Get coordinates for the weather location
            local_point = data_points.loc[int(coastdat_key[2:])]

            # Create a pvlib Location object
            location = pvlib.location.Location(
                latitude=local_point['st_y'], longitude=local_point['st_x'])

            # Adapt weather data to the needs of the pvlib
            local_weather_pv = adapt_coastdat_weather_to_pvlib(
                local_weather, location)

            # Create one DataFrame for each pv-set and store into the file
            for pv_key, pv_set in pv_sets.items():
                if pv_key in hdf['solar']:
                    hdf['solar'][pv_key][coastdat_key] = feedin.feedin_pv_sets(
                        local_weather_pv, location, pv_set)

        # Create one DataFrame for each wind-set and store into the file
        for wind_key, wind_set in wind_sets.items():
            if wind_key in hdf['wind']:
                hdf['wind'][wind_key][coastdat_key] = (
                    feedin.feedin_wind_sets(
                        local_weather, data_height, wind_set))

        # Start- time logging *******
        remain -= 1
        done += 1
        if divmod(remain, 10)[1] == 0:
            elapsed_time = (datetime.datetime.now() - start).seconds
            remain_time = elapsed_time / done * remain
            end_time = datetime.datetime.now() + datetime.timedelta(
                seconds=remain_time)
            msg = "Actual time: {:%H:%M}, estimated end time: {:%H:%M}, "
            msg += "done: {0}, remain: {1}".format(done, remain)
            logging.info(msg.format(datetime.datetime.now(), end_time))
        # End - time logging ********

    for k1 in hdf.keys():
        for k2 in hdf[k1].keys():
            hdf[k1][k2].close()
    weather.close()
    logging.info("All feedin time series for {0} are stored in {1}".format(
        year, feedin_path))


def get_average_wind_speed(weather_path, grid_geometry_file, geometry_path,
                           in_file_pattern, out_file, overwrite=False):
    """
    Get average wind speed over all years for each weather region. This can be
    used to select the appropriate wind turbine for each region
    (strong/low wind turbines).
    
    Parameters
    ----------
    overwrite : boolean
        Will overwrite existing files if set to 'True'.
    weather_path : str
        Path to folder that contains all needed files.
    geometry_path : str
        Path to folder that contains geometry files.   
    grid_geometry_file : str
        Name of the geometry file of the weather data grid.
    in_file_pattern : str
        Name of the hdf5 weather files with one wildcard for the year e.g.
        weather_data_{0}.h5
    out_file : str
        Name of the results file (csv)

    """
    if not os.path.isfile(os.path.join(weather_path, out_file)) or overwrite:
        logging.info("Calculating the average wind speed...")

        # Finding existing weather files.
        filelist = (os.listdir(weather_path))
        years = list()
        for year in range(1970, 2020):
                if in_file_pattern.format(year=year) in filelist:
                    years.append(year)

        # Loading coastdat-grid as shapely geometries.
        polygons_wkt = pd.read_csv(os.path.join(geometry_path,
                                                grid_geometry_file))
        polygons = pd.DataFrame(tools.postgis2shapely(polygons_wkt.geom),
                                index=polygons_wkt.gid, columns=['geom'])

        # Opening all weather files
        store = dict()

        # open hdf files
        for year in years:
            store[year] = pd.HDFStore(os.path.join(
                weather_path, in_file_pattern.format(year=year)), mode='r')
        logging.info("Files loaded.")

        keys = store[years[0]].keys()
        logging.info("Keys loaded.")

        n = len(list(keys))
        logging.info("Remaining: {0}".format(n))
        for key in keys:
            wind_speed_avg = pd.Series()
            n -= 1
            if n % 100 == 0:
                logging.info("Remaining: {0}".format(n))
            weather_id = int(key[2:])
            for year in years:
                # Remove entries if year has to many entries.
                if calendar.isleap(year):
                    h_max = 8784
                else:
                    h_max = 8760
                ws = store[year][key]['v_wind']
                surplus = h_max - len(ws)
                if surplus < 0:
                    ws = ws.ix[:surplus]

                # add wind speed time series
                wind_speed_avg = wind_speed_avg.append(
                    ws, verify_integrity=True)

            # calculate the average wind speed for one grid item
            polygons.loc[weather_id, 'v_wind_avg'] = wind_speed_avg.mean()

        # Close hdf files
        for year in years:
            store[year].close()

        # write results to csv file
        polygons.to_csv(os.path.join(weather_path, out_file))
    else:
        logging.info("Skipped: Calculating the average wind speed.")


def calculate_average_parameter_by_region(year, filename, outpath,
                                          outfile=None, parameter='temp_air'):
    """
    Calculate the average temperature for all regions (de21, states...).

    Parameters
    ----------
    year : int
        Select the year you want to calculate the average temperature for.
    filename : str
        Name of a csv file with two columns. One column with the weather id
        (id) and one with the region id (region).
    outpath : str
        Place to store the outputfile.
    outfile : str
        Set your own name for the outputfile.
    parameter : str
        Name of the item (temperature, wind speed,... of the weather data set.

    Returns
    -------
    str : Full file name of the created file.

    """
    weatherfile = os.path.join(
        cfg.get('paths', 'weather'),
        cfg.get('weather', 'file_pattern').format(year=year))
    groups = pd.read_csv(filename, index_col=[0, 1, 2])
    groups = groups.swaplevel(0, 2).sort_index()
    weather = pd.HDFStore(weatherfile, mode='r')

    avg_value = pd.DataFrame()
    for region in groups.index.get_level_values(0).unique():
        w_id_list = groups.loc[region].index.get_level_values(0).unique()
        number_of_sets = len(w_id_list)
        tmp = pd.DataFrame(index=weather['A' + str(w_id_list[0])].index)
        for cid in groups.loc[region].index.get_level_values(0).unique():
            try:
                cid = int(cid)
            except ValueError:
                pass
            if isinstance(cid, int):
                key = 'A' + str(cid)
            else:
                key = cid
            tmp[cid] = weather[key][parameter]
        avg_value[region] = tmp.sum(1).div(number_of_sets)
    weather.close()

    regions = sorted(groups.index.get_level_values(0).unique())
    if outfile is None:
        out_name = '{0}_{1}'.format(regions[0], regions[-1])
        outfile = os.path.join(
            outpath,
            'average_{parameter}_{type}_{year}.csv'.format(
                year=year, type=out_name, parameter=parameter))

    avg_value.to_csv(outfile)
    logging.info("Average temperature saved to {0}".format(outfile))
    return outfile


def fetch_coastdat2_year_from_db(years=None, overwrite=False):
    """Fetch coastDat2 weather data sets from db and store it to hdf5 files.
    This files relies on the RLI-database structure and a valid access to the
    internal database of the Reiner Lemoine Institut. Contact the author for
    more information or use the hdf5 files of the reegis weather repository:
    https://github.com/...

    uwe.krien@rl-institut.de

    Parameters
    ----------
    overwrite : boolean
        Skip existing files if set to False.
    years : list of integer
        Years to fetch.
    """
    weather = os.path.join(cfg.get('paths', 'weather'),
                           cfg.get('weather', 'file_pattern'))
    geometry = os.path.join(cfg.get('paths', 'geometry'),
                            cfg.get('geometry', 'germany_polygon'))

    polygon = wkt.loads(
        pd.read_csv(geometry, index_col='gid', squeeze=True)[0])

    if years is None:
        years = range(1980, 2020)

    try:
        conn = db.connection()
    except exc.OperationalError:
        conn = None
    for year in years:
        if not os.path.isfile(weather.format(year=str(year))) or overwrite:
            logging.info("Fetching weather data for {0}.".format(year))

            try:
                weather_sets = coastdat.get_weather(conn, polygon, year)
            except AttributeError:
                logging.warning("No database connection found.")
                weather_sets = list()
            if len(weather_sets) > 0:
                logging.info("Success. Store weather data to {0}.".format(
                    weather.format(year=str(year))))
                store = pd.HDFStore(weather.format(year=str(year)), mode='w')
                for weather_set in weather_sets:
                    logging.debug(weather_set.name)
                    store['A' + str(weather_set.name)] = weather_set.data
                store.close()
            else:
                logging.warning("No weather data found for {0}.".format(year))
        else:
            logging.info("Weather data for {0} exists. Skipping.".format(year))


def coastdat_id2coord():
    """
    Creating a file with the latitude and longitude for all coastdat2 data
    sets.
    """
    conn = db.connection()
    sql = "select gid, st_x(geom), st_y(geom) from coastdat.spatial;"
    results = (conn.execute(sql))
    columns = results.keys()
    data = pd.DataFrame(results.fetchall(), columns=columns)
    data.set_index('gid', inplace=True)
    data.to_csv(os.path.join('data', 'basic', 'id2latlon.csv'))


if __name__ == "__main__":
    logger.define_logging()
    for y in [2014, 2013, 2012]:
        normalised_feedin_for_each_data_set(y, wind=True, solar=True)
