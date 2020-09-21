from disaggregator import data, spatial, temporal
from reegis import geometries as geo, config as cfg
import pandas as pd
import logging
import os


def get_nutslist_for_regions(regions):
    """
    Parameters
    ----------
    regions = Geodataframe
        Geodataframe containing the geometry where NUTS-regions should be mapped to

    Returns: DataFrame
        List of nuts3 regions for all zones in the overall geometry
    -------
    """
    # Fetch NUTS3-geometries from disaggregator database
    nuts3_disaggregator = data.database_shapes()

    # Transform CRS System to match reegis geometries
    nuts_centroid = nuts3_disaggregator.centroid.to_crs(4326)

    # Match NUTS3-regions with federal states
    nuts_geo = geo.spatial_join_with_buffer(
        nuts_centroid, regions, "fs", limit=0
    )

    # Create dictionary with lists of all NUTS3-regions for each state
    mapped_nuts = pd.DataFrame(index=regions.index, columns=["nuts"])

    for zone in regions.index:
        mapped_nuts.loc[zone, "nuts"] = list(
            nuts_geo.loc[nuts_geo["fs"] == zone].index
        )

    return mapped_nuts


def get_demandregio_hhload_by_NUTS3_profile(year, region_pick, method="SLP"):
    """
    Parameters
    ----------
    year : int
        Year of interest
    region_pick : list
        Selected regions in NUTS-3 format
    method : string
        Chosen method to generate temporal profile, either 'SLP' or 'ZVE'

    Returns: pd.DataFrame
        Dataframe containing yearly household load for selection
    -------
    """

    if method == "SLP":
        elc_consumption_hh_spattemp = data.elc_consumption_HH_spatiotemporal(
            year=year
        )
        df = elc_consumption_hh_spattemp[region_pick]

    elif method == "ZVE":
        logging.warning("Can be lengthy for larger lists")
        list_result = []
        sum_load = data.elc_consumption_HH_spatial(year=year)
        for reg in region_pick:
            elc_consumption_hh_spattemp_zve = (
                temporal.make_zve_load_profiles(year=year, reg=reg)
                * sum_load[reg]
            )
            list_result.append(elc_consumption_hh_spattemp_zve)
        df = pd.concat(list_result, axis=1, sort=False)

    else:
        raise ValueError("Chosen method is not valid")

    return df


def get_demandregio_electricity_consumption_by_nuts3(year, region_pick=None):
    """
    Parameters
    ----------
    year : int
        Year of interest, so far only 2015 and 2016 are valid inputs
    region_pick : list
        Selected regions in NUTS-3 format, if None function will return demand for all regions

    Returns: pd.DataFrame
        Dataframe containing aggregated yearly load (households, CTS and industry) for selection
    -------
    """
    if region_pick is None:
        region_pick = data.database_shapes().index  # Select all NUTS3 Regions

    fn_pattern = "elc_consumption_by_nuts3_{year}.csv".format(year=year)
    fn = os.path.join(cfg.get("paths", "disaggregator"), fn_pattern)

    if not os.path.isfile(fn):
        # Works unfortunately just for 2015, 2016 due to limited availability of householdpower
        data.cfg["base_year"] = year
        ec_hh = (
            spatial.disagg_households_power(
                by="households", weight_by_income=True
            ).sum(axis=1)
            * 1000
        )
        ec_CTS_detail = spatial.disagg_CTS_industry(
            sector="CTS", source="power", use_nuts3code=True
        )
        ec_CTS = ec_CTS_detail.sum()
        ec_industry_detail = spatial.disagg_CTS_industry(
            sector="industry", source="power", use_nuts3code=True
        )
        ec_industry = ec_industry_detail.sum()

        ec_sum = pd.concat([ec_hh, ec_CTS, ec_industry], axis=1)
        ec_sum.columns = ["households", "CTS", "industry"]
        ec_sum.to_csv(fn)
        ec_sel = ec_sum.loc[region_pick]

    else:
        ec_sum = pd.read_csv(fn)
        ec_sum.set_index("Unnamed: 0", drop=True, inplace=True)
        ec_sel = ec_sum.loc[region_pick]

    return ec_sel


def get_household_heatload_by_NUTS3(
    year, region_pick, how="top-down", weight_by_income="True"
):

    """
    Parameters
    ----------
    year : int
        Year of interest
    region_pick : list
        Selected regions in NUTS-3 format
    how : string
        Method of disaggreagtion - can be "top-down" or "bottom-up" - top-down recommended
    weight_by_income : bool
        Choose whether heat demand shall be weighted by household income

    Returns: pd.DataFrame
        Dataframe containing yearly household load for selection
    -------
    """
    # Abweichungen in den Jahresmengen bei bottom-up
    data.cfg["base_year"] = year
    qdem_temp = spatial.disagg_households_heatload_DB(
        how="top-down", weight_by_income=weight_by_income
    )
    qdem_temp = qdem_temp.sum(axis=1)
    df = qdem_temp[region_pick]

    return df


def get_CTS_heatload(year, region_pick):
    """
    Parameters
    ----------
    year : int
        Year of interest
    region_pick : list
        Selected regions in NUTS-3 format

    Returns: pd.DataFrame
        Dataframe containing yearly heat CTS heat consumption by NUTS-3 region
    -------
    """

    # Define year of interest
    data.cfg["base_year"] = year
    # Get gas consumption of defined year and divide by gas-share in end energy use for heating
    heatload_hh = data.gas_consumption_HH().sum() / 0.47
    # Multiply with CTS heatload share, Assumption: Share is constant because heatload mainly depends on wheather
    heatload_CTS = 0.37 * heatload_hh  # Verhältnis aus dem Jahr 2017
    # Calculate CTS gas consumption by economic branch and NUTS3-region
    gc_CTS = spatial.disagg_CTS_industry(
        sector="CTS", source="gas", use_nuts3code=True
    )
    # Sum up the gas consumption per NUTS3-region
    sum_gas_CTS = gc_CTS.sum().sum()
    # Calculate scaling factor
    inc_fac = heatload_CTS / sum_gas_CTS
    # Calculate CTS heatload: Assumption: Heatload correlates strongly with gas consumption
    gc_CTS_new = gc_CTS.multiply(inc_fac)
    # Select heatload of NUTS3-regions of interest
    gc_CTS_combined = gc_CTS_new.sum()
    df = gc_CTS_combined[region_pick]

    return df


def get_industry_heating_hotwater(year, region_pick):
    """
    Parameters
    ----------
    year : int
        Year of interest
    region_pick : list
        Selected regions in NUTS-3 format

    Returns: pd.DataFrame
        Dataframe containing yearly industry heat consumption by NUTS-3 region
    -------
    """

    # Define year of interest
    data.cfg["base_year"] = year
    # Get gas consumption of defined year and divide by gas-share in end energy use for heating
    heatload_hh = data.gas_consumption_HH().sum() / 0.47
    # Multiply with industries heatload share, Assumption: Share is constant because heatload mainly depends on wheather
    heatload_industry = 0.089 * heatload_hh  # Verhältnis aus dem Jahr 2017
    # Calculate industry gas consumption by economic branch and NUTS3-region
    gc_industry = spatial.disagg_CTS_industry(
        sector="industry", source="gas", use_nuts3code=True
    )
    # Sum up the gas consumption per NUTS3-region
    sum_gas_industry = gc_industry.sum().sum()
    # Calculate scaling factor
    inc_fac = heatload_industry / sum_gas_industry
    # Calculate indsutries heatload: Assumption: Heatload correlates strongly with gas consumption
    gc_industry_new = gc_industry.multiply(inc_fac)
    gc_industry_combined = gc_industry_new.sum()
    # Select heatload of NUTS3-regions of interest
    df = gc_industry_combined[region_pick]

    return df


def get_industry_CTS_process_heat(year, region_pick):
    """
    Parameters
    ----------
    year : int
        Year of interest
    region_pick : list
        Selected regions in NUTS-3 format

    Returns: pd.DataFrame
        Dataframe containing yearly industry heat consumption by NUTS-3 region
    -------
    """

    # Select year
    data.cfg["base_year"] = year
    # Get industrial gas consumption by NUTS3
    gc_industry = spatial.disagg_CTS_industry(
        sector="industry", source="gas", use_nuts3code=True
    )
    sum_gas_industry = gc_industry.sum().sum()
    # Calculate factor of process heat consumption to gas consumption.
    # Assumption: Process heat demand correlates with gas demand
    inc_fac = (515 + 42) * 1e6 / sum_gas_industry
    # Calculate process heat with factor
    ph_industry = gc_industry.multiply(inc_fac)
    ph_industry_combined = ph_industry.sum()
    # Select process heat consumptions for NUTS3-Regions of interest
    df = ph_industry_combined[region_pick]

    return df


def get_combined_heatload_for_region(year, region_pick=None):
    """
    Parameters
    ----------
    year : int
        Year of interest, so far only 2015 and 2016 are valid inputs
    region_pick : list
        Selected regions in NUTS-3 format, if None function will return demand for all regions

    Returns: pd.DataFrame
        Dataframe containing aggregated yearly low temperature heat demand (households, CTS, industry) as well
        as high temperature heat demand (ProcessHeat) for selection
    -------
    """
    if region_pick is None:
        nuts3_index = data.database_shapes().index  # Select all NUTS3 Regions

    fn_pattern = "heat_consumption_by_nuts3_{year}.csv".format(year=year)
    fn = os.path.join(cfg.get("paths", "disaggregator"), fn_pattern)

    if not os.path.isfile(fn):
        tmp0 = get_household_heatload_by_NUTS3(
            year, nuts3_index
        )  # Nur bis 2016
        tmp1 = get_CTS_heatload(year, nuts3_index)  # 2015 - 2035 (projection)
        tmp2 = get_industry_heating_hotwater(year, nuts3_index)
        tmp3 = get_industry_CTS_process_heat(year, nuts3_index)

        df_heating = pd.concat([tmp0, tmp1, tmp2, tmp3], axis=1)
        df_heating.columns = ["Households", "CTS", "Industry", "ProcessHeat"]
        df_heating.to_csv(fn)

    else:
        df_heating = pd.read_csv(fn)
        df_heating.set_index("nuts3", drop=True, inplace=True)

    return df_heating


def aggregate_heat_by_region(regions, year=2015, heat_data=None):
    """
    Parameters
    ----------
    regions: GeoDataFrame
        Geodataframe with Polygon(s) to which NUTS3-heat-demand should be mapped
    year : int
        Year of interest, so far only 2015 and 2016 are valid inputs
    region_pick : list
        Selected regions in NUTS-3 format, if None function will return demand for all regions

    Returns: pd.DataFrame
        Dataframe containing aggregated yearly low temperature heat demand (households, CTS, industry) as well
        as high temperature heat demand (ProcessHeat) for region selection
    -------
    """
    if heat_data is None:
        heat_data = get_combined_heatload_for_region(year)

    agg_heat = pd.DataFrame(
        index=regions.index, columns=["lt-heat", "ht-heat"]
    )
    nuts3_list = get_nutslist_for_regions(regions)

    for zone in regions.index:
        idx = nuts3_list.loc[zone]["nuts"]
        agg_heat.loc[zone]["lt-heat"] = (
            heat_data["Households"] + heat_data["CTS"] + heat_data["Industry"]
        )[idx].sum()
        agg_heat.loc[zone]["ht-heat"] = heat_data["ProcessHeat"][idx].sum()

    return agg_heat


def aggregate_power_by_region(regions, year, elc_data=None):
    """
    Parameters
    ----------
    regions: GeoDataFrame
        Geodataframe with Polygon(s) to which NUTS3-power-demand should be mapped
    year : int
        Year of interest, so far only 2015 and 2016 are valid inputs
    region_pick : list
        Selected regions in NUTS-3 format, if None function will return demand for all regions

    Returns: pd.DataFrame
        Dataframe containing aggregated yearly power demand (households, CTS and industry) for region selection
    -------
    """
    if elc_data is None:
        elc_data = get_demandregio_electricity_consumption_by_nuts3(year)

    agg_power = pd.DataFrame(
        index=regions.index, columns=["households", "CTS", "industry"]
    )
    nuts3_list = get_nutslist_for_regions(regions)

    for zone in regions.index:
        idx = nuts3_list.loc[zone]["nuts"]
        agg_power.loc[zone]["households"] = elc_data["households"][idx].sum()
        agg_power.loc[zone]["CTS"] = elc_data["CTS"][idx].sum()
        agg_power.loc[zone]["industry"] = elc_data["industry"][idx].sum()

    return agg_power


if __name__ == "__main__":
    pass
