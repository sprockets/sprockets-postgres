Example Web Application
=======================
The following code provides a simple example for using the

.. code-block:: python
    
    import sprockets.http
    import sprockets_postgres as postgres
    from sprockets.http import app


    class RequestHandler(postgres.RequestHandlerMixin,
                         web.RequestHandler):

        GET_SQL = """\
        SELECT foo_id, bar, baz, qux
          FROM public.foo
         WHERE foo_id = %(foo_id)s;"""

        async def get(self, foo_id: str) -> None:
            result = await self.postgres_execute(self.GET_SQL, {'foo_id': foo_id})
            await self.finish(result.row)


    class Application(postgres.ApplicationMixin, app.Application):
        """
        The ``ApplicationMixin`` provides the foundation for the
        ``RequestHandlerMixin`` to properly function and will automatically
        setup the pool to connect to PostgreSQL and will shutdown the connections
        cleanly when the application stops.

        """


    def make_app(**settings):
        return Application([
           web.url(r'/foo/(?P<foo_id>.*)', FooRequestHandler)
        ], **settings)


    if __name__ == '__main__':
        sprockets.http.run(make_app)
