High level functions
~~~~~~~~~~~~~~~~~~~~

Power plants
============

Get the capacity of powerplants for given regions and a specific year. Use
the pandas functions to process the result. The code below will show a typical
plot with the capacity for every federal state by fuel for the year 2014.

.. code-block:: python

    from matplotlib import pyplot as plt
    geometries = geo.get_federal_states_polygon()
    year = 2014
    my_pp = get_powerplants_by_region(geometries, year, 'federal_states')
    column = 'capacity_{0}'.format(year)
    my_pp[column].unstack().plot(kind='bar', stacked=True)
    plt.show()

To validate the function the results have been compared to data from the
Federal Network Agency (BNetzA). The following plot shows the results of reegis
on the left and the data from the BNetzA on the right.

.. image:: _files/compare_power_plants_reegis_bnetza.svg
  :width: 700
  :align: center

Inhabitants
+++++++++++