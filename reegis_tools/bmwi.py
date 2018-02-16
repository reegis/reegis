# -*- coding: utf-8 -*-

""" This module is designed to download and prepare BMWI data.

Copyright (c) 2016-2018 Uwe Krien <uwe.krien@rl-institut.de>

SPDX-License-Identifier: GPL-3.0-or-later
"""
__copyright__ = "Uwe Krien <uwe.krien@rl-institut.de>"
__license__ = "GPLv3"


# Python libraries
import os
import logging

# External libraries
import pandas as pd
import requests

# Internal modules
import reegis_tools.config as cfg


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
        logging.warning("File not found. Try to download it from server.")
        req = requests.get(url)
        with open(filename, 'wb') as fout:
            fout.write(req.content)
        logging.info("Downloaded from {0} and copied to '{1}'.".format(
            url, filename))
        r = req.status_code
    else:
        r = 1
    return r


def get_bmwi_energiedaten_file():
    filename = os.path.join(cfg.get('paths', 'general'),
                            cfg.get('bmwi', 'energiedaten'))
    logging.debug("Return status from energiedaten file: {0}".format(
        download_file(filename, cfg.get('bmwi', 'url_energiedaten'))))
    return filename


def read_bmwi_sheet_7(a=False):
    filename = get_bmwi_energiedaten_file()
    if a:
        sheet = '7a'
    else:
        sheet = '7'
    fs = pd.DataFrame()
    n = 4
    while 2014 not in fs.columns:
        n += 1
        fs = pd.read_excel(filename, sheet, skiprows=n)

    # Convert first column to string
    fs['Unnamed: 0'] = fs['Unnamed: 0'].apply(str)

    # Create 'A' column with sector name (shorten the name)
    fs['A'] = fs['Unnamed: 0'].apply(
        lambda x: x.replace('nach Anwendungsbereichen ', '')
        if 'Endenergie' in x else float('nan'))
    fs['A'] = fs['A'].fillna(method='ffill')
    fs = fs[fs['A'].notnull()]
    fs['A'] = fs['A'].apply(
        lambda x: x.replace('Endenergieverbrauch in der ', ''))
    fs['A'] = fs['A'].apply(
        lambda x: x.replace('Endenergieverbrauch im ', ''))
    fs['A'] = fs['A'].apply(
        lambda x: x.replace('Endenergieverbrauch in den ', ''))
    fs['A'] = fs['A'].apply(lambda x: x.replace('Sektor ', ''))
    fs['A'] = fs['A'].apply(
        lambda x: x.replace('privaten Haushalten', 'private Haushalte'))

    # Create 'B' column with type
    fs['B'] = fs['Unnamed: 0'].apply(
        lambda x: x if '-' not in x else float('nan'))
    fs['B'] = fs['B'].fillna(method='ffill')

    fs['B'] = fs['B'].apply(lambda x: x if 'nan' not in x else float('nan'))
    fs = fs[fs['B'].notnull()]

    # Create 'C' column with fuel
    fs['C'] = fs['Unnamed: 0'].apply(lambda x: x if '-' in x else float('nan'))
    fs['C'] = fs['C'].fillna(fs['B'])

    # Delete first column and set 'A', 'B', 'C' columns to index
    del fs['Unnamed: 0']

    # Set new columns to index
    fs = fs.set_index(['A', 'B', 'C'], drop=True)
    return fs


def bmwi_re_energy_capacity():
    """Prepare the energy production and capacity table from sheet 20."""
    filename = get_bmwi_energiedaten_file()
    repp = pd.read_excel(filename, '20', skiprows=22).ix[:23]
    repp = repp.drop(repp.index[[0, 4, 8, 12, 16, 20]])
    repp['type'] = (['water'] * 3 + ['wind'] * 3 + ['bioenergy'] * 3 +
                    ['biogenic waste'] * 3 + ['solar'] * 3 + ['geothermal'] * 3)
    repp['value'] = ['energy', 'capacity', 'fraction'] * 6
    repp.set_index(['type', 'value'], inplace=True)
    del repp['Unnamed: 0']
    return repp.transpose().sort_index(1)


get_bmwi_energiedaten_file()
