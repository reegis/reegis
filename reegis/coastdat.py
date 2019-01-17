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
import calendar
from collections import namedtuple

# External libraries
if not os.environ.get('READTHEDOCS') == 'True':
    import requests
    import pandas as pd
    import pvlib
    from shapely.geometry import Point

    # oemof libraries
    from oemof.tools import logger

    # Internal modules
    import reegis.tools as tools
    import reegis.feedin as feedin
    import reegis.config as cfg
    import reegis.powerplants as powerplants
    import reegis.geometries as geometries
    import reegis.bmwi


def download_coastdat_data(filename=None, year=None, url=None,
                           test_only=False, overwrite=True):
    """
    Download coastdat data set from internet source.

    Parameters
    ----------
    filename : str
        Full path with the filename, where the downloaded file will be stored.
    year : int or None
        Year of the weather data set. If a url is passed this value will be
        ignored because it is used to create the default url.
    url : str or None
        Own url can be used if the default url does not work an one found an
        alternative valid url.
    test_only : bool
        If True the the url is tested but the file will not be downloaded
        (default: False).
    overwrite : bool
        If True the file will be downloaded even if it already exist.
        (default: True)

    Returns
    -------
    str or None : If the url is valid the filename is returned otherwise None.

    Examples
    --------
    >>> download_coastdat_data(year=2014, test_only=True)
    'coastDat2_de_2014.h5'
    >>> print(download_coastdat_data(url='https://osf.io/url', test_only=True))
    None
    >>> download_coastdat_data(filename='w14.hd5', year=2014)  # doctest: +SKIP

    """
    if url is None:
        url_ids = cfg.get_dict('coastdat_url_id')
        url_id = url_ids.get(str(year), None)
        if url_id is not None:
            url = cfg.get('coastdat', 'basic_url').format(url_id=url_id)

    if url is not None and not test_only:
        response = requests.get(url, stream=True)
        if response.status_code == 200:
            msg = "Downloading the coastdat2 file of {0} from {1} ..."
            logging.info(msg.format(year, url))
            if filename is None:
                headers = response.headers['Content-Disposition']
                filename = headers.split('; ')[1].split('=')[1].replace(
                    '"', '')
            tools.download_file(filename, url, overwrite=overwrite)
            return filename
        else:
            raise ValueError("URL not valid: {0}".format(url))
    elif url is not None and test_only:
        response = requests.get(url, stream=True)
        if response.status_code == 200:
            headers = response.headers['Content-Disposition']
            filename = headers.split('; ')[1].split('=')[1].replace('"', '')
        else:
            filename = None
        return filename
    else:
        raise ValueError("No URL found for {0}".format(year))


def fetch_id_by_coordinates(latitude, longitude):
    """
    Get nearest weather data set to a given location.

    Parameters
    ----------
    latitude : float
    longitude : float

    Returns
    -------
    int : coastdat id

    Examples
    --------
    >>> fetch_id_by_coordinates(53.655119, 11.181475)
    1132101
    """
    coastdat_polygons = geometries.load(
        cfg.get('paths', 'geometry'),
        cfg.get('coastdat', 'coastdatgrid_polygon'))
    location = Point(longitude, latitude)

    cid = coastdat_polygons[coastdat_polygons.contains(location)].index

    if len(cid) == 0:
        msg = "No id found for latitude {0} and longitude {1}."
        logging.warning(msg.format(latitude, longitude))
        return None
    elif len(cid) == 1:
        return cid[0]


def fetch_data_coordinates_by_id(coastdat_id):
    """
    Returns the coordinates of the weather data set.

    Parameters
    ----------
    coastdat_id : int or str
        ID of the coastdat weather data set

    Returns
    -------
    namedtuple : Fields are latitude and longitude

    Examples
    --------
    >>> location = fetch_data_coordinates_by_id(1132101)
    >>> round(location.latitude, 3)
    53.692
    >>> round(location.longitude, 3)
    11.351
    """
    coord = namedtuple('weather_location', 'latitude, longitude')
    coastdat_polygons = geometries.load(
        cfg.get('paths', 'geometry'),
        cfg.get('coastdat', 'coastdatgrid_polygon'))
    c = coastdat_polygons.loc[int(coastdat_id)].geometry.centroid
    return coord(latitude=c.y, longitude=c.x)


def fetch_coastdat_weather(year, coastdat_id):
    """
    Fetch weather one coastdat weather data set.

    Parameters
    ----------
    year : int
        Year of the weather data set
    coastdat_id : numeric
        ID of the coastdat data set.

    Returns
    -------
    pd.DataFrame : Weather data set.

    Examples
    --------
    >>> coastdat_id = fetch_id_by_coordinates(53.655119, 11.181475)
    >>> fetch_coastdat_weather(2014, coastdat_id)['v_wind'].mean().round(2)
    4.39
    """
    weather_file_name = os.path.join(
        cfg.get('paths', 'coastdat'),
        cfg.get('coastdat', 'file_pattern').format(year=year))
    if not os.path.isfile(weather_file_name):
        download_coastdat_data(filename=weather_file_name, year=year)
    key = '/A{0}'.format(int(coastdat_id))
    return pd.DataFrame(pd.read_hdf(weather_file_name, key))


def adapt_coastdat_weather_to_pvlib(weather, loc):
    """
    Adapt the coastdat weather data sets to the needs of the pvlib.

    Parameters
    ----------
    weather : pandas.DataFrame
        Coastdat2 weather data set.
    loc : pvlib.location.Location
        The coordinates of the weather data point.

    Returns
    -------
    pandas.DataFrame : Adapted weather data set.

    Examples
    --------
    >>> cd_id = 1132101
    >>> cd_weather = fetch_coastdat_weather(2014, cd_id)
    >>> c = fetch_data_coordinates_by_id(cd_id)
    >>> location = pvlib.location.Location(**getattr(c, '_asdict')())
    >>> pv_weather = adapt_coastdat_weather_to_pvlib(cd_weather, location)
    >>> 'ghi' in cd_weather.columns
    False
    >>> 'ghi' in pv_weather.columns
    True
    """
    w = pd.DataFrame(weather.copy())
    w['temp_air'] = w.temp_air - 273.15
    w['ghi'] = w.dirhi + w.dhi
    clearskydni = loc.get_clearsky(w.index).dni
    w['dni'] = pvlib.irradiance.dni(
        w['ghi'], w['dhi'], pvlib.solarposition.get_solarposition(
            w.index, loc.latitude, loc.longitude).zenith,
        clearsky_dni=clearskydni, clearsky_tolerance=1.1)
    return w


def adapt_coastdat_weather_to_windpowerlib(weather, data_height):
    """
    Adapt the coastdat weather data sets to the needs of the pvlib.

    Parameters
    ----------
    weather : pandas.DataFrame
        Coastdat2 weather data set.
    data_height : dict
        The data height for each weather data column.

    Returns
    -------
    pandas.DataFrame : Adapted weather data set.

    Examples
    --------
    >>> cd_id = 1132101
    >>> cd_weather = fetch_coastdat_weather(2014, cd_id)
    >>> data_height = cfg.get_dict('coastdat_data_height')
    >>> wind_weather = adapt_coastdat_weather_to_windpowerlib(
    ...     cd_weather, data_height)
    >>> cd_weather.columns.nlevels
    1
    >>> wind_weather.columns.nlevels
    2
    """
    weather = pd.DataFrame(weather.copy())
    cols = {'v_wind': 'wind_speed',
            'z0': 'roughness_length',
            'temp_air': 'temperature'}
    weather.rename(columns=cols, inplace=True)
    dh = [(key, data_height[key]) for key in weather.columns]
    weather.columns = pd.MultiIndex.from_tuples(dh)
    return weather


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
                     cfg.get('coastdat', 'coastdatgrid_centroid')),
        index_col='gid')

    # Open coastdat-weather data hdf5 file for the given year or try to
    # download it if the file is not found.
    weather_file_name = os.path.join(
        cfg.get('paths', 'coastdat'),
        cfg.get('coastdat', 'file_pattern').format(year=year))
    if not os.path.isfile(weather_file_name):
        download_coastdat_data(year=year, filename=weather_file_name)

    weather = pd.HDFStore(weather_file_name, mode='r')

    # Fetch coastdat data heights from ini file.
    data_height = cfg.get_dict('coastdat_data_height')

    # Create basic file and path pattern for the resulting files
    coastdat_path = os.path.join(cfg.get('paths_pattern', 'coastdat'))

    feedin_file = os.path.join(coastdat_path,
                               cfg.get('feedin', 'file_pattern'))

    # Fetch coastdat region-keys from weather file.
    key_file_path = coastdat_path.format(year='', type='')[:-2]
    key_file = os.path.join(key_file_path, 'coastdat_keys.csv')
    if not os.path.isfile(key_file):
        coastdat_keys = weather.keys()
        if not os.path.isdir(key_file_path):
            os.makedirs(key_file_path)
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
                latitude=local_point['lat'], longitude=local_point['lon'])

            # Adapt weather data to the needs of the pvlib
            local_weather_pv = adapt_coastdat_weather_to_pvlib(
                local_weather, location)

            # Create one DataFrame for each pv-set and store into the file
            for pv_key, pv_set in pv_sets.items():
                if pv_key in hdf['solar']:
                    hdf['solar'][pv_key][coastdat_key] = feedin.feedin_pv_sets(
                        local_weather_pv, location, pv_set)

        # Create one DataFrame for each wind-set and store into the file
        if wind and len(list(hdf['wind'].keys())) > 0:
            local_weather_wind = adapt_coastdat_weather_to_windpowerlib(
                local_weather, data_height)
            for wind_key, wind_set in wind_sets.items():
                if wind_key in hdf['wind']:
                    hdf['wind'][wind_key][coastdat_key] = (
                        feedin.feedin_wind_sets(
                            local_weather_wind, wind_set))

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
        year, coastdat_path.format(year=year, type='')))


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


def spatial_average_weather(year, geo, parameter, outpath=None, outfile=None):
    """
    Calculate the average temperature for all regions (de21, states...).

    Parameters
    ----------
    year : int
        Select the year you want to calculate the average temperature for.
    geo : geometries.Geometry object
        Polygons to calculate the average parameter for.
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
    logging.info("Getting average {0} for {1} in {2} from coastdat2.".format(
        parameter, geo.name, year))

    col_name = geo.name.replace(' ', '_')

    # Create a Geometry object for the coastdat centroids.
    coastdat_geo = geometries.Geometry(name='coastdat')
    coastdat_geo.load(cfg.get('paths', 'geometry'),
                      cfg.get('coastdat', 'coastdatgrid_polygon'))
    coastdat_geo.gdf['geometry'] = coastdat_geo.gdf.centroid

    # Join the tables to create a list of coastdat id's for each region.
    coastdat_geo.gdf = geometries.spatial_join_with_buffer(
        coastdat_geo, geo, name='federal_states', limit=0)

    # Fix regions with no matches (no matches if a region ist too small).
    fix = {}
    for reg in set(geo.gdf.index) - set(coastdat_geo.gdf[col_name].unique()):
        reg_point = geo.gdf.representative_point().loc[reg]
        coastdat_poly = geometries.Geometry(name='coastdat_poly')
        coastdat_poly.load(cfg.get('paths', 'geometry'),
                           cfg.get('coastdat', 'coastdatgrid_polygon'))
        fix[reg] = coastdat_poly.gdf.loc[coastdat_poly.gdf.intersects(
            reg_point)].index[0]

    # Open the weather file
    weatherfile = os.path.join(
        cfg.get('paths', 'coastdat'),
        cfg.get('coastdat', 'file_pattern').format(year=year))
    if not os.path.isfile(weatherfile):
        download_coastdat_data(year=year, filename=weatherfile)
    weather = pd.HDFStore(weatherfile, mode='r')

    # Calculate the average temperature for each region with more than one id.
    avg_value = pd.DataFrame()
    for region in geo.gdf.index:
        cd_ids = coastdat_geo.gdf[coastdat_geo.gdf[col_name] == region].index
        number_of_sets = len(cd_ids)
        tmp = pd.DataFrame()
        logging.debug((region, len(cd_ids)))
        for cid in cd_ids:
            try:
                cid = int(cid)
            except ValueError:
                pass
            if isinstance(cid, int):
                key = 'A' + str(cid)
            else:
                key = cid
            tmp[cid] = weather[key][parameter]
        if len(cd_ids) < 1:
            key = 'A' + str(fix[region])
            avg_value[region] = weather[key][parameter]
        else:
            avg_value[region] = tmp.sum(1).div(number_of_sets)
    weather.close()

    # Create the name an write to file
    regions = sorted(geo.gdf.index)
    if outfile is None:
        out_name = '{0}_{1}'.format(regions[0], regions[-1])
        outfile = os.path.join(
            outpath,
            'average_{parameter}_{type}_{year}.csv'.format(
                year=year, type=out_name, parameter=parameter))

    avg_value.to_csv(outfile)
    logging.info("Average temperature saved to {0}".format(outfile))
    return outfile


def federal_state_average_weather(year, parameter):
    federal_states = geometries.Geometry(name='federal_states')
    federal_states.load(cfg.get('paths', 'geometry'),
                        cfg.get('geometry', 'federalstates_polygon'))
    filename = os.path.join(
        cfg.get('paths', 'coastdat'),
        'average_{0}_BB_TH_{1}.csv'.format(parameter, year))
    if not os.path.isfile(filename):
        spatial_average_weather(year, federal_states, parameter,
                                outfile=filename)
    return pd.read_csv(filename, index_col=[0], parse_dates=True)


def aggregate_by_region_coastdat_feedin(pp, regions, year, category, outfile,
                                        weather_year=None):
    cat = category.lower()
    logging.info("Aggregating {0} feed-in for {1}...".format(cat, year))
    if weather_year is None:
        weather_year = year
        weather_year_str = ""
    else:
        logging.info("Weather data taken from {0}.".format(weather_year))
        weather_year_str = " (weather: {0})".format(weather_year)

    # Define the path for the input files.
    coastdat_path = os.path.join(cfg.get('paths_pattern', 'coastdat')).format(
        year=weather_year, type=cat)
    if not os.path.isdir(coastdat_path):
        normalised_feedin_for_each_data_set(weather_year)
    # Prepare the lists for the loops
    set_names = []
    set_name = None
    pwr = dict()
    columns = dict()
    replace_str = 'coastdat_{0}_{1}_'.format(weather_year, category)
    for file in os.listdir(coastdat_path):
        if file[-2:] == 'h5':
            set_name = file[:-3].replace(replace_str, '')
            set_names.append(set_name)
            pwr[set_name] = pd.HDFStore(os.path.join(coastdat_path, file))
            columns[set_name] = pwr[set_name]['/A1129087'].columns

    # Create DataFrame with MultiColumns to take the results
    my_index = pwr[set_name]['/A1129087'].index
    my_cols = pd.MultiIndex(levels=[[], [], []], labels=[[], [], []],
                            names=[u'region', u'set', u'subset'])
    feed_in = pd.DataFrame(index=my_index, columns=my_cols)

    # Loop over all aggregation regions
    # Sum up time series for one region and divide it by the
    # capacity of the region to get a normalised time series.
    for region in regions:
        try:
            coastdat_ids = pp.loc[(category, region)].index
        except KeyError:
            coastdat_ids = []
        number_of_coastdat_ids = len(coastdat_ids)
        logging.info("{0}{3} - {1} ({2})".format(
            year, region, number_of_coastdat_ids, weather_year_str))
        logging.debug("{0}".format(coastdat_ids))

        # Loop over all sets that have been found in the coastdat path
        if number_of_coastdat_ids > 0:
            for name in set_names:
                # Loop over all sub-sets that have been found within each file.
                for col in columns[name]:
                    temp = pd.DataFrame(index=my_index)

                    # Loop over all coastdat ids, that intersect with the
                    # actual region.
                    for coastdat_id in coastdat_ids:
                        # Create a tmp table for each coastdat id.
                        coastdat_key = '/A{0}'.format(int(coastdat_id))
                        pp_inst = float(pp.loc[(category, region, coastdat_id),
                                               'capacity_{0}'.format(year)])
                        temp[coastdat_key] = (
                            pwr[name][coastdat_key][col][:8760].multiply(
                                pp_inst))
                    # Sum up all coastdat columns to one region column
                    colname = '_'.join(col.split('_')[-3:])
                    feed_in[region, name, colname] = (
                        temp.sum(axis=1).divide(float(
                            pp.loc[(category, region), 'capacity_{0}'.format(
                                year)].sum())))

    feed_in.to_csv(outfile)
    for name_of_set in set_names:
        pwr[name_of_set].close()


def aggregate_by_region_hydro(pp, regions, year, outfile_name):
    hydro = reegis.bmwi.bmwi_re_energy_capacity()['water']

    hydro_capacity = (pp.loc['Hydro', 'capacity'].sum())

    full_load_hours = (hydro.loc[year, 'energy'] /
                       hydro_capacity * 1000)

    hydro_path = os.path.abspath(os.path.join(
        *outfile_name.split('/')[:-1]))

    if not os.path.isdir(hydro_path):
        os.makedirs(hydro_path)

    idx = pd.date_range(start="{0}-01-01 00:00".format(year),
                        end="{0}-12-31 23:00".format(year),
                        freq='H', tz='Europe/Berlin')
    feed_in = pd.DataFrame(columns=regions, index=idx)
    feed_in[feed_in.columns] = full_load_hours / len(feed_in)
    feed_in.to_csv(outfile_name)

    # https://shop.dena.de/fileadmin/denashop/media/Downloads_Dateien/esd/
    # 9112_Pumpspeicherstudie.pdf
    # S. 110ff


def aggregate_by_region_geothermal(regions, year, outfile_name):
    full_load_hours = cfg.get('feedin', 'geothermal_full_load_hours')

    hydro_path = os.path.abspath(os.path.join(
        *outfile_name.split('/')[:-1]))

    if not os.path.isdir(hydro_path):
        os.makedirs(hydro_path)

    idx = pd.date_range(start="{0}-01-01 00:00".format(year),
                        end="{0}-12-31 23:00".format(year),
                        freq='H', tz='Europe/Berlin')
    feed_in = pd.DataFrame(columns=regions, index=idx)
    feed_in[feed_in.columns] = full_load_hours / len(feed_in)
    feed_in.to_csv(outfile_name)


def get_grouped_power_plants(year):
    """Filter the capacity of the powerplants for the given year.
    """
    return powerplants.get_pp_by_year(year).groupby(
        ['energy_source_level_2', 'federal_states', 'coastdat2']).sum()


def aggregate_by_region(year, state):
    # Create the path for the output files.
    feedin_state_path = cfg.get('paths_pattern', 'state_feedin').format(
        year=year)
    os.makedirs(feedin_state_path, exist_ok=True)

    # Create pattern for the name of the resulting files.
    feedin_berlin_outfile_name = os.path.join(
        feedin_state_path,
        cfg.get('feedin', 'feedin_state_pattern').format(
            year=year, type='{type}', state=state))

    # Filter the capacity of the powerplants for the given year.
    pp = get_grouped_power_plants(year)

    # Loop over weather depending feed-in categories.
    # WIND and PV

    for cat in ['Wind', 'Solar']:
        outfile_name = feedin_berlin_outfile_name.format(type=cat.lower())
        if not os.path.isfile(outfile_name):
            aggregate_by_region_coastdat_feedin(
                pp, [state], year, cat, outfile_name)

    # HYDRO
    outfile_name = feedin_berlin_outfile_name.format(type='hydro')
    if not os.path.isfile(outfile_name):
        aggregate_by_region_hydro(
            pp, [state], year, outfile_name)

    # GEOTHERMAL
    outfile_name = feedin_berlin_outfile_name.format(type='geothermal')
    if not os.path.isfile(outfile_name):
        aggregate_by_region_geothermal([state], year, outfile_name)


def get_feedin_by_state(year, feedin_type, state):
    """

    Parameters
    ----------
    year
    feedin_type
    state : str
        Official abbreviation of state in Germany e.g. 'BE', 'SH', 'TH'...

    Returns
    -------

    """
    feedin_state_file_name = os.path.join(
        cfg.get('paths_pattern', 'state_feedin'),
        cfg.get('feedin', 'feedin_state_pattern')).format(
            year=year, type=feedin_type, state=state)

    # Add any federal state to get its normalised feed-in.
    if feedin_type in ['solar', 'wind']:
        if not os.path.isfile(feedin_state_file_name):
            aggregate_by_region(year, state)
        return pd.read_csv(feedin_state_file_name, index_col=[0],
                           header=[0, 1, 2])
    elif feedin_type in ['hydro', 'geothermal']:
        if not os.path.isfile(feedin_state_file_name):
            aggregate_by_region(year, state)
        return pd.read_csv(feedin_state_file_name, index_col=[0], header=[0])
    else:
        return None


def scenario_feedin(year, state):
    feed_in = scenario_feedin_pv(year, state)
    feed_in = scenario_feedin_wind(year, feed_in, state)
    feed_in.columns = pd.MultiIndex.from_product([[state], feed_in.columns])
    return feed_in


def scenario_feedin_wind(year, feedin_ts, state):
    logging.critical("ERROR. Fixed turbine type for all regions.")
    wind = get_feedin_by_state(year, 'wind', state)
    for reg in wind.columns.levels[0]:
        feedin_ts['wind'] = wind[
            reg, 'coastdat_{0}_wind_ENERCON_127_hub135_pwr_7500'.format(year),
            'E_126_7500']
    return feedin_ts.sort_index(1)


def scenario_feedin_pv(year, state):
    pv_types = cfg.get_dict('pv_types')
    pv_orientation = cfg.get_dict('pv_orientation')
    pv = get_feedin_by_state(year, 'solar', state)

    # combine different pv-sets to one feedin time series
    feedin_ts = pd.DataFrame(index=pv.index)
    orientation_fraction = pd.Series(pv_orientation)

    pv.sort_index(1, inplace=True)
    orientation_fraction.sort_index(inplace=True)
    base_set_column = 'coastdat_{0}_solar_{1}'.format(year, '{0}')
    for reg in pv.columns.levels[0]:
        feedin_ts['solar'] = 0
        for mset in pv_types.keys():
            set_col = base_set_column.format(mset)
            feedin_ts['solar'] += pv[reg, set_col].multiply(
                orientation_fraction).sum(1).multiply(
                pv_types[mset])
    return feedin_ts.sort_index(1)


def get_time_series_for_one_location(latitude, longitude, year, set_name=None):
    coastdat_id = fetch_id_by_coordinates(latitude, longitude)

    # set_name = 'M_LG290G3__I_ABB_MICRO_025_US208'
    df = pd.DataFrame()
    if set_name is not None:
        hd_file = pd.HDFStore(os.path.join(
            cfg.get('paths', 'feedin'), 'coastdat', str(year), 'solar',
            cfg.get('feedin', 'file_pattern').format(year=year, type='solar',
                                                     set_name=set_name)),
            mode='r')
        df = hd_file['/A{0}'.format(coastdat_id)]
        hd_file.close()
    else:
        path = os.path.join(
            cfg.get('paths', 'feedin'), 'coastdat', str(year), 'solar')
        for file in os.listdir(path):
            hd_file = pd.HDFStore(os.path.join(path, file), mode='r')
            tmp = hd_file['/A{0}'.format(coastdat_id)]
            hd_file.close()
            df = pd.concat([df, tmp], axis=1)

    opt = int(round(feedin.get_optimal_pv_angle(latitude)))
    df.columns = df.columns.str.replace('opt', str(opt))
    return df


def get_all_time_series_for_one_location(latitude, longitude, set_name=None):
    path = os.path.join(cfg.get('paths', 'feedin'), 'coastdat')
    years = os.listdir(path)
    df = pd.DataFrame(columns=pd.MultiIndex(levels=[[], []], labels=[[], []]))
    # years = [2012, 2013, 2014]
    for year in years:
        if os.path.isdir(os.path.join(path, str(year))):
            tmp = get_time_series_for_one_location(
                latitude, longitude, year, set_name).reset_index(drop=True)
            for col in tmp.columns:
                # print(tmp[col].sum())
                df[year, col] = tmp[col]
    return df


if __name__ == "__main__":
    logger.define_logging()
    # import pprint
    # pprint.pprint(feedin.create_windpowerlib_sets())
    # exit(0)
    # my_coastdat_id = fetch_id_by_coordinates(53.655119, 11.181475)
    # print(my_coastdat_id)
    # print(fetch_coastdat_weather(2014, my_coastdat_id)['v_wind'].mean())
    weather_file_name_out = os.path.join(
        cfg.get('paths', 'coastdat'),
        cfg.get('coastdat', 'file_pattern').format(year=2000))
    weather_file_name_in = os.path.join(
        cfg.get('paths', 'coastdat'),
        cfg.get('coastdat', 'file_pattern').format(year='2000_new_'))

    weather_out = pd.HDFStore(weather_file_name_out, mode='r')
    weather_in = pd.HDFStore(weather_file_name_in, mode='w')
    for k in weather_out.keys():
        print(k)
        weather_in[k] = weather_out[k][:-1]
    weather_out.close()
    weather_in.close()
    exit(0)

    # my_df = get_time_series_for_one_location(53.655119, 11.181475, 2012)
    # print(my_df)
    # print()
    # print("One year:")
    # print(my_df.sum())
    # my_df = get_all_time_series_for_one_location(
    #     53.655119, 11.181475, set_name='M_LG290G3__I_ABB_MICRO_025_US208')
    # print()
    # print("One set:")
    # print(my_df.swaplevel(axis=1)['LG290G3_ABB_tlt34_az180_alb02'].sum())
    # print(scenario_feedin(2014, 'BE'))
    for y in [2014]:
        normalised_feedin_for_each_data_set(y, wind=True, solar=True)
    # print(federal_state_average_weather(2012, 'temp_air'))
