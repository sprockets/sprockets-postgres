RequestHandler Mixin
====================
The :class:`~sprockets_postgres.RequestHandlerMixin` is a Tornado
:class:`tornado.web.RequestHandler` mixin that provides easy to use
functionality for interacting with PostgreSQL.

.. autoclass:: sprockets_postgres.RequestHandlerMixin
    :members:
    :undoc-members:
    :private-members:
    :member-order: bysource

The :class:`~sprockets_postgres.StatusRequestHandler` is a Tornado
:class:`tornado.web.RequestHandler` that can be used for application health
monitoring. If the Postgres connection is unavailable, it will report the
API as unavailable and return a 503 status code.

.. autoclass:: sprockets_postgres.StatusRequestHandler
    :members:
    :undoc-members:
    :private-members:
    :member-order: bysource
