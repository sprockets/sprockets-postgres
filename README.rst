Sprockets Postgres
==================
An set of mixins and classes for interacting with PostgreSQL using asyncio in
Tornado / sprockets.http applications using aiopg.

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

+---------------------------------+--------------------------------------------------+-----------+
| Variable                        | Definition                                       | Default   |
+=================================+==================================================+===========+
| ``POSTGRES_URL``                | The PostgreSQL URL to connect to                 |           |
+---------------------------------+--------------------------------------------------+-----------+
| ``POSTGRES_MAX_POOL_SIZE``      | Maximum connection count to Postgres per backend | ``10``    |
+---------------------------------+--------------------------------------------------+-----------+
| ``POSTGRES_MIN_POOL_SIZE``      | Minimum or starting pool size.                   | ``1``     |
+---------------------------------+--------------------------------------------------+-----------+
| ``POSTGRES_CONNECTION_TIMEOUT`` | The maximum time in seconds to spend attempting  | ``10``    |
|                                 | to create a new connection.                      |           |
+---------------------------------+--------------------------------------------------+-----------+
| ``POSTGRES_CONNECTION_TTL``     | Time-to-life in seconds for a pooled connection. | ``300``   |
+---------------------------------+--------------------------------------------------+-----------+
| ``POSTGRES_QUERY_TIMEOUT``      | Maximum execution time for a query in seconds.   | ``60``    |
+---------------------------------+--------------------------------------------------+-----------+
| ``POSTGRES_HSTORE``             | Enable HSTORE support in the client.             | ``FALSE`` |
+---------------------------------+--------------------------------------------------+-----------+
| ``POSTGRES_JSON``               | Enable JSON support in the client.               | ``FALSE`` |
+---------------------------------+--------------------------------------------------+-----------+
| ``POSTGRES_UUID``               | Enable UUID support in the client.               | ``TRUE``  |
+---------------------------------+--------------------------------------------------+-----------+

If ``POSTGRES_URL`` uses a scheme of ``postgresql+srv``, a SRV DNS lookup will be
performed and the lowest priority record with the highest weight will be selected
for connecting to Postgres.

AWS's ECS service discovery does not follow the SRV standard, but creates SRV
records. If ``POSTGRES_URL`` uses a scheme of ``aws+srv``, a SRV DNS lookup will be
performed using the correct format for ECS service discovery. The lowest priority
record with the highest weight will be selected for connecting to Postgres.

Requirements
------------
- `aiodns <https://github.com/saghul/aiodns>`_
- `aiopg <https://aioboto3.readthedocs.io/en/latest/>`_
- `sprockets.http <https://sprocketshttp.readthedocs.io/en/master/>`_
- `Tornado <https://tornadoweb.org>`_

Version History
---------------
Available at https://sprockets-postgres.readthedocs.org/en/latest/history.html

.. |Version| image:: https://img.shields.io/pypi/v/sprockets-postgres.svg?
   :target: https://pypi.python.org/pypi/sprockets-postgres

.. |Status| image:: https://github.com/sprockets/sprockets-postgres/workflows/Testing/badge.svg?
   :target: https://github.com/sprockets/sprockets-postgres/actions?workflow=Testing
   :alt: Build Status

.. |Coverage| image:: https://img.shields.io/codecov/c/github/sprockets/sprockets-postgres.svg?
   :target: https://codecov.io/github/sprockets/sprockets-postgres?branch=master

.. |License| image:: https://img.shields.io/pypi/l/sprockets-postgres.svg?
   :target: https://sprockets-postgres.readthedocs.org
