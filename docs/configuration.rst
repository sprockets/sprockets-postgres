Configuration
=============
:py:mod:`sprockets-postgres <sprockets_postgres>` is configured via environment variables. The following table
details the configuration options and their defaults.

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
