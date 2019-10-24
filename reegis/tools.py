# -*- coding: utf-8 -*-

"""Code snippets without context.

Copyright (c) 2016-2019 Uwe Krien <krien@uni-bremen.de>

SPDX-License-Identifier: MIT
"""
__copyright__ = "Uwe Krien <krien@uni-bremen.de>"
__license__ = "MIT"


# Python libraries
import os
import logging

# External libraries
import requests


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


if __name__ == "__main__":
    pass
