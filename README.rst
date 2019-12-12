.. image:: https://travis-ci.org/reegis/reegis.svg?branch=master
    :target: https://travis-ci.org/reegis/reegis

.. image:: https://coveralls.io/repos/github/reegis/reegis/badge.svg?branch=master
    :target: https://coveralls.io/github/reegis/reegis?branch=master

.. image:: https://img.shields.io/lgtm/grade/python/g/reegis/reegis.svg?logo=lgtm&logoWidth=18
    :target: https://lgtm.com/projects/g/reegis/reegis/context:python

.. image:: https://img.shields.io/lgtm/alerts/g/reegis/reegis.svg?logo=lgtm&logoWidth=18
    :target: https://lgtm.com/projects/g/reegis/reegis/alerts/

.. image:: https://img.shields.io/badge/automatic%20code%20style-black-blueviolet
    :target: https://black.readthedocs.io/en/stable/

.. image:: https://img.shields.io/badge/licence-MIT-blue
    :target: https://spdx.org/licenses/MIT.html

.. image:: https://zenodo.org/badge/DOI/10.5281/zenodo.3572316.svg
   :target: https://doi.org/10.5281/zenodo.3572316


The reegis repository provides tools to fetch, prepare and organise input data for heat and power models. At the moment the focus is on the territory of Germany but some tools can be used for european models as well.

Installation
============

On a Linux Debian system you can use the following command to solve all
requirements beforehand.

.. code-block::

    sudo apt-get install python3-dev proj-bin libproj-dev libgeos-dev python3-tk libspatialindex-dev virtualenv

For other Linux systems you may have to adapt the package names. For Windows
systems you can just start pip install and fix occurring errors step by step.

The reegis library is designed for Python 3 and tested on Python >= 3.6. We highly recommend to use virtual environments.
Please see the `installation page <http://oemof.readthedocs.io/en/stable/installation_and_setup.html>`_ of the oemof documentation for complete instructions on how to install python and a virtual environment on your operating system.

If you have a working Python 3 environment, use pypi to install the latest reegis version:

.. code-block::

    pip install reegis


Documentation
=============

The `reegis documentation <https://reegis.readthedocs.io/en/latest/>`_ is powered by readthedocs.

Go to the `download page <http://readthedocs.org/projects/reegis/downloads/>`_ to download different versions and formats (pdf, html, epub) of the documentation.


Contributing
==============

We are warmly welcoming all who want to contribute to the reegis library. If
you frequently use one of the data sources you may contact me and help to
maintain the packages. Don't be shy, even if you are a beginner.


Citing reegis
========================

Go to the `Zenodo page of reegis <https://doi.org/10.5281/zenodo.3572316>`_ to find the DOI of your version. To cite all reegis versions use:

.. image:: https://zenodo.org/badge/DOI/10.5281/zenodo.3572316.svg
   :target: https://doi.org/10.5281/zenodo.3572316

License
============

Copyright (c) 2019 Uwe Krien, nesnoj

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.