"""
Processing a list of power plants in Germany.

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
import pandas as pd

# oemof libraries
from oemof.tools import logger

# Internal modules
import reegis_tools.config as cfg
import reegis_tools.geometries as geo
import reegis_tools.opsd as opsd


def prepare_power_plants(category, overwrite=False):
    """

    Parameters
    ----------
    category
    overwrite

    Returns
    -------

    """
    # Define file and path pattern for power plant file.
    spatial_file_name = os.path.join(
        cfg.get('paths', category),
        cfg.get('powerplants', 'spatial_file_pattern').format(
            cat=category))

    # If the power plant file does not exist, download and prepare it.
    if not os.path.isfile(spatial_file_name):
        df = opsd.load_opsd_file(category, overwrite, prepared=True)
        pp = geo.Geometry('{0} power plants'.format(category), df=df)
        pp = spatial_preparation_power_plants(pp)
        pp.df.to_csv(spatial_file_name)

    # Fetch the powerplant file.
    df = pd.read_csv(os.path.join(
        cfg.get('paths', category),
        cfg.get('powerplants', 'spatial_file_pattern').format(
            cat=category)), index_col=[0])

    # Create a Geometry object of power plants
    pp = geo.Geometry('{0} power plants'.format(category), df=df)

    # Filter powerplants by the given year.
    start = datetime.datetime.now()
    c1 = (pp.df['com_year'] < 2012) & (pp.df['decom_year'] > 2012)
    pp.df.loc[c1, 'grp_cap'] = pp.df.loc[c1, 'electrical_capacity']

    c2 = pp.df['com_year'] == 2012
    pp.df.loc[c2, 'grp_cap'] = (pp.df.loc[c2, 'electrical_capacity'] *
                                (12 - pp.df.loc[c2, 'com_month']) / 12)

    c3 = ((pp.df['com_year'] < 2013) & (pp.df['decom_year'] > 2012) &
          (pp.df['com_year'] < 2013))

    # TESTS!!!
    print(pp.df.loc[c1, ['electrical_capacity', 'grp_cap']].sum())
    print(pp.df.loc[c2, ['electrical_capacity', 'grp_cap']].sum())
    print(pp.df.loc[c3, ['electrical_capacity', 'grp_cap']].sum())
    print(datetime.datetime.now() - start)
    # print(my.sort_values('com_year'))
    print(datetime.datetime.now() - start)


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

    # Add column with region names of the model_region
    model_region = geo.Geometry('model region')
    model_region.load(cfg.get('paths', 'geometry'),
                      cfg.get('geometry', 'region_polygon'))

    pp.gdf = geo.spatial_join_with_buffer(pp, model_region)

    # Add column with name of the federal state (Bayern, Berlin,...)
    federal_states = geo.Geometry('federal states')
    federal_states.load(cfg.get('paths', 'geometry'),
                        cfg.get('geometry', 'federalstates_polygon'))
    pp.gdf = geo.spatial_join_with_buffer(pp, federal_states)

    # Add column with coastdat id
    coastdat = geo.Geometry('coastdat2')
    coastdat.load(cfg.get('paths', 'geometry'),
                  cfg.get('geometry', 'coastdatgrid_polygon'))
    pp.gdf = geo.spatial_join_with_buffer(pp, coastdat)

    # Update DataFrame with the new content of the GeoDataFrame.
    pp.gdf2df()
    return pp


if __name__ == "__main__":
    logger.define_logging()
    prepare_power_plants('renewable', overwrite=False)
