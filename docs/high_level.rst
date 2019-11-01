High level functions
~~~~~~~~~~~~~~~~~~~~

.. highlight:: python

Power plants
++++++++++++

The powerplant module is based on
`OPSD <https://open-power-system-data.org/>`_.

Get the capacity of powerplants for given regions and a specific year. Use
the pandas functions to process the result. The code below will show a typical
plot with the capacity for every federal state by fuel for the year 2014.

.. code-block::

    from matplotlib import pyplot as plt
    from reegis import powerplant
    geometries = geo.get_federal_states_polygon()
    year = 2014
    my_pp = powerplant.get_powerplants_by_region(
        geometries, year, 'federal_states')
    column = 'capacity_{0}'.format(year)
    my_pp[column].unstack().plot(kind='bar', stacked=True)
    plt.show()

To validate the function the results have been compared to data from the
Federal Network Agency (BNetzA). The following plot shows the results of reegis
on the left and the data from the BNetzA on the right.

.. image:: _files/compare_power_plants_reegis_bnetza.svg
  :width: 700
  :align: center

See the :py:func:`~reegis.dev.figures.fig_powerplants` function for the
full code of the function above.

Inhabitants
+++++++++++

The inhabitants data come from the
`Federal Agency for Cartography and Geodesy (BKG) <https://gdz.bkg.bund.de/index.php/default/open-data/verwaltungsgebiete-1-250-000-mit-einwohnerzahlen-ebenen-stand-31-12-vg250-ew-ebenen-31-12.html>`_

Inhabitants date is available for about 11.400 municipalities in Germany. To
get the number of inhabitants for a polygon a map of centroids of these
municipalities is used and summed up within each polygon.

Electricity demand
++++++++++++++++++

The electricity demand is based on ENTSO-E time series provided by
`OPSD demand time series <https://github.com/Open-Power-System-Data/national_generation_capacity>`_.

For spatial distribution the `openEgo <https://github.com/openego>`_ approach
is used.

Heat demand
+++++++++++

The heat demand is based on the energy balance of the federal states.

Feedin time series
++++++++++++++++++

At the moment feed-in time series are calculated using the HZG
`coastdat2 <https://www.earth-syst-sci-data.net/6/147/2014/>`_ weather data
set. This data set is deprecated and will be replaced by the HZG OpenFred
data set using the `feedinlib <https://github.com/oemof/feedinlib>`_.

The feed-in calculations are using the
`windpowerlib <https://github.com/wind-python/windpowerlib>`_ and the
`pvlib <https://github.com/pvlib/pvlib-python>`_.
