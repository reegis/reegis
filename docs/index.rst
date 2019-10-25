.. reegis documentation master file

.. image:: https://travis-ci.org/reegis/reegis.svg?branch=master
    :target: https://travis-ci.org/reegis/reegis

.. image:: https://coveralls.io/repos/github/reegis/reegis/badge.svg?branch=master
    :target: https://coveralls.io/github/reegis/reegis?branch=master

.. image:: https://img.shields.io/lgtm/grade/python/g/reegis/reegis.svg?logo=lgtm&logoWidth=18
    :target: https://lgtm.com/projects/g/reegis/reegis/context:python

.. image:: https://img.shields.io/lgtm/alerts/g/reegis/reegis.svg?logo=lgtm&logoWidth=18
    :target: https://lgtm.com/projects/g/reegis/reegis/alerts/


Introduction
=============

The reegis repository provides tools to fetch, prepare and organise input data for heat and power models. At the moment the focus is on the territory of Germany but some tools can be used for european models as well.


Most tools use spatial data and can be used for arbitrary regions.

 * Feed-in time series using the HZG [coastdat2](https://www.earth-syst-sci-data.net/6/147/2014/) weather data set and the libraries [windpowerlib](https://github.com/wind-python/windpowerlib) and [pvlib](https://github.com/pvlib/pvlib-python).
 * Demand time series based on [OPSD](https://github.com/Open-Power-System-Data/national_generation_capacity), [openEgo](https://github.com/openego) and oemof demandlib
 * Powerplants based on [OPSD](https://github.com/Open-Power-System-Data).
 * Integration of open data from the german geo-data-platform of the  [BKG](http://www.geodatenzentrum.de/geodaten/gdz_rahmen.gdz_div?gdz_spr=deu&gdz_akt_zeile=5&gdz_anz_zeile=1&gdz_unt_zeile=0&gdz_user_id=0) and the energy ministry [BMWI](http://www.bmwi.de/Navigation/EN/Home/home.html).
 * Using prepared energy balances from Germany's federal states.


.. toctree::
   :maxdepth: 2
   :glob:

   getting_started
   usage
   reegis


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

