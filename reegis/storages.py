# -*- coding: utf-8 -*-

"""Processing a list of power plants in Germany.

Copyright (c) 2016-2019 Uwe Krien <krien@uni-bremen.de>

SPDX-License-Identifier: MIT
"""
__copyright__ = "Uwe Krien <krien@uni-bremen.de>"
__license__ = "MIT"


# Python libraries
import os

# External libraries
import pandas as pd
import numpy as np
from shapely.geometry import Point

# internal modules
from reegis import config as cfg
from reegis import geometries


def lat_lon2point(df):
    """Create shapely point object of latitude and longitude."""
    return Point(df['Wikipedia', 'longitude'], df['Wikipedia', 'latitude'])


def pumped_hydroelectric_storage_by_region(regions, year, name=None):
    """
    Fetch pumped hydroelectric storage by region. This function is based on
    static data. Please adapt the source file for years > 2018.

    Parameters
    ----------
    regions : geopandas.geoDataFrame
    name : str or None

    Returns
    -------
    pd.DataFrame

    Examples
    --------
    >>> federal_states = geometries.get_federal_states_polygon()
    >>> phes = pumped_hydroelectric_storage_by_region(
    ...     federal_states, 2002, 'federal_states')
    >>> int(phes.turbine.sum())
    5533
    >>> phes = pumped_hydroelectric_storage_by_region(
    ...     federal_states, 2018, 'federal_states')
    >>> int(phes.turbine.sum())
    6593
    >>> int(phes.energy.sum())
    37841
    >>> round(phes.loc['BW'].pump_eff, 2)
    0.86
    """
    phes_raw = pd.read_csv(os.path.join(cfg.get('paths', 'static_sources'),
                                        cfg.get('storages', 'hydro_storages')),
                           header=[0, 1]).sort_index(1)

    phes_raw = phes_raw.loc[phes_raw['Wikipedia', 'commissioning'] < year]
    phes_raw = phes_raw.loc[phes_raw['Wikipedia', 'ensured_operation'] >= year]

    phes = phes_raw['dena'].copy()

    # add geometry from wikipedia
    phes_raw = phes_raw[phes_raw['Wikipedia', 'longitude'].notnull()]
    phes['geom'] = (phes_raw.apply(lat_lon2point, axis=1))

    # add energy from ZFES because dena values seem to be corrupted
    phes['energy'] = phes_raw['ZFES', 'energy']
    phes['name'] = phes_raw['ZFES', 'name']

    phes['efficiency'] = phes['efficiency'].fillna(
        cfg.get('storages', 'default_efficiency'))

    # remove storages that do not have an entry for energy capacity
    phes = phes[phes.energy.notnull()]

    # create a GeoDataFrame with geom column
    gphes = geometries.create_geo_df(phes)

    if name is None:
        name = '{0}_region'.format(cfg.get('init', 'map'))

    gphes = geometries.spatial_join_with_buffer(
        gphes, regions, name=name, limit=0)

    # create turbine and pump efficiency from overall efficiency (square root)
    # multiply the efficiency with the capacity to group with "sum()"
    gphes['pump_eff'] = np.sqrt(gphes.efficiency) * gphes.pump
    gphes['turbine_eff'] = (
            np.sqrt(gphes.efficiency) * gphes.turbine)

    phes = gphes.groupby(name).sum()

    # divide by the capacity to get the efficiency and remove overall
    # efficiency
    phes['pump_eff'] = phes.pump_eff / phes.pump
    phes['turbine_eff'] = phes.turbine_eff / phes.turbine
    del phes['efficiency']

    return phes


if __name__ == "__main__":
    pass
