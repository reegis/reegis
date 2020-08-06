import glaes as gl
import pandas as pd
import os
from disaggregator import data
import geopandas as gpd
from reegis import demand_disaggregator
from reegis import config as cfg


def save_nuts3_to_geojson(path):
    # Apparently this doesn't work with geopandas 0.8.0 but with geopandas 0.4.1
    nuts3_gdf = data.database_shapes()

    if not os.path.isdir(path):
        os.mkdir(path)

    for i, r in nuts3_gdf.iterrows():
        gs = gpd.GeoSeries()
        gs[i] = r["geometry"]
        gs.crs = "epsg:25832"
        # gs.to_file(os.path.join(path, str(i) + '.geojson'), driver='GeoJSON')
        gs.to_file(path + "/" + str(i) + ".geojson", driver="GeoJSON")


def calculate_wind_area(region):
    # Choose Region
    ecWind = gl.ExclusionCalculator(
        region, srs=3035, pixelSize=100, limitOne=False
    )

    # Define Exclusion Criteria
    selExlWind = {
        "access_distance": (5000, None),
        # "agriculture_proximity": (None, 50 ),
        # "agriculture_arable_proximity": (None, 50 ),
        # "agriculture_pasture_proximity": (None, 50 ),
        # "agriculture_permanent_crop_proximity": (None, 50 ),
        # "agriculture_heterogeneous_proximity": (None, 50 ),
        "airfield_proximity": (None, 1760),  # Diss WB
        "airport_proximity": (None, 5000),  # Diss WB
        "connection_distance": (10000, None),
        # "dni_threshold": (None, 3.0 ),
        "elevation_threshold": (1500, None),
        # "ghi_threshold": (None, 3.0 ),
        "industrial_proximity": (None, 250),  # Diss Wingenbach / UBA 2013
        "lake_proximity": (None, 0),
        "mining_proximity": (None, 100),
        "ocean_proximity": (None, 10),
        "power_line_proximity": (None, 120),  # Diss WB
        "protected_biosphere_proximity": (None, 5),  # UBA 2013
        "protected_bird_proximity": (None, 200),  # UBA 2013
        "protected_habitat_proximity": (None, 5),  # UBA 2013
        "protected_landscape_proximity": (None, 5),  # UBA 2013
        "protected_natural_monument_proximity": (None, 200),  # UBA 2013
        "protected_park_proximity": (None, 5),  # UBA 2013
        "protected_reserve_proximity": (None, 200),  # UBA 2013
        "protected_wilderness_proximity": (None, 200),  # UBA 2013
        "camping_proximity": (None, 900),  # UBA 2013)
        # "touristic_proximity": (None, 800),
        # "leisure_proximity": (None, 1000),
        "railway_proximity": (None, 250),  # Diss WB
        "river_proximity": (None, 5),  # Abweichung vom standardwert (200)
        "roads_proximity": (None, 80),  # Diss WB
        "roads_main_proximity": (None, 80),  # Diss WB
        "roads_secondary_proximity": (None, 80),  # Diss WB
        # "sand_proximity": (None, 5 ),
        "settlement_proximity": (None, 600),  # Diss WB
        "settlement_urban_proximity": (None, 1000),
        "slope_threshold": (10, None),
        # "slope_north_facing_threshold": (3, None ),
        "wetland_proximity": (None, 5),  # Diss WB / UBA 2013
        "waterbody_proximity": (None, 5),  # Diss WB / UBA 2013
        "windspeed_100m_threshold": (
            None,
            5.5,
        ),  # Wert angepasst. Bei Nabenhöhe >100m realistisch?
        # "windspeed_50m_threshold": (None, 4.5),
        "woodland_proximity": (
            None,
            0,
        ),  # Abweichung vom standardwert (300) / Diss WB
        "woodland_coniferous_proximity": (
            None,
            0,
        ),  # Abweichung vom standardwert (300)
        "woodland_deciduous_proximity": (
            None,
            0,
        ),  # Abweichung vom standardwert (300)
        "woodland_mixed_proximity": (
            None,
            0,
        ),  # Abweichung vom standardwert (300)
    }

    # Apply selected exclusion criteria
    # for key in selExlWind:
    #     ecWind.excludePrior(pr[key], value=ecWind.typicalExclusions[key])

    for key in selExlWind.keys():
        ecWind.excludePrior(key, value=selExlWind[key])

    area = ecWind.areaAvailable

    return area


def calc_wind_pv_areas(path):
    nuts3_gdf = data.database_shapes()
    list_filenames = list()
    suitable_area = pd.DataFrame(
        index=nuts3_gdf.index, columns=["wind_area", "pv_area"]
    )

    for nuts3_name in nuts3_gdf.index:
        list_filenames.append(path + "/" + nuts3_name + ".geojson")

    # list_filenames = list_filenames[0:20]

    for n in list_filenames:
        idx = n[len(path) + 1 : len(path) + 6]
        area_wind = calculate_wind_area(n)
        suitable_area["wind_area"][idx] = area_wind

    for n in list_filenames:
        idx = n[len(path) + 1 : len(path) + 6]
        area_pv = calculate_pv_area(n)
        suitable_area["pv_area"][idx] = area_pv

    return suitable_area


def calculate_pv_area(region):
    # Quaschning, Volker. Systemtechnik einer klimaverträglichen Elektrizitätsversorgung in Deutschland für
    # das 21. Jahrhundert. Düsseldorf, 2000
    # Fraunhofer Institut für Windenergie und Energiesystemtechnik (IWES). Vorstudie zur Integration großer
    # Anteile Photovoltaik in die elektrische Energieversorgung – Studie im Auftrag des BSW - Bundesverband
    # Solarwirtschaft e.V. – ergänzte Fassung vom 29.05.2012. 2012
    # WG: 818.31 km² und NWG: 698 km²  Gesamt: 1516 km²

    # Divide Potential by eligible area in Germany
    share_pv = 1516 / 43677

    # Intialise ExclusionCalculator object
    ecPV = gl.ExclusionCalculator(
        region, srs=3035, pixelSize=100, limitOne=False
    )
    # Perform exclusion
    ecPV.excludePrior("settlement_proximity", value=0)
    ecPV.excludePrior("settlement_urban_proximity", value=0)

    # Calculate area eligible for pv
    area_total = (float(ecPV.maskPixels) / 100) * 1e6  # Fläche in m²
    area_excluded = ecPV.areaAvailable
    area_available = area_total - area_excluded
    area_pv = area_available * share_pv

    return area_pv


def get_pv_wind_areas_by_nuts3(create_geojson=False):
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
    path = os.path.join(cfg.get("paths", "GLAES"), "nuts3_geojson")

    if create_geojson:
        save_nuts3_to_geojson(path)

    fn = os.path.join(cfg.get("paths", "GLAES"), "suitable_area_wind_pv.csv")

    if not os.path.isfile(fn):
        suitable_area = calc_wind_pv_areas(path)
        suitable_area.to_csv(fn)
    else:
        suitable_area = pd.read_csv(fn)
        suitable_area.set_index("nuts3", drop=True, inplace=True)

    return suitable_area


def get_pv_wind_capacity_potential_by_nuts3(
    pwind_per_m2=8, psolar_per_m2=200, suitable_area=None
):

    fn = os.path.join(cfg.get("paths", "GLAES"), "suitable_area_wind_pv.csv")

    if suitable_area is None:
        if not os.path.isfile(fn):
            # Calculate PV and Wind areas
            path = os.path.join(cfg.get("paths", "GLAES"), "nuts3_geojson")
            if not os.path.isdir(path):
                mkjson = True
                suitable_area = get_pv_wind_areas_by_nuts3(create_geojson=True)
            else:
                suitable_area = get_pv_wind_areas_by_nuts3()

        else:
            # Read PV and Wind areas from file
            suitable_area = pd.read_csv(fn)
            suitable_area.set_index("nuts3", drop=True, inplace=True)

    # Calculate maximum installable capacity with assumptions
    P_max_wind = suitable_area["wind_area"] * (
        pwind_per_m2 / 1e6
    )  # Convert W to MW
    P_max_pv = suitable_area["pv_area"] * (
        psolar_per_m2 / 1e6
    )  # Convert W to MW

    P_max = pd.DataFrame(index=suitable_area.index, columns=["P_wind", "P_pv"])
    P_max["P_wind"] = P_max_wind
    P_max["P_pv"] = P_max_pv

    # Store results in reegis directory if it does not exist
    outfile = os.path.join(
        cfg.get("paths", "GLAES"), "wind_pv_capacity_per_NUTS3.csv"
    )
    if not os.path.isfile(outfile):
        P_max.to_csv(outfile)

    return P_max


def aggregate_capacity_by_region(regions, P_max=None):

    fn = os.path.join(
        cfg.get("paths", "GLAES"), "wind_pv_capacity_per_NUTS3.csv"
    )

    if P_max is None:
        if not os.path.isfile(fn):
            # Calculate PV and Wind potential
            P_max = get_pv_wind_capacity_potential_by_nuts3()

        else:
            # Read PV and Wind potential from file
            P_max = pd.read_csv(fn)
            P_max.set_index("nuts3", drop=True, inplace=True)

    agg_capacity = pd.DataFrame(
        index=regions.index, columns=["P_wind", "P_pv"]
    )
    nuts3_list = demand_disaggregator.get_nutslist_for_regions(regions)

    for zone in regions.index:
        idx = nuts3_list.loc[zone]["nuts"]
        agg_capacity.loc[zone]["P_wind"] = P_max["P_wind"][idx].sum()
        agg_capacity.loc[zone]["P_pv"] = P_max["P_pv"][idx].sum()

    return agg_capacity


if __name__ == "__main__":
    pass
