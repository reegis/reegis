# -*- coding: utf-8 -*-

""" This module is designed for the use with the pvlib, windpowerlib. If you
want to use other libraries you have to adapt the code.

The weather data set has to be a DataFrame with the following columns:

pvlib:
 * ghi - global horizontal irradiation [W/m2]
 * dni - direct normal irradiation [W/m2]
 * dhi - diffuse horizontal irradiation [W/m2]
 * temp_air - ambient temperature [°C]

windpowerlib:
 * pressure - air pressure [Pa]
 * temp_air - ambient temperature [K]
 * v_wind - horizontal wind speed [m/s]
 * z0 - roughness length [m]

Copyright (c) 2016-2018 Uwe Krien <uwe.krien@rl-institut.de>

SPDX-License-Identifier: GPL-3.0-or-later
"""
__copyright__ = "Uwe Krien <uwe.krien@rl-institut.de>"
__license__ = "GPLv3"


# Python libraries
import logging

# External libraries
import pandas as pd
import windpowerlib
import pvlib
# from pvlib.pvsystem import PVSystem
# from pvlib.modelchain import ModelChain

# oemof libraries
from oemof.tools import logger

# Internal modules
import reegis_tools.config as cfg


def get_optimal_pv_angle(lat):
    """ About 27° to 34° from ground in Germany.
    The pvlib uses tilt angles horizontal=90° and up=0°. Therefore 90° minus
    the angle from the horizontal.
    """
    return lat - 20


def create_pvlib_sets():
    """Create pvlib parameter sets from the solar.ini file.

    Returns
    -------
    dict
    """
    # get module and inverter parameter from sandia database
    sandia_modules = pvlib.pvsystem.retrieve_sam('sandiamod')
    sapm_inverters = pvlib.pvsystem.retrieve_sam('sandiainverter')

    pvlib_sets = cfg.get_list('solar', 'set_list')

    pvsets = {}
    for pvlib_set in pvlib_sets:
        set_name = cfg.get(pvlib_set, 'pv_set_name')
        module_name = cfg.get(pvlib_set, 'module_name')
        module_key = cfg.get(pvlib_set, 'module_key')
        inverter = cfg.get(pvlib_set, 'inverter_name')
        azimuth_angles = cfg.get_list(pvlib_set, 'surface_azimuth')
        tilt_angles = cfg.get_list(pvlib_set, 'surface_tilt')
        albedo_values = cfg.get_list(pvlib_set, 'albedo')

        set_idx = 0
        pvsets[set_name] = {}
        for t in tilt_angles:
            if t == '0':
                az_angles = (0,)
            else:
                az_angles = azimuth_angles
            for a in az_angles:
                for alb in albedo_values:
                    set_idx += 1
                    pvsets[set_name][set_idx] = {
                        'module_parameters': sandia_modules[module_name],
                        'inverter_parameters': sapm_inverters[inverter],
                        'surface_azimuth': float(a),
                        'surface_tilt': t,
                        'albedo': float(alb)}
                    pvsets[set_name][set_idx]['p_peak'] = (
                        pvsets[set_name][set_idx]['module_parameters'].Impo *
                        pvsets[set_name][set_idx]['module_parameters'].Vmpo)
                    pvsets[set_name][set_idx]['name'] = "_".join([
                        module_key,
                        inverter[:3],
                        "tlt{}".format(t[:3].rjust(3, '0')),
                        "az{}".format(str(a).rjust(3, '0')),
                        "alb{}".format(str(alb).replace('.', ''))
                    ])
                    logging.debug("PV set: {}".format(
                        pvsets[set_name][set_idx]['name']))

    return pvsets


def feedin_pv_sets(weather, location, pv_parameter_set):
    """Create a pv feed-in time series from a given weather data set and a
    set of pvlib parameter sets. The result of every parameter set will be a
    column in the resulting DataFrame.

    Parameters
    ----------
    weather : pandas.DataFrame
        Weather data set. See module header.
    location : pvlib.location.Location
        Location of the weather data.
    pv_parameter_set : dict
        Parameter sets can be created using `create_pvlib_sets()`.

    Returns
    -------
    pandas.DataFrame

    """
    df = pd.DataFrame()
    for pv_system in pv_parameter_set.values():
        if pv_system['surface_tilt'] == 'optimal':
            tilt = get_optimal_pv_angle(location.latitude)
        else:
            tilt = float(pv_system['surface_tilt'])
        mc = feedin_pvlib(location, pv_system, weather, tilt=tilt)
        df[pv_system['name']] = mc
    return df


def feedin_pvlib(location, system, weather, tilt=None, peak=None,
                 orientation_strategy=None, installed_capacity=1):
    """
    Create a pv feed-in time series from a given weather data set and a valid
    pvlib parameter set.

    Parameters
    ----------
    location : pvlib.location.Location or dict
        Location of the weather data.
    system : dict
        System parameter for the pvlib.
    weather : pandas.DataFrame
        Weather data set. See file header for more information.
    tilt : float
        The tilt angle of the surface. This value can also be defined directly
        in the system dictionary..
    peak : float
        Peak power of the pv-module. This value can also be defined directly
        in the system dictionary.
    orientation_strategy : str
        See the pvlib documentation for different strategies.
    installed_capacity : float
        Overall installed capacity for the given pv module. The installed
        capacity is set to 1 by default for normalised time series.

    Returns
    -------

    """
    if tilt is None:
        tilt = system['surface_tilt']

    if peak is not None:
        system['peak'] = peak

    if not isinstance(location, pvlib.location.Location):
        location = pvlib.location.Location(**location)

    # pvlib's ModelChain
    pvsys = pvlib.pvsystem.PVSystem(
        inverter_parameters=system['inverter_parameters'],
        module_parameters=system['module_parameters'],
        surface_tilt=tilt,
        surface_azimuth=system['surface_azimuth'],
        albedo=system['albedo'])

    mc = pvlib.modelchain.ModelChain(
        pvsys, location, orientation_strategy=orientation_strategy)
    out = mc.run_model(weather.index, weather=weather)
    return out.ac.fillna(0).clip(0).div(system['p_peak']).multiply(
        installed_capacity)


def create_windpowerlib_sets():
    """Create parameter sets for the windpowerlib from wind.ini.

    Returns
    -------
    dict

    """
    windpowerlib_sets = cfg.get_list('wind', 'set_list')

    # Only one subset is created but following the pvlib sets it is possible
    # to create subsets.
    windsets = {}
    for windpowerlib_set in windpowerlib_sets:
        set_name = cfg.get(windpowerlib_set, 'set_name')
        windsets[set_name] = {1: {}}
        windsets[set_name][1]['hub_height'] = cfg.get(
            windpowerlib_set, 'hub_height')
        windsets[set_name][1]['d_rotor'] = cfg.get(
            windpowerlib_set, 'd_rotor')
        windsets[set_name][1]['turbine_name'] = cfg.get(
            windpowerlib_set, 'turbine_name')
        windsets[set_name][1]['nominal_power'] = cfg.get(
            windpowerlib_set, 'nominal_power')
    return windsets


def feedin_wind_sets(weather, data_height, wind_parameter_set):
    """Create a pv feed-in time series from a given weather data set and a
    set of pvlib parameter sets. The result of every parameter set will be a
    column in the resulting DataFrame.

    Parameters
    ----------
    weather : pandas.DataFrame
        Weather data set. See module header.
    data_height :
        Data heigth of the weather data.
    wind_parameter_set : dict
        Parameter sets can be created using `create_windpowerlib_sets()`.

    Returns
    -------
    pandas.DataFrame

    """
    df = pd.DataFrame()
    for turbine in wind_parameter_set.values():
        mc = feedin_windpowerlib(weather, data_height, turbine)
        df[turbine['turbine_name'].replace(' ', '_')] = mc
    return df


def feedin_windpowerlib(weather, data_height, turbine, installed_capacity=1):
    """Use the windpowerlib to generate normalised feedin time series.

    Parameters
    ----------
    turbine : dict
        Parameters of the wind turbine (hub height, diameter of the rotor,
        identifier of the turbine to get cp-series, nominal power).
    weather : pandas.DataFrame
        Weather data set. See module header.
    data_height :
        Data heigth of the weather data.
    installed_capacity : float
        Overall installed capacity for the given wind turbine. The installed
        capacity is set to 1 by default for normalised time series.

    Returns
    -------
    pandas.DataFrame

    """
    wpp = windpowerlib.wind_turbine.WindTurbine(**turbine)
    modelchain_data = cfg.get_dict('windpowerlib')
    mc = windpowerlib.modelchain.ModelChain(wpp, **modelchain_data)
    mcwpp = mc.run_model(weather, data_height=data_height)
    return mcwpp.power_output.div(turbine['nominal_power']).multiply(
        installed_capacity)


# from datetime import datetime as time
import os
# import bisect
# from pvlib.location import Location


def normalised_feedin_by_region_wind(pp, feedin_de21, feedin_coastdat,
                                     overwrite):
    """

    Parameters
    ----------
    pp
    feedin_de21
    feedin_coastdat
    overwrite

    Returns
    -------

    """
    vtype = 'Wind'

    # Check for existing in-files and non-existing out-files
    years = list()
    for y in range(1990, 2025):
        outfile = feedin_de21.format(year=y, type=vtype.lower())
        infile = feedin_coastdat.format(year=y, type=vtype.lower(),
                                        sub='coastdat')
        if not os.path.isfile(outfile) or overwrite:
            if os.path.isfile(infile):
                years.append(y)
    if overwrite:
        logging.warning("Existing files will be overwritten.")
    else:
        logging.info("Existing files are skipped.")
    logging.info(
        "Will create {0} time series for the following years: {1}".format(
            vtype.lower(), years))

    # Loop over all years according to the file check above
    for year in years:
        logging.info("Processing {0}...".format(year))
        pwr = pd.HDFStore(feedin_coastdat.format(year=year,
                                                 type=vtype.lower(),
                                                 sub='coastdat'))
        my_index = pwr[pwr.keys()[0]].index
        feedin = pd.DataFrame(index=my_index)

        # Loop over all aggregation regions
        for region in sorted(
                pp.loc[(vtype, year)].index.get_level_values(0).unique()):

            # Create an temporary DataFrame to collect the results
            temp = pd.DataFrame(index=my_index)
            logging.debug("{0} - {1}".format(year, region))

            # Multiply normalised time series (normalised to 1kW_peak) with peak
            # capacity(kW).
            for coastdat in pp.loc[(vtype, year, region)].index:
                tmp = pwr['/A' + str(int(coastdat))].multiply(
                    float(pp.loc[(vtype, year, region, coastdat)]))
                temp[coastdat] = tmp
            if str(region) == 'nan':
                region = 'unknown'

            # Sum up time series for one region and divide it by the
            # capacity of the region to get a normalised time series.
            feedin[region] = temp.sum(axis=1).divide(
                    float(pp.loc[(vtype, year, region)].sum()))

        # Write table into a csv-file
        feedin.to_csv(feedin_de21.format(year=year, type=vtype.lower()))
        pwr.close()


def normalised_feedin_by_region_solar(pp, feedin_de21, feedin_coastdat,
                                      overwrite):
    vtype = 'Solar'
    de21_dir = os.path.dirname(feedin_de21.format(type=vtype.lower(),
                                                  year=2000))
    if not os.path.isdir(de21_dir):
        os.mkdir(de21_dir)

    set_list = config.get_list('solar', 'solar_sets_list')
    set_names = list()
    for my_set in set_list:
        set_names.append(cfg.get(my_set, 'pv_set_name'))

    # Check for existing output and input files
    # Only years with all sets will be used
    years = list()
    for y in range(1990, 2025):
        outfile = feedin_de21.format(year=y, type=vtype.lower())
        infiles_exist = True
        if not os.path.isfile(outfile) or overwrite:
            for name_set in set_names:
                infile = feedin_coastdat.format(year=y, type=vtype.lower(),
                                                sub=name_set)
                if not os.path.isfile(infile):
                    infiles_exist = False
            if infiles_exist:
                years.append(y)

    # Display logging warning of files will be overwritten
    if overwrite:
        logging.warning("Existing files will be overwritten.")
    else:
        logging.info("Existing files are skipped.")
    logging.info(
        "Will create {0} time series for the following years: {1}".format(
            vtype.lower(), years))

    pwr = dict()
    columns = dict()
    for year in years:
        logging.info("Processing {0}...".format(year))
        name_of_set = None
        for name_of_set in set_names:
            pwr[name_of_set] = pd.HDFStore(
                feedin_coastdat.format(year=year, sub=name_of_set,
                                       type=vtype.lower()))
            columns[name_of_set] = pwr[name_of_set]['/A1129087'].columns

        # Create DataFrame with MultiColumns to take the results
        my_index = pwr[name_of_set]['/A1129087'].index
        my_cols = pd.MultiIndex(levels=[[], [], []], labels=[[], [], []],
                                names=[u'region', u'set', u'subset'])
        feedin = pd.DataFrame(index=my_index, columns=my_cols)

        # Loop over all aggregation regions
        for region in sorted(
                pp.loc[(vtype, year)].index.get_level_values(0).unique()):
            coastdat_ids = pp.loc[(vtype, year, region)].index
            logging.info("{0} - {1} ({2})".format(
                year, region, len(coastdat_ids)))
            logging.debug("{0}".format(pp.loc[(vtype, year, region)].index))

            # Loop over all coastdat ids, that intersect with the region
            for name in set_names:
                for col in columns[name]:
                    temp = pd.DataFrame(index=my_index)
                    for coastdat in pp.loc[(vtype, year, region)].index:
                        coastdat_id = '/A{0}'.format(int(coastdat))
                        pp_inst = float(pp.loc[(vtype, year, region, coastdat)])
                        temp[coastdat_id] = (
                            pwr[name][coastdat_id][col][:8760].multiply(
                                pp_inst))
                    colname = '_'.join(col.split('_')[-3:])
                    feedin[region, name, colname] = (
                        temp.sum(axis=1).divide(float(
                            pp.loc[(vtype, year, region)].sum())))

            # Sum up time series for one region and divide it by the
            # capacity of the region to get a normalised time series.

        feedin.to_csv(feedin_de21.format(year=year, type=vtype.lower()))
        for name_of_set in set_names:
            pwr[name_of_set].close()


def normalised_feedin_by_region_hydro(c, feedin_de21, regions, overwrite=False):
    hydro_energy = pd.read_csv(
        os.path.join(c.paths['static'], 'energy_capacity_bmwi.csv'),
        header=[0, 1], index_col=[0])['Wasserkraft']['energy']

    hydro_capacity = pd.read_csv(
        os.path.join(c.paths['powerplants'], c.files['sources']),
        index_col=[0, 1, 2]).loc['Hydro'].groupby(
            'year').sum().loc[hydro_energy.index].capacity

    full_load_hours = (hydro_energy / hydro_capacity).multiply(1000)

    hydro_path = os.path.abspath(os.path.join(
        *feedin_de21.format(year=0, type='hydro').split('/')[:-1]))

    if not os.path.isdir(hydro_path):
        os.makedirs(hydro_path)

    skipped = list()
    for year in full_load_hours.index:
        filename = feedin_de21.format(year=year, type='hydro')
        if not os.path.isfile(filename) or overwrite:
            idx = pd.date_range(start="{0}-01-01 00:00".format(year),
                                end="{0}-12-31 23:00".format(year),
                                freq='H',tz='Europe/Berlin')
            feedin = pd.DataFrame(columns=regions, index=idx)
            feedin[feedin.columns] = full_load_hours.loc[year] / len(feedin)
            feedin.to_csv(filename)
        else:
            skipped.append(year)

    if len(skipped) > 0:
        logging.warning("Hydro feedin. Skipped the following years:\n" +
                        "{0}.\n".format(skipped) +
                        " Use overwrite=True to replace the files.")

    # https://shop.dena.de/fileadmin/denashop/media/Downloads_Dateien/esd/
    # 9112_Pumpspeicherstudie.pdf
    # S. 110ff


def normalised_feedin_by_region(c, overwrite=False):
    feedin_de21 = os.path.join(c.paths['feedin'], '{type}', 'de21',
                               c.pattern['feedin_de21'])
    feedin_coastdat = os.path.join(c.paths['feedin'], '{type}', '{sub}',
                                   c.pattern['feedin'])
    category = 'renewable'
    powerplants = os.path.join(c.paths[category],
                               c.pattern['grouped'].format(cat=category))

    pp = pd.read_csv(powerplants, index_col=[0, 1, 2, 3])

    regions = pp.index.get_level_values(2).unique().sort_values()

    normalised_feedin_by_region_solar(pp, feedin_de21, feedin_coastdat,
                                      overwrite)
    normalised_feedin_by_region_wind(pp, feedin_de21, feedin_coastdat,
                                     overwrite)
    normalised_feedin_by_region_hydro(c, feedin_de21, regions, overwrite)


if __name__ == "__main__":
    logger.define_logging()
    y = 2012
    hd_file = pd.HDFStore(os.path.join(
        cfg.get('paths', 'feedin'), 'wind', 'coastdat',
        cfg.get('feedin', 'feedin_file_pattern').format(year=y,
                                                        type='wind')),
        mode='r')
    print(hd_file['/A1113109'].sum())
    hd_file.close()
    # cfg = config.get_configuration()
    # normalised_feedin_by_region(cfg, overwrite=True)
