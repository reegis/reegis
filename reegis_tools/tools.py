# -*- coding: utf-8 -*-

"""Code snippets without context.

Copyright (c) 2016-2018 Uwe Krien <uwe.krien@rl-institut.de>

SPDX-License-Identifier: GPL-3.0-or-later
"""
__copyright__ = "Uwe Krien <uwe.krien@rl-institut.de>"
__license__ = "GPLv3"


# Python libraries
import os
import logging

# External libraries
import requests
from shapely.wkt import loads as wkt_loads

# oemof packages
from oemof.tools import logger

import reegis_tools.geometries as geometries


def postgis2shapely(postgis):
    geom = list()
    for geo in postgis:
        geom.append(wkt_loads(geo))
    return geom


def download_file(filename, url, overwrite=False):
    """
    Check if file exist and download it if necessary.

    Parameters
    ----------
    filename : str
        Full filename with path.
    url : str
        Full URL to the file to download.
    overwrite : boolean (default False)
        If set to True the file will be downloaded even though the file exits.
    """
    if not os.path.isfile(filename) or overwrite:
        if overwrite:
            logging.warning("File {0} will be overwritten.".format(filename))
        else:
            logging.warning("File {0} not found.".format(filename))
        logging.warning("Try to download it from {0}.".format(url))
        req = requests.get(url)
        with open(filename, 'wb') as fout:
            fout.write(req.content)
        logging.info("Downloaded from {0} and copied to '{1}'.".format(
            url, filename))
        r = req.status_code
    else:
        r = 1
    return r


def convert_shp2csv(infile, outfile):
    logging.info("Converting {0} to {1}.".format(infile, outfile))
    geo = geometries.Geometry()
    df = geo.load(fullname=infile).get_df()
    df.loc[df.KLASSENNAM == 'FL_Vattenfall', 'KLASSENNAM'] = 'FL_Vattenfall_1'
    df.loc[df.KLASSENNAM == 'FL_Vattenfall_2', 'STIFT'] = 229
    df.to_csv(outfile)


if __name__ == "__main__":
    logger.define_logging()
    inf = '/home/uwe/chiba/Promotion/Statstik/Fernwaerme/Fernwaerme_2007/district_heat_blocks_mit_Vattenfall_1_2.shp'
    outf = '/home/uwe/git_local/reegis/berlin_hp/berlin_hp/data/static/map_district_heating_areas_berlin.csv'
    convert_shp2csv(inf, outf)
