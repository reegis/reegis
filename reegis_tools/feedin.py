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
from windpowerlib.modelchain import ModelChain
from windpowerlib.wind_turbine import WindTurbine
import pvlib

# oemof libraries
from oemof import tools

# Internal modules
import reegis_tools.config as cfg


def get_optimal_pv_angle(lat):
    """ About 27° to 34° from ground in Germany.
    The pvlib uses tilt angles horizontal=90° and up=0°. Therefore 90° minus
    the angle from the horizontal.
    """
    return lat - 15


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
        w_set = {1: cfg.get_dict(windpowerlib_set)}
        set_name = w_set[1].pop('set_name')
        windsets[set_name] = w_set
    return windsets


def feedin_wind_sets(weather, wind_parameter_set):
    """Create a pv feed-in time series from a given weather data set and a
    set of pvlib parameter sets. The result of every parameter set will be a
    column in the resulting DataFrame.

    Parameters
    ----------
    weather : pandas.DataFrame
        Weather data set. See module header.
    wind_parameter_set : dict
        Parameter sets can be created using `create_windpowerlib_sets()`.

    Returns
    -------
    pandas.DataFrame

    """
    df = pd.DataFrame()
    for turbine in wind_parameter_set.values():
        mc = feedin_windpowerlib(weather, turbine)
        df[turbine['name'].replace(' ', '_')] = mc
    return df


def feedin_windpowerlib(weather, turbine, installed_capacity=1):
    """Use the windpowerlib to generate normalised feedin time series.

    Parameters
    ----------
    turbine : dict
        Parameters of the wind turbine (hub height, diameter of the rotor,
        identifier of the turbine to get cp-series, nominal power).
    weather : pandas.DataFrame
        Weather data set. See module header.
    installed_capacity : float
        Overall installed capacity for the given wind turbine. The installed
        capacity is set to 1 by default for normalised time series.

    Returns
    -------
    pandas.DataFrame

    """
    wpp = WindTurbine(**turbine)
    modelchain_data = cfg.get_dict('windpowerlib')
    mc = ModelChain(wpp, **modelchain_data)
    mcwpp = mc.run_model(weather)
    return mcwpp.power_output.div(turbine['nominal_power']).multiply(
        installed_capacity)


if __name__ == "__main__":
    tools.logger.define_logging()
    import os
    y = 2012
    set_name = 'M_LG290G3__I_ABB_MICRO_025_US208'
    hd_file = pd.HDFStore(os.path.join(
        cfg.get('paths', 'feedin'), 'coastdat', str(y), 'solar',
        cfg.get('feedin', 'file_pattern').format(year=y, type='solar',
                                                 set_name=set_name)),
        mode='r')
    print(hd_file['/A1113109'].sum())
    hd_file.close()
    # cfg = config.get_configuration()
    # normalised_feedin_by_region(cfg, overwrite=True)
