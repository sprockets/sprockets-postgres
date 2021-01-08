Configuration
=============
Configuration of :py:mod:`sprockets-postgres <sprockets_postgres>` is done by
using of environment variables or :py:attr:`tornado.web.Application.settings`
dictionary. The :py:class:`sprockets_postgres.ApplicationMixin` will use configuration
as applied to the settings dictionary, falling back to the environment variable
if the value is not set in the dictionary. Keys in the settings dictionary are
lowercase, and if provided as environment variables, are uppercase.  For example
to set the Postgres URL in a :py:attr:`tornado.web.Application.settings`,
you'd do the following:

.. code-block::

    settings = {'postgres_url': 'postgresql://postgres@localhost:5432/postgres'}
    app = web.Application([routes], settings=settings)

and as an environment variable:

.. code-block::

    POSTGRES_URL=postgresql://postgres@localhost:5432/postgres


Available Settings
------------------

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

