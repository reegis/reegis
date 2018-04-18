# -*- coding: utf-8 -*-

"""Reegis geometry tools.

Copyright (c) 2016-2018 Uwe Krien <uwe.krien@rl-institut.de>

SPDX-License-Identifier: GPL-3.0-or-later
"""
__copyright__ = "Uwe Krien <uwe.krien@rl-institut.de>"
__license__ = "GPLv3"


# Python libraries
import os
import logging
import configparser as cp
import sys


FILE = None
cfg = cp.RawConfigParser()
cfg.optionxform = str
_loaded = False

# Path of the package that imports this package.
importer = os.path.dirname(sys.modules['__main__'].__file__)


def get_ini_filenames():
    paths = list()
    files = list()

    paths.append(os.path.join(os.path.dirname(__file__)))
    paths.append(importer)
    paths.append(os.path.join(os.path.expanduser("~"), '.oemof'))

    for p in paths:
        for f in os.listdir(p):
            if f[-4:] == '.ini':
                files.append(os.path.join(p, f))
    return files


def main():
    pass


def init(file):
    """Read config file(s).

    Parameters
    ----------
    file : str or list or None
        Absolute path to config file (incl. filename)
    """
    if file is None:
        file = get_ini_filenames()
    cfg.read(file)
    global _loaded
    _loaded = True
    set_reegis_paths()


def get(section, key):
    """Returns the value of a given key in a given section.
    """
    if not _loaded:
        init(FILE)
    try:
        return cfg.getint(section, key)
    except ValueError:
        try:
            return cfg.getfloat(section, key)
        except ValueError:
            try:
                return cfg.getboolean(section, key)
            except ValueError:
                try:
                    value = cfg.get(section, key)
                    if value == 'None':
                        value = None
                    return value
                except ValueError:
                    logging.error(
                        "section {0} with key {1} not found in {2}".format(
                            section, key, FILE))
                    return cfg.get(section, key)


def get_list(section, parameter, sep=',', string=False):
    """Returns the values (separated by sep) of a given key in a given
    section as a list.
    """
    try:
        my_list = get(section, parameter).split(sep)
        my_list = [x.strip() for x in my_list]

    except AttributeError:
        if string is True:
            my_list = list((cfg.get(section, parameter),))
        else:
            my_list = list((get(section, parameter),))
    return my_list


def get_dict(section):
    """Returns the values of a section as dictionary
    """
    if not _loaded:
        init(FILE)
    dc = {}
    for key, value in cfg.items(section):
        dc[key] = get(section, key)
    return dc


# def set(section, key, value):
#     if not _loaded:
#         init(FILE)
#     return cfg.set(section, key, value)


def extend_path(basic_path, new_dir):
    pathname = os.path.join(basic_path, new_dir)
    if not os.path.isdir(pathname):
        os.makedirs(pathname)
    return pathname


def set_reegis_paths():
    # initialise de21 configuration
    logging.info('Loading reegis configuration....')

    # Set default paths for 'basic' and 'data' if set to 'None' in the ini-file
    basicpath = get('root_paths', 'package_data')
    if basicpath is None:
        basicpath = os.path.join(os.path.dirname(__file__), 'data')
        logging.debug("Set default path for basic path: {0}".format(basicpath))
    cfg.set('paths', 'package_data', basicpath)

    datapath = get('root_paths', 'local_root')
    if datapath is None:
        datapath = os.path.join(os.path.expanduser("~"), 'reegis')
        logging.debug("Set default path for data path: {0}".format(datapath))
    cfg.set('paths', 'local_root', datapath)

    if importer != os.path.join(os.path.dirname(__file__)):
        importer_name = importer.split(os.sep)[-1]
        cfg.set('paths', '{0}'.format(importer_name), importer)

    # *************************************************************************
    # ********* Set sub-paths according to ini-file ***************************
    # *************************************************************************
    for key in get_dict('path_names').keys():
        names = get_list('path_names', key)
        pathname = os.path.join(get('paths', names[0]), *names[1:])
        cfg.set('paths', key, pathname)
        os.makedirs(pathname, exist_ok=True)

    if not cfg.has_section('paths_pattern'):
        cfg.add_section('paths_pattern')

    for key in get_dict('path_pattern_names').keys():
        names = get_list('path_pattern_names', key)
        pathname = os.path.join(get('paths', names[0]), *names[1:])
        cfg.set('paths_pattern', key, pathname)


if __name__ == "__main__":
    print(get('paths', 'package_data'))
