# -*- coding: utf-8 -*-

"""Work with the scenario data.

Copyright (c) 2016-2018 Uwe Krien <uwe.krien@rl-institut.de>

SPDX-License-Identifier: GPL-3.0-or-later
"""
__copyright__ = "Uwe Krien <uwe.krien@rl-institut.de>"
__license__ = "GPLv3"


# Python libraries
import os
import logging
import calendar

# External libraries
import pandas as pd
import networkx as nx
from matplotlib import pyplot as plt

# oemof libraries
import oemof.tools.logger as logger
import oemof.solph as solph
import oemof.outputlib as outputlib
import oemof.graph as graph

# internal modules
import reegis_tools.config as cfg


class NodeDict(dict):
    __slots__ = ()

    def __setitem__(self, key, item):
        if super().get(key) is None:
            super().__setitem__(key, item)
        else:
            msg = ("Key '{0}' already exists. ".format(key) +
                   "Duplicate keys are not allowed in a node dictionary.")
            raise KeyError(msg)


class Scenario:
    def __init__(self, **kwargs):
        self.name = kwargs.get('name', 'unnamed_scenario')
        self.table_collection = kwargs.get('table_collection', {})
        self.year = kwargs.get('year', None)
        self.ignore_errors = kwargs.get('ignore_errors', False)
        self.round_values = kwargs.get('round_values', 0)
        self.filename = kwargs.get('filename', None)
        self.path = kwargs.get('path', None)
        self.model = kwargs.get('model', None)
        self.es = kwargs.get('es', self.initialise_energy_system())

    def initialise_energy_system(self):
        if calendar.isleap(self.year):
            number_of_time_steps = 8784
        else:
            number_of_time_steps = 8760

        date_time_index = pd.date_range('1/1/{0}'.format(self.year),
                                        periods=number_of_time_steps, freq='H')
        return solph.EnergySystem(timeindex=date_time_index)

    def load_excel(self, filename=None):
        if filename is not None:
            self.filename = filename
        xls = pd.ExcelFile(filename)
        for sheet in xls.sheet_names:
            self.table_collection[sheet] = xls.parse(
                sheet, index_col=[0], header=[0, 1])

    def load_csv(self, path=None):
        if path is not None:
            self.path = path
        for file in os.listdir(path):
            if file[-4:] == '.csv':
                filename = os.path.join(self.path, file)
                self.table_collection[file[:-4]] = pd.read_csv(
                    filename, index_col=[0], header=[0, 1])

    def to_excel(self, filename=None):
        if filename is not None:
            self.filename = filename
        if not os.path.isdir(os.path.dirname(self.filename)):
            os.makedirs(os.path.dirname(self.filename))
        self.path = os.path.dirname(self.filename)
        writer = pd.ExcelWriter(self.filename)
        for name, df in sorted(self.table_collection.items()):
            df.to_excel(writer, name)
        writer.save()
        logging.info("Scenario saved as excel file to {0}".format(
            self.filename))

    def to_csv(self, path):
        if path is not None:
            self.path = path
        if not os.path.isdir(self.path):
            os.makedirs(self.path)
        for name, df in self.table_collection.items():
            name = name.replace(' ', '_') + '.csv'
            filename = os.path.join(self.path, name)
            df.to_csv(filename)
        logging.info("Scenario saved as csv-collection to {0}".format(
            self.path))

    def create_nodes(self):
        pass

    def add_nodes2solph(self, es=None):
        if es is not None:
            self.es = es
        self.es.add(*self.create_nodes().values())

    def create_model(self):
        self.model = solph.Model(self.es)

    def dump_results_to_es(self):
        self.es.results['main'] = outputlib.processing.results(self.model)
        self.es.results['meta'] = outputlib.processing.meta_results(self.model)
        self.es.dump(dpath='/home/uwe', filename='berlin.reegis')
        fn = os.path.join('/home/uwe', 'berlin.reegis')
        logging.info("Results dumped to {0}.".format(fn))

    def restore_results(self):
        self.es.restore(dpath='/home/uwe', filename='berlin.reegis')

    def solve(self, with_duals=False):
        solver_name = cfg.get('general', 'solver')

        logging.info("Optimising using {0}.".format(solver_name))

        if with_duals:
            self.model.receive_duals()

        self.model.solve(solver=solver_name, solve_kwargs={'tee': True})

    def plot_nodes(self, show=None, filename=None, **kwargs):

        rm_nodes = kwargs.get('remove_nodes_with_substrings')

        g = graph.create_nx_graph(self.es, filename=filename,
                                  remove_nodes_with_substrings=rm_nodes)
        if show is True:
            draw_graph(g, **kwargs)
        return g


def check_table(table):
    if table.isnull().values.any():
        c = []
        for column in table.columns:
            if table[column].isnull().any():
                c.append(column)
        msg = "Nan Values in the following columns: {0}".format(c)
        raise ValueError(msg)


def draw_graph(grph, edge_labels=True, node_color='#AFAFAF',
               edge_color='#CFCFCF', plot=True, node_size=2000,
               with_labels=True, arrows=True, layout='neato'):
    """
    Draw a graph. This function will be removed in future versions.

    Parameters
    ----------
    grph : networkxGraph
        A graph to draw.
    edge_labels : boolean
        Use nominal values of flow as edge label
    node_color : dict or string
        Hex color code oder matplotlib color for each node. If string, all
        colors are the same.

    edge_color : string
        Hex color code oder matplotlib color for edge color.

    plot : boolean
        Show matplotlib plot.

    node_size : integer
        Size of nodes.

    with_labels : boolean
        Draw node labels.

    arrows : boolean
        Draw arrows on directed edges. Works only if an optimization_model has
        been passed.
    layout : string
        networkx graph layout, one of: neato, dot, twopi, circo, fdp, sfdp.
    """
    if type(node_color) is dict:
        node_color = [node_color.get(g, '#AFAFAF') for g in grph.nodes()]

    # set drawing options
    options = {
     'prog': 'dot',
     'with_labels': with_labels,
     'node_color': node_color,
     'edge_color': edge_color,
     'node_size': node_size,
     'arrows': arrows
    }

    # draw graph
    pos = nx.drawing.nx_agraph.graphviz_layout(grph, prog=layout)

    nx.draw(grph, pos=pos, **options)

    # add edge labels for all edges
    if edge_labels is True and plt:
        labels = nx.get_edge_attributes(grph, 'weight')
        nx.draw_networkx_edge_labels(grph, pos=pos, edge_labels=labels)

    # show output
    if plot is True:
        plt.show()


if __name__ == "__main__":
    logger.define_logging()
    pass
