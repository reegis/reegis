.. toctree::
   :maxdepth: 4
   :glob:

Important usage note
~~~~~~~~~~~~~~~~~~~~

Some functions may take some minutes even hours on the first run. Calculations
that need a lot of time will store the result on your hard disc so that the
next run will be a lot shorter on the same computer.

Use a logger to see the progress:

.. code-block:: python

    import logging
    logging.basicConfig(level=logging.DEBUG)

