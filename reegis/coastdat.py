# -*- coding: utf-8 -*-

"""
This module is EXPERIMENTAL, that means that tests are missing.
The reason is that the coastdat2 dataset is deprecated and will be replaced by
the OpenFred dataset from Helmholtz-Zentrum Geesthacht. It should work though.

This module is designed for the use with the coastdat2 weather data set
of the Helmholtz-Zentrum Geesthacht.

A description of the coastdat2 data set can be found here:

https://www.earth-syst-sci-data.net/6/147/2014/

Copyright (c) 2016-2019 Uwe Krien <krien@uni-bremen.de>

SPDX-License-Identifier: MIT
"""
__copyright__ = "Uwe Krien <krien@uni-bremen.de>"
__license__ = "MIT"


# Python libraries
import os
import datetime
import logging
from collections import namedtuple
import calendar

# External libraries
import requests
import pandas as pd
import pvlib
from shapely.geometry import Point
from windpowerlib.wind_turbine import WindTurbine

# Internal modules
from reegis import tools
from reegis import feedin
from reegis import config as cfg
from reegis import powerplants as powerplants
from reegis import geometries
from reegis import bmwi


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
        clearsky_dni=clearskydni)
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

    pv_sets = None
    wind_sets = None

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

    if wind:
        logging.info(txt_create.format('wind', year))
        # Add directory if not present
        os.makedirs(coastdat_path.format(year=year, type='wind'),
                    exist_ok=True)
        # Create the pv-sets defined in the wind.ini
        wind_sets = feedin.create_windpowerlib_sets()
        # Open a file for each main set (subsets are stored in columns)
        for wind_key, wind_set in wind_sets.items():
            for subset_key, subset in wind_set.items():
                wind_sets[wind_key][subset_key] = WindTurbine(
                    **subset)
            filename = feedin_file.format(
                type='wind', year=year, set_name=wind_key)
            if not os.path.isfile(filename) or overwrite:
                hdf['wind'][wind_key] = pd.HDFStore(filename, mode='w')

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


def store_average_weather(data_type, weather_path=None, years=None, keys=None,
                          out_file_pattern='average_data_{data_type}.csv'):
    """
    Get average wind speed over all years for each weather region. This can be
    used to select the appropriate wind turbine for each region
    (strong/low wind turbines).
    
    Parameters
    ----------
    data_type : str
        The data_type of the coastdat weather data: 'dhi', 'dirhi', 'pressure',
         'temp_air', 'v_wind', 'z0'.
    keys : list or None
        List of coastdat keys. If None all available keys will be used.
    years : list or None
        List of one or more years to calculate the average data from. You
        have to make sure that the weather data files for the given years
        exist in the weather path.
    weather_path : str
        Path to folder that contains all needed files. If None the default
        path defined in the config file will be used.
    out_file_pattern : str or None
        Name of the results file with a placeholder for the data type e.g.
        ``average_data_{data_type}.csv``). If None no file will be written.

    Examples
    --------
    >>> store_average_weather('temp_air', years=[2014, 2013])  # doctest: +SKIP
    >>> v = store_average_weather('v_wind', years=[2014],
    ...                           out_file_pattern=None, keys=[1132101])
    >>> float(v.loc[1132101].round(2))
    4.39
    """
    logging.info("Calculating the average wind speed...")

    weather_pattern = cfg.get('coastdat', 'file_pattern')

    if weather_path is None:
        weather_path = cfg.get('paths', 'coastdat')

    # Finding existing weather files.
    data_files = os.listdir(weather_path)

    # Possible time range for coastdat data set (reegis: 1998-2014).
    check = True
    if years is None:
        years = range(1948, 2017)
        check = False

    used_years = []
    for year in years:
        if weather_pattern.format(year=year) in data_files:
            used_years.append(year)
        elif check is True:
            msg = "File not found".format(weather_pattern.format(year=year))
            raise FileNotFoundError(msg)

    # Loading coastdat-grid as shapely geometries.
    coastdat_polygons = pd.DataFrame(geometries.load(
        cfg.get('paths', 'geometry'),
        cfg.get('coastdat', 'coastdatgrid_polygon')))
    coastdat_polygons.drop('geometry', axis=1, inplace=True)

    # Opening all weather files
    weather = dict()

    # open hdf files
    for year in used_years:
        weather[year] = pd.HDFStore(os.path.join(
            weather_path, weather_pattern.format(year=year)), mode='r')

    if keys is None:
        keys = coastdat_polygons.index

    n = len(list(keys))
    logging.info("Remaining: {0}".format(n))
    for key in keys:
        data_type_avg = pd.Series()
        n -= 1
        if n % 100 == 0:
            logging.info("Remaining: {0}".format(n))
        hdf_id = '/A{0}'.format(key)
        for year in used_years:
            ws = weather[year][hdf_id][data_type]
            data_type_avg = data_type_avg.append(
                ws, verify_integrity=True)

        # calculate the average wind speed for one grid item
        coastdat_polygons.loc[key, '{0}_avg'.format(data_type)] = (
            data_type_avg.mean())

    # Close hdf files
    for year in used_years:
        weather[year].close()

    if keys is not None:
        coastdat_polygons.dropna(inplace=True)

    # write results to csv file
    if out_file_pattern is not None:
        filename = out_file_pattern.format(data_type=data_type)
        fn = os.path.join(weather_path, filename)
        logging.info("Average temperature saved to {0}".format(fn))
        coastdat_polygons.to_csv(fn)
    return coastdat_polygons


def spatial_average_weather(year, geo, parameter, name,
                            outpath=None, outfile=None):
    """
    Calculate the mean value of a parameter over all data sets within each
    region for one year.

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
    name : str
        Name of the regions table to be used as a column name.

    Returns
    -------
    str : Full file name of the created file.

    Example
    -------
    >>> germany_geo = geometries.load(
    ...     cfg.get('paths', 'geometry'),
    ...     cfg.get('geometry', 'germany_polygon'))
    >>> fn = spatial_average_weather(2012, germany_geo, 'temp_air', 'deTemp',
    ...                              outpath=os.path.expanduser('~')
    ...                              )# doctest: +SKIP
    >>> temp = pd.read_csv(fn, index_col=[0], parse_dates=True, squeeze=True
    ...                    )# doctest: +SKIP
    >>> round(temp.mean() - 273.15, 2)# doctest: +SKIP
    8.28
    >>> os.remove(fn)# doctest: +SKIP
    """
    logging.info("Getting average {0} for {1} in {2} from coastdat2.".format(
        parameter, name, year))

    name = name.replace(' ', '_')

    # Create a Geometry object for the coastdat centroids.
    coastdat_geo = geometries.load(cfg.get('paths', 'geometry'),
                                   cfg.get('coastdat', 'coastdatgrid_polygon'))
    coastdat_geo['geometry'] = coastdat_geo.centroid

    # Join the tables to create a list of coastdat id's for each region.
    coastdat_geo = geometries.spatial_join_with_buffer(
        coastdat_geo, geo, name=name, limit=0)

    # Fix regions with no matches (no matches if a region ist too small).
    fix = {}
    for reg in set(geo.index) - set(coastdat_geo[name].unique()):
        reg_point = geo.representative_point().loc[reg]
        coastdat_poly = geometries.load(
            cfg.get('paths', 'geometry'),
            cfg.get('coastdat', 'coastdatgrid_polygon'))
        fix[reg] = coastdat_poly.loc[coastdat_poly.intersects(
            reg_point)].index[0]

    # Open the weather file
    weather_file = os.path.join(
        cfg.get('paths', 'coastdat'),
        cfg.get('coastdat', 'file_pattern').format(year=year))
    if not os.path.isfile(weather_file):
        download_coastdat_data(year=year, filename=weather_file)
    weather = pd.HDFStore(weather_file, mode='r')

    # Calculate the average temperature for each region with more than one id.
    avg_value = pd.DataFrame()
    for region in geo.index:
        cd_ids = coastdat_geo[coastdat_geo[name] == region].index
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
    regions = sorted(geo.index)
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
    """
    Example for spatial_average_weather() with federal states polygons.

    Parameters
    ----------
    year
    parameter

    Returns
    -------

    """
    federal_states = geometries.get_federal_states_polygon()
    filename = os.path.join(
        cfg.get('paths', 'coastdat'),
        'average_{0}_BB_TH_{1}.csv'.format(parameter, year))
    if not os.path.isfile(filename):
        spatial_average_weather(year, federal_states, parameter,
                                'federal_states', outfile=filename)
    return pd.read_csv(filename, index_col=[0], parse_dates=True,
                       date_parser=lambda col: pd.to_datetime(col, utc=True))


def aggregate_by_region_coastdat_feedin(pp, regions, year, category, outfile,
                                        weather_year=None):
    """
    Aggregate wind and pv feedin time series for each region defined by
    a geoDataFrame with region polygons.

    Parameters
    ----------
    pp : pd.DataFrame
        Power plant table.
    regions : geopandas.geoDataFrame
        Table with the polygons.
    year : int
        Year for the power plants and for the weather data if weather_year is
        None.
    category : str
        Feed-in category: 'wind' or 'solar'
    outfile : str
        Name of the output file.
    weather_year : int or None
        If None the year parameter will be used for the weather year.

    """
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
    # Do normalized timeseries exist? If not, create
    if os.path.isdir(coastdat_path):
        if len(os.listdir(coastdat_path)) == 0:
            normalised_feedin_for_each_data_set(weather_year)
    else:
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
    my_cols = pd.MultiIndex(levels=[[], [], []], codes=[[], [], []],
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
    """Aggregate hydro power plants by region."""

    hydro = bmwi.bmwi_re_energy_capacity()['water']

    hydro_capacity = (pp.loc['Hydro', 'capacity_{0}'.format(year)].sum())

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
    """Aggregate hydro power plants by region."""
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


def load_feedin_by_region(year, feedin_type, name, region=None,
                          weather_year=None):
    """

    Parameters
    ----------
    year
    feedin_type
    name
    region
    weather_year

    Returns
    -------

    """
    feedin_path = os.path.join(cfg.get('paths', 'feedin'), name, str(year))

    # Create pattern for the name of the resulting files.
    if weather_year is None:
        feedin_region_outfile_name = os.path.join(
            feedin_path,
            cfg.get('feedin', 'region_file_pattern').format(
                year=year, type=feedin_type, name=name))
    else:
        feedin_path = os.path.join(feedin_path, 'weather_variations')
        feedin_region_outfile_name = os.path.join(
            feedin_path,
            cfg.get('feedin', 'region_file_pattern_var').format(
                year=year, type=feedin_type, name=name, var=weather_year))

    # Add any federal state to get its normalised feed-in.
    if feedin_type in ['solar', 'wind']:
        fd_in = pd.read_csv(feedin_region_outfile_name, index_col=[0],
                            header=[0, 1, 2])
    elif feedin_type in ['hydro', 'geothermal']:
        fd_in = pd.read_csv(feedin_region_outfile_name, index_col=[0],
                            header=[0])
    else:
        fd_in = None

    if region is not None and fd_in is not None:
        fd_in = fd_in[region]
    return fd_in


def windzone_region_fraction(pp, name, year=None, dump=False):
    """

    Parameters
    ----------
    pp : pd.DataFrame
    year : int
    name : str
    dump : bool

    Returns
    -------

    Examples
    --------
    >>> my_fn = os.path.join(cfg.get('paths', 'powerplants'),
    ...                      cfg.get('powerplants', 'reegis_pp'))
    >>> my_pp = pd.DataFrame(pd.read_hdf(my_fn, 'pp'))  # doctest: +SKIP
    >>> wz = windzone_region_fraction(my_pp, 'federal_states', 2014
    ...                               dump=False)  # doctest: +SKIP
    >>> round(float(wz.loc['NI', 1]), 2)  # doctest: +SKIP
    0.31
    """
    pp = pp.loc[pp.energy_source_level_2 == 'Wind']

    if year is None:
        capacity_col = 'capacity'
    else:
        capacity_col = 'capacity_{0}'.format(year)

    path = cfg.get('paths', 'geometry')
    filename = 'windzones_germany.geojson'
    gdf = geometries.load(path=path, filename=filename)
    gdf.set_index('zone', inplace=True)

    geo_path = cfg.get('paths', 'geometry')
    geo_file = cfg.get('coastdat', 'coastdatgrid_polygon')
    coastdat_geo = geometries.load(path=geo_path, filename=geo_file)
    coastdat_geo['geometry'] = coastdat_geo.centroid

    points = geometries.spatial_join_with_buffer(coastdat_geo, gdf, 'windzone')

    wz = pd.DataFrame(points['windzone'])
    pp = pd.merge(pp, wz, left_on='coastdat2', right_index=True)
    pp['windzone'].fillna(0, inplace=True)
    pp = pp.groupby([name, 'windzone']).sum()[capacity_col]
    wz_regions = pp.groupby(level=0).apply(lambda x: x / float(x.sum()))

    if dump is True:
        filename = 'windzone_{0}.csv'.format(name)
        fn = os.path.join(cfg.get('paths', 'powerplants'), filename)
        wz_regions.to_csv(fn, header=False)
    return wz_regions


def scenario_feedin(year, name, weather_year=None, feedin_ts=None):
    """
    Load solar, wind, hydro, geothermal for all regions in one Mulitindex table

    year : int
    name : str
    weather_year : pd.DataFrame or None
    feedin_ts : pd.DataFrame or None

    """
    if feedin_ts is None:
        cols = pd.MultiIndex(levels=[[], []], codes=[[], []])
        feedin_ts = pd.DataFrame(columns=cols)

    hydro = load_feedin_by_region(
        year, 'hydro', name, weather_year=weather_year).reset_index(drop=True)
    for region in hydro.columns:
        feedin_ts[region, 'hydro'] = hydro[region]

    geothermal = load_feedin_by_region(
        year, 'geothermal', name, weather_year=weather_year).reset_index(
        drop=True)
    for region in geothermal.columns:
        feedin_ts[region, 'geothermal'] = geothermal[region]

    if calendar.isleap(year) and weather_year is not None:
        if not calendar.isleap(weather_year):
            feedin_ts = feedin_ts.iloc[:8760]

    feedin_ts = scenario_feedin_pv(year, name, feedin_ts=feedin_ts,
                                   weather_year=weather_year)

    feedin_ts = scenario_feedin_wind(year, name, feedin_ts=feedin_ts,
                                     weather_year=weather_year)

    return feedin_ts.sort_index(1)


def scenario_feedin_wind(year, name, regions=None, feedin_ts=None,
                         weather_year=None):
    """

    Parameters
    ----------
    year
    name
    regions
    feedin_ts
    weather_year

    Returns
    -------

    """
    # Get fraction of windzone per region
    wz = pd.read_csv(os.path.join(cfg.get('paths', 'powerplants'),
                                  'windzone_{0}.csv'.format(name)),
                     index_col=[0, 1], header=None)

    # Get normalised feedin time series
    wind = load_feedin_by_region(
        year, 'wind', name, weather_year=weather_year).reset_index(drop=True)

    if weather_year is not None:
        if calendar.isleap(weather_year) and not calendar.isleap(year):
            wind = wind.iloc[:8760]

    # Rename columns and remove obsolete level
    wind.columns = wind.columns.droplevel(2)
    cols = wind.columns.get_level_values(1).unique()
    rn = {c: c.replace('coastdat_{0}_wind_'.format(year), '') for c in cols}
    wind.rename(columns=rn, level=1, inplace=True)
    wind.sort_index(1, inplace=True)

    # Get wind turbines by wind zone
    wind_types = {float(k): v for (k, v) in cfg.get_dict('windzones').items()}
    wind_types = pd.Series(wind_types).sort_index()

    if regions is None:
        regions = wind.columns.get_level_values(0).unique()

    if feedin_ts is None or len(feedin_ts.index) == 0:
        cols = pd.MultiIndex(levels=[[], []], codes=[[], []])
        feedin_ts = pd.DataFrame(index=wind.index, columns=cols)

    for region in regions:
        frac = pd.merge(wz.loc[region], pd.DataFrame(wind_types), how='right',
                        right_index=True, left_index=True).set_index(
                            0, drop=True).fillna(0).sort_index()
        feedin_ts[region, 'wind'] = wind[region].multiply(frac[2]).sum(1)
    return feedin_ts.sort_index(1)


def scenario_feedin_pv(year, name, regions=None, feedin_ts=None,
                       weather_year=None):
    """
    Join the different solar types and orientations to one time series defined
    by the fraction of each type and orientation.

    Parameters
    ----------
    year
    name
    regions
    feedin_ts
    weather_year

    Returns
    -------

    """
    pv_types = cfg.get_dict('pv_types')
    pv_orientation = cfg.get_dict('pv_orientation')
    pv = load_feedin_by_region(
        year, 'solar', name, weather_year=weather_year).reset_index(drop=True)

    if weather_year is not None:
        if calendar.isleap(weather_year) and not calendar.isleap(year):
            pv = pv.iloc[:8760]

    if regions is None:
        regions = pv.columns.get_level_values(0).unique()

    if feedin_ts is None or len(feedin_ts.index) == 0:
        cols = pd.MultiIndex(levels=[[], []], codes=[[], []])
        feedin_ts = pd.DataFrame(index=pv.index, columns=cols)

    orientation_fraction = pd.Series(pv_orientation)

    pv.sort_index(1, inplace=True)
    orientation_fraction.sort_index(inplace=True)
    base_set_column = 'coastdat_{0}_solar_{1}'.format(year, '{0}')

    for region in regions:
        # combine different pv-sets to one feedin time series
        feedin_ts[region, 'solar'] = 0
        for mset in pv_types.keys():
            set_col = base_set_column.format(mset)
            feedin_ts[region, 'solar'] += pv[region, set_col].multiply(
                orientation_fraction).sum(1).multiply(pv_types[mset])
    return feedin_ts.sort_index(1)


def get_feedin_per_region(year, region, name, weather_year=None,
                          windzones=True, subregion=False, pp=None):
    """
    Aggregate feed-in time series for the given geometry set.

    Parameters
    ----------
    year : int
    region : geopandas.geoDataFrame
    name : str
    weather_year : int
    windzones : bool
    pp : pd.DataFrame or None
    subregion : bool
        Set to True if all region polygons together are a subregion of
        Germany. This will switch off the buffer in the spatial_join function.

    Notes
    -----
    The feedin is calculated per region entry (row of the region CSV / GeoDF),
    the output file will contain columns per region entry and generator set
    entry. E.g. a file with 10 regions and 2 wind generators will result in 20
    different feedin timeseries.
    Example region file: federalstates_polygon.csv

    You may want to use geometries.load() to import a region CSV.
    """
    # create and dump reegis basic powerplants table (created from opsd data)
    fn = powerplants.pp_opsd2reegis()
    filename = fn.split(os.sep)[-1]
    path = fn.replace(filename, '')

    # Add column name "coastdat2" with the id of the coastdat weather cell for
    # each power plant.
    geo_path = cfg.get('paths', 'geometry')
    geo_file = cfg.get('coastdat', 'coastdatgrid_polygon')
    gdf = geometries.load(path=geo_path, filename=geo_file)

    pp = powerplants.add_regions_to_powerplants(
        gdf, 'coastdat2', filename=filename, path=path, pp=pp)

    # Add a column named with the name parameter, adding the region id to
    # each power plant
    pp = powerplants.add_regions_to_powerplants(
        region, name, filename=filename, path=path, pp=pp, subregion=subregion)

    # Get only the power plants that are online in the given year.
    pp = powerplants.get_reegis_powerplants(year, pp=pp)

    if windzones:
        windzone_region_fraction(pp, name, year=year, dump=True)

    # Aggregate feedin time series for each region
    return aggregate_feedin_by_region(year, pp, name,
                                      weather_year=weather_year)


def aggregate_feedin_by_region(year, pp, name, weather_year=None):
    """
    Aggregate all feed-in time series for one year and one region set.
    The name of the region set has to be a column in the pp table.
    """
    # Create the path for the output files.
    feedin_path = os.path.join(cfg.get('paths', 'feedin'), name, str(year))

    if weather_year is not None:
        feedin_path = os.path.join(feedin_path, 'weather_variations')

    os.makedirs(feedin_path, exist_ok=True)

    # Create pattern for the name of the resulting files.
    if weather_year is None:
        feedin_deflex_outfile_name = os.path.join(
            feedin_path,
            cfg.get('feedin', 'region_file_pattern').format(
                year=year, type='{type}', name=name))
    else:
        feedin_deflex_outfile_name = os.path.join(
            feedin_path,
            cfg.get('feedin', 'region_file_pattern_var').format(
                year=year, type='{type}', name=name, var=weather_year))

    # Filter the capacity of the powerplants for the given year.
    pp = pp.groupby(
        ['energy_source_level_2', name, 'coastdat2']).sum()

    pp.index = pp.index.set_levels(pp.index.levels[1].astype(str), level=1)
    regions = pp.index.get_level_values(1).unique().sort_values()

    # Loop over weather depending feed-in categories.
    # WIND and PV
    for cat in ['Wind', 'Solar']:
        outfile_name = feedin_deflex_outfile_name.format(type=cat.lower())
        if not os.path.isfile(outfile_name):
            aggregate_by_region_coastdat_feedin(
                pp, regions, year, cat, outfile_name, weather_year)

    # HYDRO
    outfile_name = feedin_deflex_outfile_name.format(type='hydro')
    if not os.path.isfile(outfile_name):
        aggregate_by_region_hydro(pp, regions, year, outfile_name)

    # GEOTHERMAL
    outfile_name = feedin_deflex_outfile_name.format(type='geothermal')
    if not os.path.isfile(outfile_name):
        aggregate_by_region_geothermal(regions, year, outfile_name)
    return feedin_path


def get_solar_time_series_for_one_location(latitude, longitude, year,
                                           set_name=None):
    """
    Get a normalised solar time series for one location for one set or all
    available set if set_name is None.
    """
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


def get_solar_time_series_for_one_location_all_years(latitude, longitude,
                                                     set_name=None):
    """
    Get a normalised solar time series for one location for one set or all
    available set if set_name is None. Get all available years.
    """
    path = os.path.join(cfg.get('paths', 'feedin'), 'coastdat')
    years = os.listdir(path)
    df = pd.DataFrame(columns=pd.MultiIndex(levels=[[], []], codes=[[], []]))

    for year in years:
        if os.path.isdir(os.path.join(path, str(year))):
            tmp = get_solar_time_series_for_one_location(
                latitude, longitude, year, set_name).reset_index(drop=True)
            for col in tmp.columns:
                df[year, col] = tmp[col]
    return df


def federal_states_feedin_example():
    """Get fullload hours for renewable sources for a federal states."""
    federal_states = geometries.get_federal_states_polygon()
    get_feedin_per_region(2014, federal_states, 'federal_states')
    return scenario_feedin(2014, 'federal_states')


if __name__ == "__main__":
    pass
