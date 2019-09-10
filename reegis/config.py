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
FILES = []

# Path of the package that imports this package.
try:
    IMPORTER = os.path.dirname(sys.modules['__main__'].__file__)
except AttributeError:
    IMPORTER = None


def get_ini_filenames(additional_paths=None, use_importer=True, local=True):
    paths = []
    files = []

    paths.append(os.path.join(os.path.dirname(__file__)))
    if additional_paths is not None:
        paths.extend(additional_paths)
    if IMPORTER is not None and use_importer is True:
        paths.append(IMPORTER)
    local_reegis = os.path.join(os.path.expanduser("~"), '.reegis')
    if os.path.isdir(local_reegis) and local is True:
        paths.append(local_reegis)

    for p in paths:
        for f in os.listdir(p):
            if f[-4:] == '.ini':
                files.append(os.path.join(p, f))
    return files


def add_config_files(files=None, paths=None):
    """

    Parameters
    ----------
    files : list
        A list of .ini files.
    paths : list
        A list of paths where ini files can be found.

    """
    if files is None:
        files = []
    if paths is not None:
        for p in paths:
            for f in os.listdir(p):
                if f[-4:] == '.ini':
                    files.append(os.path.join(p, f))
    global FILES
    FILES.extend(files)
    cfg.read(files)
    set_reegis_paths(paths)


def main():
    pass


def init(files=None, paths=None, **kwargs):
    """Read config file(s).

    Parameters
    ----------
    files : str or list or None
        Absolute path to config file (incl. filename)
    paths : list
        List of paths where it is searched for .ini files.
    """
    if files is None:
        files = get_ini_filenames(paths, **kwargs)
    global FILES
    FILES = files
    cfg.read(files)
    global _loaded
    _loaded = True
    set_reegis_paths(paths)


def has_option(section, option):
    return cfg.has_option(section, option)


def has_section(section):
    return cfg.has_section(section)


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


def get_dict_list(section, string=False):
    """Returns the values of a section as dictionary
    """
    if not _loaded:
        init(FILE)
    dc = {}
    for key, value in cfg.items(section):
        dc[key] = get_list(section, key, string=string)
    return dc


def tmp_set(section, key, value):
    if not _loaded:
        init(FILE)
    return cfg.set(section, key, value)


def extend_path(basic_path, new_dir):
    pathname = os.path.join(basic_path, new_dir)
    if not os.path.isdir(pathname):
        os.makedirs(pathname)
    return pathname


def set_reegis_paths(paths=None):
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

    if (IMPORTER != os.path.join(os.path.dirname(__file__))
            and IMPORTER is not None):
        importer_name = IMPORTER.split(os.sep)[-1]
        cfg.set('paths', '{0}'.format(importer_name), IMPORTER)

    if paths is not None:
        for p in paths:
            package_name = p.split(os.sep)[-1]
            cfg.set('paths', '{0}'.format(package_name), p)

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
