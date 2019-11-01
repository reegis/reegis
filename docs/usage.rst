Basic information
~~~~~~~~~~~~~~~~~

There are two types of data functions in reegis. The high level functions
contain `by_region` functions, that make it possible to get data for a
specific region set.
Basic functions provide useful functions to get a pandas.DataFrame from
a specific data source. These functions may return more or less raw data.
Using pandas.DataFrame it is still pretty easy to process these tables to your
own needs.

The region set used in the following examples is the
federal state set. This set contains 17 regions (16 federal states plus one
offshore region).

.. highlight:: python

.. code-block::

    from reegis import geometries
    geometries.get_federal_states_polygon()

See the :py:func:`~reegis.dev.figures.fig_federal_states_polygons` to get the
full code of this figure.

.. image:: _files/federal_states_region_plot.svg
  :width: 400
  :alt: Federal states regions
  :align: center