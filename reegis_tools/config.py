# -*- coding: utf-8 -*-
"""
Created on Fri Sep  5 12:26:40 2014

:module-author: steffen
:filename: config.py


This module provides a high level layer for reading and writing config files.
There must be a file called "config.ini" in the root-folder of the project.
The file has to be of the following structure to be imported correctly.

# this is a comment \n
# the file structure is like: \n
 \n
[netCDF] \n
RootFolder = c://netCDF \n
FilePrefix = cd2_ \n
 \n
[mySQL] \n
host = localhost \n
user = guest \n
password = root \n
database = znes \n
 \n
[SectionName] \n
OptionName = value \n
Option2 = value2 \n


"""
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
    """
    Read config file

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
    """
    returns the value of a given key of a given section of the main
    config file.

    :param section: the section.
    :type section: str.
    :param key: the key.
    :type key: str.

    :returns: the value which will be casted to float, int or boolean.
    if no cast is successful, the raw string will be returned.

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


def get_list(section, parameter):
    try:
        my_list = get(section, parameter).split(',')
        my_list = [x.strip() for x in my_list]

    except AttributeError:
        my_list = list((get(section, parameter),))
    return my_list


def get_dict(section):
    """

    Parameters
    ----------
    section : str

    Returns
    -------
    dict
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
