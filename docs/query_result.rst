Query Result
============
A :class:`~sprockets_postgres.QueryResult` instance is created for every query
and contains the count of rows effected by the query and either the ``row`` as
a :class:`dict` or ``rows`` as a list of :class:`dict`.  For queries that do
not return any data, both ``row`` and ``rows`` will be :const:`None`.

.. autoclass:: sprockets_postgres.QueryResult
    :members:
