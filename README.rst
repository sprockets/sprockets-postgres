Sprockets Postgres
==================
An asynchronous Postgres client mixin for Tornado applications

|Version| |Status| |Coverage| |License|

Installation
------------
``sprockets-postgres`` is available on the Python package index and is installable via pip:

.. code:: bash

    pip install sprockets-postgres

Documentation
-------------
Documentation is available at `sprockets-postgres.readthedocs.io <https://sprockets-postgres.readthedocs.io>`_.

Configuration
-------------
The following table details the environment variable configuration options:

+---------------------------------+--------------------------------------------------+---------------------------------+
| Variable                        | Definition                                       | Default                         |
+=================================+==================================================+=================================+
| ``PGSQL_URL``                   | The PostgreSQL URL to connect to                 | ``postgresql://localhost:5432`` |
+---------------------------------+--------------------------------------------------+---------------------------------+
| ``POSTGRES_MAX_POOL_SIZE``      | Maximum connection count to Postgres per backend | ``0`` (Unlimited                |
+---------------------------------+--------------------------------------------------+---------------------------------+
| ``POSTGRES_MIN_POOL_SIZE``      | Minimum or starting pool size.                   | ``1``                           |
+---------------------------------+--------------------------------------------------+---------------------------------+
| ``POSTGRES_CONNECTION_TIMEOUT`` | The maximum time in seconds to spend attempting  | ``10``                          |
|                                 | to create a new connection.                      |                                 |
+---------------------------------+--------------------------------------------------+---------------------------------+
| ``POSTGRES_CONNECTION_TTL``     | Time-to-life in seconds for a pooled connection. | ``300``                         |
+---------------------------------+--------------------------------------------------+---------------------------------+
| ``POSTGRES_QUERY_TIMEOUT``      | Maximum execution time for a query in seconds.   | ``60``                          |
+---------------------------------+--------------------------------------------------+---------------------------------+
| ``POSTGRES_HSTORE``             | Enable HSTORE support in the client.             | ``FALSE``                       |
+---------------------------------+--------------------------------------------------+---------------------------------+
| ``POSTGRES_JSON``               | Enable JSON support in the client.               | ``FALSE``                       |
+---------------------------------+--------------------------------------------------+---------------------------------+
| ``POSTGRES_UUID``               | Enable UUID support in the client.               | ``TRUE``                        |
+---------------------------------+--------------------------------------------------+---------------------------------+


Requirements
------------
- `aiopg <https://aioboto3.readthedocs.io/en/latest/>`_
- `sprockets.http <https://sprocketshttp.readthedocs.io/en/master/>`_
- `Tornado <https://tornadoweb.org>`_

Version History
---------------
Available at https://sprockets-postgres.readthedocs.org/en/latest/history.html

.. |Version| image:: https://img.shields.io/pypi/v/sprockets-postgres.svg?
   :target: http://badge.fury.io/py/sprockets-postgres

.. |Status| image:: https://img.shields.io/travis/sprockets/sprockets-postgres.svg?
   :target: https://travis-ci.org/sprockets/sprockets-postgres

.. |Coverage| image:: https://img.shields.io/codecov/c/github/sprockets/sprockets-postgres.svg?
   :target: https://codecov.io/github/sprockets/sprockets-postgres?branch=master

.. |License| image:: https://img.shields.io/pypi/l/sprockets-postgres.svg?
   :target: https://sprockets-postgres.readthedocs.org
