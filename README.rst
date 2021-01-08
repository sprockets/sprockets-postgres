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
Configuration of sprockets-postgres is done by using of environment variables or
`tornado.web.Application.settings <https://www.tornadoweb.org/en/stable/web.html#tornado.web.Application.settings>`_
dictionary. The `sprockets_postgres.ApplicationMixin <https://sprockets-postgres.readthedocs.io/en/stable/application.html>`_
will use configuration as applied to the settings dictionary, falling back to the
environment variable if the value is not set in the dictionary. Keys in the
settings dictionary are lowercase, and if provided as environment variables,
are uppercase.

The following table details the available configuration options:

+---------------------------------+--------------------------------------------------+------+-----------+
| Variable                        | Definition                                       | Type | Default   |
+=================================+==================================================+======+===========+
| ``postgres_url``                | The PostgreSQL URL to connect to                 | str  |           |
+---------------------------------+--------------------------------------------------+------+-----------+
| ``postgres_max_pool_size``      | Maximum connection count to Postgres per backend | int  | ``10``    |
+---------------------------------+--------------------------------------------------+------+-----------+
| ``postgres_min_pool_size``      | Minimum or starting pool size.                   | int  | ``1``     |
+---------------------------------+--------------------------------------------------+------+-----------+
| ``postgres_connection_timeout`` | The maximum time in seconds to spend attempting  | int  | ``10``    |
|                                 | to create a new connection.                      |      |           |
+---------------------------------+--------------------------------------------------+------+-----------+
| ``postgres_connection_ttl``     | Time-to-life in seconds for a pooled connection. | int  | ``300``   |
+---------------------------------+--------------------------------------------------+------+-----------+
| ``postgres_query_timeout``      | Maximum execution time for a query in seconds.   | int  | ``60``    |
+---------------------------------+--------------------------------------------------+------+-----------+
| ``postgres_hstore``             | Enable HSTORE support in the client.             | bool | ``FALSE`` |
+---------------------------------+--------------------------------------------------+------+-----------+
| ``postgres_json``               | Enable JSON support in the client.               | bool | ``FALSE`` |
+---------------------------------+--------------------------------------------------+------+-----------+
| ``postgres_uuid``               | Enable UUID support in the client.               | bool | ``TRUE``  |
+---------------------------------+--------------------------------------------------+------+-----------+

If ``postgres_url`` uses a scheme of ``postgresql+srv``, a SRV DNS lookup will be
performed and the lowest priority record with the highest weight will be selected
for connecting to Postgres.

AWS's ECS service discovery does not follow the SRV standard, but creates SRV
records. If ``postgres_url`` uses a scheme of ``aws+srv``, a SRV DNS lookup will be
performed and the URL will be constructed containing all host and port combinations
in priority and weighted order, utilizing `libpq's supoprt <https://www.postgresql.org/docs/12/libpq-connect.html>`_
for multiple hosts in a URL.

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
