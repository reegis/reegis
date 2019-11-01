# -*- coding: utf-8 -*-

"""Processing a list of power plants in Germany.

Copyright (c) 2016-2019 Uwe Krien <krien@uni-bremen.de>

SPDX-License-Identifier: MIT
"""
__copyright__ = "Uwe Krien <krien@uni-bremen.de>"
__license__ = "MIT"


# Python libraries
import os
import logging

# External libraries
import pandas as pd
import numpy as np

# Internal modules
from reegis import config as cfg
from reegis import opsd
from reegis import energy_balance
from reegis import geometries as geo


MSG = "File '{0}' does not exist. Will create it from source files."


def patch_offshore_wind(orig_df, columns=None):
    """
    Patch the power plants table with additional data of offshore wind parks.

    Examples
    --------
    >>> df = pd.DataFrame()
    >>> int(patch_offshore_wind(df)['capacity'].sum())
    5332
    """
    if columns is None:
        df = pd.DataFrame()
    else:
        df = pd.DataFrame(columns=columns)

    offsh = pd.read_csv(
        os.path.join(cfg.get('paths', 'static_sources'),
                     cfg.get('static_sources', 'patch_offshore_wind')),
        header=[0, 1], index_col=[0])

    offsh = offsh.loc[offsh['reegis', 'com_year'].notnull(), 'reegis']
    for column in offsh.columns:
        df[column] = offsh[column]
    df['decom_year'] = 2050
    df['decom_month'] = 12
    df['energy_source_level_1'] = 'Renewable energy'
    df['energy_source_level_2'] = 'Wind'
    df['energy_source_level_3'] = 'Offshore'
    goffsh = geo.create_geo_df(df)

    offsh_df = pd.DataFrame(goffsh)

    new_cap = offsh_df['capacity'].sum()

    if len(orig_df) > 0:
        old_cap = orig_df.loc[orig_df['technology'] == 'Offshore',
                              'capacity'].sum()
        # Remove Offshore technology from power plant table
        orig_df = orig_df.loc[orig_df['technology'] != 'Offshore']
    else:
        old_cap = 0

    patched_df = pd.DataFrame(pd.concat([orig_df, offsh_df],
                                        ignore_index=True, sort=True))
    logging.warning(
        "Offshore wind is patched. {0} MW were replaced by {1} MW".format(
            old_cap, new_cap))
    return patched_df


def pp_opsd2reegis(offshore_patch=True, filename_in=None, filename_out=None,
                   hydro_storage_fix=True):
    """
    Adapt opsd power plants to a more generalised reegis API with a reduced
    number of columns. In most case you should use the higher functions,
    which include this function.

    Parameters
    ----------
    offshore_patch : bool
        Will overwrite the offshore wind power plants with own data set if set
        to True (default=True).
    hydro_storage_fix : bool
        Rename "fuel" of Pumped hydro storage from Hydro to Storage if set to
        True (default: True).
    filename_in : str or None
        Alternative filename for the input file. In most case the default case
        is the best choice.
    filename_out : str or None
        Alternative filename for the output file. In most case the default case
        is the best choice.

    Returns
    -------
    str : Filename of the stored file.

    Examples
    --------
    >>> filename_out = os.path.join(cfg.get('paths', 'powerplants'),
    ...                             cfg.get('powerplants', 'reegis_pp'))
    >>> if not os.path.isfile(filename_out):
    ...     filename = pp_opsd2reegis()  # doctest: +SKIP
    """
    version_name = cfg.get('opsd', 'version_name')

    if filename_in is None:
        opsd_path = cfg.get('paths_pattern', 'opsd').format(
            version=version_name)
        filename_in = os.path.join(opsd_path, cfg.get('opsd', 'opsd_prepared'))
    if filename_out is None:
        filename_out = os.path.join(cfg.get('paths', 'powerplants'),
                                    cfg.get('powerplants', 'reegis_pp'))
        filename_out = filename_out.format(version=version_name)

    keep_cols = {'decom_year', 'comment', 'chp', 'energy_source_level_1',
                 'thermal_capacity', 'com_year', 'com_month',
                 'chp_capacity_uba', 'energy_source_level_3', 'decom_month',
                 'geometry', 'energy_source_level_2', 'capacity', 'technology',
                 'com_year', 'efficiency'}

    string_cols = ['chp', 'comment', 'energy_source_level_1',
                   'energy_source_level_2', 'energy_source_level_3',
                   'geometry', 'technology']

    # Create opsd power plant tables if they do not exist.
    if not os.path.isfile(filename_in):
        logging.debug(MSG.format(filename_in))
        filename_in = opsd.opsd_power_plants()
    else:
        for cat in ['renewable', 'conventional']:
            try:
                pd.read_hdf(filename_in, cat)
            except KeyError:
                msg = "File '{0}' exists but key '{1}' is not present."
                logging.debug(msg.format(filename_in, cat))
                logging.debug("Will re-create file with all keys.")
                os.remove(filename_in)
                filename_in = opsd.opsd_power_plants()

    pp = {}
    for cat in ['conventional', 'renewable']:
        # Read opsd power plant tables
        pp[cat] = pd.DataFrame(pd.read_hdf(filename_in, cat))

        # Patch offshore wind energy with investigated data.
        if cat == 'renewable' and offshore_patch:
            pp[cat] = patch_offshore_wind(pp[cat], keep_cols)

        if cat == 'conventional' and hydro_storage_fix:
            pp[cat].loc[pp[cat]['technology'] == 'Pumped storage',
                        'energy_source_level_2'] = 'Storage'
            pp[cat].loc[pp[cat]['technology'] == 'Pumped storage',
                        'energy_source_level_3'] = 'Pumped storage'

        pp[cat] = pp[cat].drop(columns=set(pp[cat].columns) - keep_cols)

        # Replace 'nan' strings with nan values.
        pp[cat] = pp[cat].replace('nan', np.nan)

        # Remove lines with comments. Comments mark suspicious data.
        pp[cat] = pp[cat].loc[pp[cat].comment.isnull()]

        # Fill missing 'energy_source_level_1' values with 'unknown' and
        # the category from opsd.
        pp[cat]['energy_source_level_1'] = (
            pp[cat]['energy_source_level_1'].fillna(
                'unknown from {0}'.format(cat)))

        # Fill missing 'energy_source_level_2' values with values from
        # 'energy_source_level_1' column.
        pp[cat]['energy_source_level_2'] = (
            pp[cat]['energy_source_level_2'].fillna(
                pp[cat]['energy_source_level_1']))

    pp = pd.DataFrame(pd.concat([pp['renewable'], pp['conventional']],
                                ignore_index=True, sort=True))

    # Merge 'chp_capacity_uba' into 'thermal_capacity' column.
    pp['thermal_capacity'] = pp['thermal_capacity'].fillna(
        pp['chp_capacity_uba'])
    del pp['chp_capacity_uba']

    # Convert all values to strings in string-columns
    pp[string_cols] = pp[string_cols].astype(str)

    # Store power plant table to hdf5 file.
    pp.to_hdf(filename_out, 'pp', mode='w')

    logging.info("Reegis power plants based on opsd stored in {0}".format(
        filename_out))
    return filename_out


def add_capacity_in(pp):
    """Add a column to the conventional power plants to make it possible to
    calculate an average efficiency for the summed up groups.
    """
    # Calculate the inflow capacity for power plants with an efficiency value.
    pp['capacity_in'] = pp['capacity'].div(pp['efficiency'])

    # Sum up the valid in/out capacities to calculate an average efficiency
    cap_valid = pp.loc[pp['efficiency'].notnull(), 'capacity'].sum()
    cap_in = pp.loc[pp['efficiency'].notnull(), 'capacity_in'].sum()

    # Set the average efficiency for missing efficiency values
    pp['efficiency'] = pp['efficiency'].fillna(
        cap_valid / cap_in)

    # Calculate the inflow for all power plants
    pp['capacity_in'] = pp['capacity'].div(pp['efficiency'])

    logging.info("'capacity_in' column added to power plant table.")
    return pp


def add_model_region_pp(pp, region_polygons, col_name, subregion=False):
    """ Add a region column to the powerplant table
    """
    # Create a geoDataFrame from power plant DataFrame.
    pp = geo.create_geo_df(pp)

    if subregion is True:
        limit = 0
    else:
        limit = 1

    # Add region names to power plant table
    logging.debug('Adding column {0} to power plant table...'.format(col_name))
    pp = pd.DataFrame(geo.spatial_join_with_buffer(pp, region_polygons,
                                                   name=col_name, limit=limit))
    pp['geometry'] = pp['geometry'].astype(str)

    logging.info(
        "Region column {0} added to power plant table.".format(col_name))
    return pp


def get_reegis_powerplants(year, path=None, filename=None, pp=None,
                           overwrite_capacity=False):
    """
    Get all reegis power plants for the given year. The function uses the
    opsd power plant file. If this file does not exist it created. In that
    case the function will take more time.

    Parameters
    ----------
    filename : str or None
        Name of the power plant hdf5 file. If None the default name of the
        config file is used (section: 'powerplants', value: 'reegis_pp').
    path : str or None
        Directory of the power plant file. If None the default path of the
        config file for power plants is used.
    pp : pd.DataFrame
        A power plant table with the reegis power plant structure.
    year : int
        Get all power plants, that a online in this year.
    overwrite_capacity : bool
        By default (False) a new column "capacity_<year>" is created. If set to
        True the old capacity column will be overwritten.

    Returns
    -------
    pd.DataFrame

    Examples
    --------
    >>> pp_reegis = get_reegis_powerplants(2012)  # doctest: +SKIP
    >>> 'capacity_2012' in pp_reegis.columns  # doctest: +SKIP
    True
    >>> pp_reegis2 = get_reegis_powerplants(
    ...     2012, overwrite_capacity=True)  # doctest: +SKIP
    >>> 'capacity_2012' in pp_reegis2.columns  # doctest: +SKIP
    False
    >>> 'capacity' in pp_reegis2.columns  # doctest: +SKIP
    True
    """
    if path is None and filename is None:
        default = True
    else:
        default = False

    if path is None:
        path = cfg.get('paths', 'powerplants')

    if filename is None:
        version = cfg.get('opsd', 'version_name')
        filename = cfg.get('powerplants', 'reegis_pp').format(version=version)

    fn = os.path.join(path, filename)

    logging.info("Get reegis power plants for {0}.".format(year))
    if default is True and not os.path.isfile(fn) and pp is None:
        logging.debug(MSG.format(fn))
        fn = pp_opsd2reegis()
    if pp is None:
        pp = pd.DataFrame(pd.read_hdf(fn, 'pp'))

    filter_columns = ['capacity_{0}']

    if 'capacity_in' in pp.columns:
        filter_columns.append('capacity_in_{0}')

    # Get all powerplants for the given year.
    # If com_month exist the power plants will be considered month-wise.
    # Otherwise the commission/decommission within the given year is not
    # considered.
    for fcol in filter_columns:
        filter_column = fcol.format(year)
        orig_column = fcol[:-4]
        c1 = (pp['com_year'] < year) & (pp['decom_year'] > year)
        pp.loc[c1, filter_column] = pp.loc[c1, orig_column]

        c2 = pp['com_year'] == year
        pp.loc[c2, filter_column] = (pp.loc[c2, orig_column] *
                                     (12 - pp.loc[c2, 'com_month']) / 12)
        c3 = pp['decom_year'] == year
        pp.loc[c3, filter_column] = (pp.loc[c3, orig_column] *
                                     pp.loc[c3, 'com_month'] / 12)

        if overwrite_capacity:
            pp[orig_column] = 0
            pp[orig_column] = pp[filter_column]
            del pp[filter_column]

    return pp


def add_regions_to_powerplants(region, column, filename=None,
                               filename_out=None, path=None, hdf_key='pp',
                               subregion=False, dump=True, pp=None):
    """
    Add a column to the power plant table with the region id of the given
    region file.

    Parameters
    ----------
    region : geoDataFrame
        A geoDataFrame with the region polygons.
    column : str
        Name of the column with the region ids.
    filename : str or None
        Name of the power plant hdf5 file e.g. 'reegis_pp.h5'.
    filename_out : str or None
        Name of the new power plant hdf5 file e.g. 'reegis_pp_region.h5'. If
        None the original file will be overwritten.
    subregion : bool
        Set to True if all region polygons together are a subregion of
        Germany. This will switch off the buffer in the spatial_join function.
    path : str or None
        Path for the files. If None the default power plant path from the
        config file is used.
    hdf_key : str
        The key of the hdf file.
    dump : bool
        If True the table is dumped to an hdf5 file.
    pp : pd.DataFrame or None
        It is possible to pass a power plant table otherwise a stored table
        will be used.

    Returns
    -------

    Examples
    --------
    >>> region_polygons = geo.load(path=cfg.get('paths', 'geometry'),
    ...                            filename='region_polygons_de21_wiese.csv')
    >>> pp = add_regions_to_powerplants(
    ...     region_polygons, 'de_21_wiese', 'reegis_pp.h5',
    ...     filename_out='reegis_pp_regions.h5')  # doctest: +SKIP

    """
    if path is None and filename is None:
        default = True
    else:
        default = False

    if path is None:
        path = cfg.get('paths', 'powerplants')

    if filename is None:
        version = cfg.get('opsd', 'version_name')
        filename = cfg.get('powerplants', 'reegis_pp').format(version=version)

    if filename_out is None:
        filename_out = filename

    fn = os.path.join(path, filename)

    if default and pp is None and not os.path.isfile(fn):
        logging.debug(MSG.format(fn))
        fn = pp_opsd2reegis()

    if pp is None:
        pp = pd.DataFrame(pd.read_hdf(fn, hdf_key))

    if column not in pp:
        pp = add_model_region_pp(pp, region, column, subregion=subregion)

    if 'capacity_in' not in pp:
        pp = add_capacity_in(pp)

    if dump:
        fn = os.path.join(path, filename_out)
        pp.to_hdf(fn, 'pp', mode='w')

    return pp


def calculate_chp_share_and_efficiency(eb, fix_total=True):
    """Efficiency and fuel share of combined heat and power plants (chp) and
    heat plants (hp) from conversion balance.

    Examples
    --------
    >>> cb = energy_balance.get_transformation_balance(2014)
    >>> efficiency = calculate_chp_share_and_efficiency(cb, fix_total=False)
    >>> round(efficiency['NI']['hp'], 4)
    0.9888
    >>> round(efficiency['BB']['hp'], 4)
    inf
    >>> efficiency = calculate_chp_share_and_efficiency(cb)
    >>> round(efficiency['NI']['hp'], 4)
    0.9888
    >>> round(efficiency['BB']['hp'], 4)
    0.8885
    """
    row_chp = 'Heizkraftwerke der allgemeinen Versorgung (nur KWK)'
    row_hp = 'Heizwerke'
    row_total = 'Insgesamt'

    regions = list(eb.index.get_level_values(0).unique())
    eta = {}
    rows = ['Heizkraftwerke der allgemeinen Versorgung (nur KWK)',
            'Heizwerke']

    if fix_total:
        eb.loc[eb.total == 0, 'total'] = eb.loc[eb.total == 0].sum(axis=1)

    for region in regions:
        eta[region] = {}
        in_chp = eb.loc[region, 'input', row_chp]
        in_hp = eb.loc[region, 'input', row_hp]
        elec_chp = eb.loc[(region, 'output', row_chp), 'electricity']
        heat_chp = eb.loc[(region, 'output', row_chp),
                          'district heating']
        heat_hp = eb.loc[(region, 'output', row_hp),
                         'district heating']
        heat_total = eb.loc[(region, 'output', row_total),
                            'district heating']
        end_total_heat = eb.loc[(region, 'usage', 'Endenergieverbrauch'),
                                'district heating']
        eta[region]['sys_heat'] = end_total_heat / heat_total

        eta[region]['hp'] = float(heat_hp / in_hp.total)
        eta[region]['heat_chp'] = heat_chp / in_chp.total
        eta[region]['elec_chp'] = elec_chp / in_chp.total

        eta[region]['fuel_share'] = eb.loc[region, 'input', rows].div(
            eb.loc[region, 'input', rows].total.sum(), axis=0)

    return eta


def get_chp_share_and_efficiency_states(year):
    """
    Get the efficiency for chp and heat plants from the conversion balance for
    a specific year (keys: heat_chp, elec_chp, hp).

    Get the share of the heat producing plant from the conversion balance
    (key: fuel_share)

    Examples
    --------
    >>> df = get_chp_share_and_efficiency_states(2014)
    >>> round(df['BB']['heat_chp'], 2)
    0.52
    >>> round(df['BB']['elec_chp'], 2)
    0.26
    >>> round(df['BB']['hp'], 2)
    0.89
    >>> round(df['BB']['fuel_share'].loc[('BB', 'input'), 'total'], 2)
    Heizkraftwerke der allgemeinen Versorgung (nur KWK)    0.85
    Heizwerke                                              0.15
    Name: total, dtype: float64
    >>> round(df['BB']['fuel_share']['gas'].sum(), 2)
    0.29
    """
    conversion_blnc = energy_balance.get_transformation_balance(year)
    return calculate_chp_share_and_efficiency(conversion_blnc)


def get_powerplants_by_region(region, year, name, grouped=True):
    """
    Get all powerplants of a region grouped by fuel for a given year.

    Parameters
    ----------
    region : geopandas.geoDataFrame or None
    year : int
    name : str
    grouped : bool

    Notes
    -----
    A table with the name pattern reegis_pp_{name}.h5 will be dumped. If you
    are sure your file exists you can pass region=None.
    You may want to use geometries.load() to import a region CSV.

    Returns
    -------
    pd.DataFrame

    Examples
    --------
    >>> geometries = geo.get_federal_states_polygon()  # doctest: +SKIP
    >>> my_year = 2014  # doctest: +SKIP
    >>> my_pp = get_powerplants_by_region(
    ...     geometries, my_year, 'federal_states')  # doctest: +SKIP

    """
    version = cfg.get('opsd', 'version_name')
    filename = cfg.get('powerplants', 'reegis_pp')
    filename = filename.format(version=str(version) + '_' + str(name))

    path = cfg.get('paths', 'powerplants')

    fn = os.path.join(path, filename)

    basefile = cfg.get('powerplants', 'reegis_pp').format(version=version)

    if not os.path.isfile(os.path.join(path, basefile)):
        pp_opsd2reegis(filename_out=os.path.join(path, basefile))

    if not os.path.isfile(fn) and region is not None:
        add_regions_to_powerplants(region, name, path=path, filename=basefile,
                                   filename_out=filename, subregion=True)

    pp = get_reegis_powerplants(year, path=path, filename=filename)

    if grouped is True:
        pp = pp.groupby([name, 'energy_source_level_2']).sum()
        rm_columns = ['com_month', 'com_year', 'decom_month', 'decom_year',
                      'efficiency']
        pp.drop(rm_columns, axis=1, inplace=True)

    return pp


if __name__ == "__main__":
    pass
