Usage
-----

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

.. image:: _files/federal_states_region_plot.svg
  :width: 400
  :alt: Federal states regions
  :align: center

.. contents::
   :local:

.. toctree::
   :maxdepth: 3
   :glob:

High level functions
********************



Power plants
++++++++++++




Inhabitants
+++++++++++

Basic functions
***************

Energy Balance
++++++++++++++

Get the energy balance of the federal states for a given year. The data is
taken from a csv-file that is manually downloaded from the LAK page.

https://www.lak-energiebilanzen.de/eingabe-dynamisch/?a=e900

As an automatic download does not work you may have to download the file to
get the latest updates. Just rename the downloaded file to
`energy_balance_federal_states.csv` and replace the existing file in the
`data/static/` directory of the reegis package. Alternatively you can download
the file and adapt the path in the config file
(`energy_balance: energy_balance_states`) or use the config module to set a
ne path.

Usage with file in the default directory:

.. code-block::

    from reegis import energy_balance as eb
    year = 2012
    states = ['BB', 'NW']
    fuel = 'lignite (raw)'
    row = 'extraction'

    my_eb = eb.get_states_energy_balance(year)
    print(my_eb.loc[(states, row), fuel])

Usage with alternative file:

.. code-block::

    from reegis import energy_balance as eb, config as cfg
    year = 2012
    states = ['BB', 'NW']
    fuel = 'lignite (raw)'
    row = 'extraction'

    fn = '/my/path/my_file.csv'
    cfg.tmp_set('energy_balance', 'energy_balance_states', fn)
    my_eb = eb.get_states_energy_balance(year)
    print(my_eb.loc[(states, row), fuel])

If no year is passed to the function the whole table will be returned. This can
be used to show changes over the time.

.. code-block::

    from matplotlib import pyplot as plt
    fuel = 'lignite (raw)'
    eb = get_states_energy_balance()
    ax = plt.figure(figsize=(9, 5)).add_subplot(1, 1, 1)
    eb.loc[(slice(None), slice(None), 'extraction'), fuel].groupby(
        level=0).sum().plot(ax=ax)
    plt.title("Extraction of raw lignite in Germany")
    plt.xlabel('year')
    plt.ylabel('energy [TJ]')
    plt.ylim(bottom=0)
    plt.show()


.. image:: _files/energy_balance_lignite_extraction.svg
  :width: 650
  :align: center

The reason of the drop for the year is not that extraction of raw extraction
ended but that the data set for 2016 is not complete yet. So be careful with
most recent data sets and check them before use.

If you frequently work with energy balances please contact the author and help
to improve the API.
