"""
:class:`sprockets.http.app.Application` mixin for handling the connection to
Postgres and exporting functions for querying the database, getting the status,
and proving a cursor.

Automatically creates and shuts down :class:`aio.pool.Pool` on startup
and shutdown.

"""
import asyncio
import contextlib
import functools
import logging
import os
import typing
from distutils import util

import aiopg
import psycopg2
from aiopg import pool
from psycopg2 import errors, extras, extensions
from tornado import ioloop, web

LOGGER = logging.getLogger('sprockets-postgres')

DEFAULT_POSTGRES_CONNECTION_TIMEOUT = 10
DEFAULT_POSTGRES_CONNECTION_TTL = 300
DEFAULT_POSTGRES_HSTORE = 'FALSE'
DEFAULT_POSTGRES_JSON = 'FALSE'
DEFAULT_POSTGRES_MAX_POOL_SIZE = 0
DEFAULT_POSTGRES_MIN_POOL_SIZE = 1
DEFAULT_POSTGRES_QUERY_TIMEOUT = 120
DEFAULT_POSTGRES_URL = 'postgresql://localhost:5432'
DEFAULT_POSTGRES_UUID = 'TRUE'


class ApplicationMixin:
    """Application mixin for setting up the PostgreSQL client pool"""

    POSTGRES_STATUS_TIMEOUT = 3

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._postgres_pool: typing.Optional[pool.Pool] = None
        self.runner_callbacks['on_start'].append(self._postgres_setup)
        self.runner_callbacks['shutdown'].append(self._postgres_shutdown)

    @contextlib.asynccontextmanager
    async def postgres_cursor(self,
                              timeout: typing.Optional[int] = None,
                              raise_http_error: bool = True) \
            -> typing.AsyncContextManager[extensions.cursor]:
        """Return a Postgres cursor for the pool"""
        try:
            async with self._postgres_pool.acquire() as conn:
                async with conn.cursor(
                        cursor_factory=extras.RealDictCursor,
                        timeout=self._postgres_query_timeout(timeout)) as pgc:
                    yield pgc
        except (asyncio.TimeoutError,
                psycopg2.OperationalError,
                psycopg2.Error) as error:
            LOGGER.critical('Error connecting to Postgres: %s', error)
            if raise_http_error:
                raise web.HTTPError(503, 'Database Unavailable')
            raise

    async def postgres_callproc(self,
                                name: str,
                                params: typing.Union[list, tuple, None] = None,
                                timeout: typing.Optional[int] = None) \
            -> typing.Union[dict, list, None]:
        """Execute a stored procedure, specifying the name, SQL, passing in
        optional parameters.

        :param name: The stored-proc to call
        :param params: Optional parameters to pass into the function
        :param timeout: Optional timeout to override the default query timeout

        """
        async with self.postgres_cursor(timeout) as cursor:
            return await self._postgres_query(
                cursor, cursor.callproc, name, name, params)

    async def postgres_execute(self, name: str, sql: str,
                               *args,
                               timeout: typing.Optional[int] = None) \
            -> typing.Union[dict, list, None]:
        """Execute a query, specifying a name for the query, the SQL statement,
        and optional positional arguments to pass in with the query.

        Parameters may be provided as sequence or mapping and will be
        bound to variables in the operation.  Variables are specified
        either with positional ``%s`` or named ``%({name})s`` placeholders.

        :param name: The stored-proc to call
        :param sql: The SQL statement to execute
        :param timeout: Optional timeout to override the default query timeout

        """
        async with self.postgres_cursor(timeout) as cursor:
            return await self._postgres_query(
                cursor, cursor.execute, name, sql, args)

    async def postgres_status(self) -> dict:
        """Invoke from the ``/status`` RequestHandler to check that there is
         a Postgres connection handler available and return info about the
         pool.

         """
        available = True
        try:
            async with self.postgres_cursor(
                    self.POSTGRES_STATUS_TIMEOUT, False) as cursor:
                await cursor.execute('SELECT 1')
        except (asyncio.TimeoutError, psycopg2.OperationalError):
            available = False
        return {
            'available': available,
            'pool_size': self._postgres_pool.size,
            'pool_free': self._postgres_pool.freesize
        }

    async def _postgres_query(self,
                              cursor: aiopg.Cursor,
                              method: typing.Callable,
                              name: str,
                              sql: str,
                              parameters: typing.Union[dict, list, tuple]) \
            -> typing.Union[dict, list, None]:
        """Execute a query, specifying the name, SQL, passing in

        """
        try:
            await method(sql, parameters)
        except asyncio.TimeoutError as err:
            LOGGER.error('Query timeout for %s: %s',
                         name, str(err).split('\n')[0])
            raise web.HTTPError(500, reason='Query Timeout')
        except errors.UniqueViolation as err:
            LOGGER.error('Database error for %s: %s',
                         name, str(err).split('\n')[0])
            raise web.HTTPError(409, reason='Unique Violation')
        except psycopg2.Error as err:
            LOGGER.error('Database error for %s: %s',
                         name, str(err).split('\n')[0])
            raise web.HTTPError(500, reason='Database Error')
        try:
            return await self._postgres_query_results(cursor)
        except psycopg2.ProgrammingError:
            return

    @staticmethod
    async def _postgres_query_results(cursor: aiopg.Cursor) \
            -> typing.Union[dict, list, None]:
        """Invoked by self.postgres_query to return all of the query results
        as either a ``dict`` or ``list`` depending on the quantity of rows.

        This can raise a ``psycopg2.ProgrammingError`` for an INSERT/UPDATE
        without RETURNING or a DELETE. That exception is caught by the caller.

        :raises psycopg2.ProgrammingError: when there are no rows to fetch
            even though the rowcount is > 0

        """
        if cursor.rowcount == 1:
            return await cursor.fetchone()
        elif cursor.rowcount > 1:
            return await cursor.fetchall()
        return None

    @functools.lru_cache
    def _postgres_query_timeout(self,
                                timeout: typing.Optional[int] = None) -> int:
        """Return query timeout, either from the specified value or
        ``POSTGRES_QUERY_TIMEOUT`` environment variable, if set.

        Defaults to sprockets_postgres.DEFAULT_POSTGRES_QUERY_TIMEOUT.

        """
        return timeout if timeout else int(
            os.environ.get(
                'POSTGRES_QUERY_TIMEOUT',
                DEFAULT_POSTGRES_QUERY_TIMEOUT))

    async def _postgres_setup(self,
                              _app: web.Application,
                              _ioloop: ioloop.IOLoop) -> None:
        """Setup the Postgres pool of connections and log if there is an error.

        This is invoked by the Application on start callback mechanism.

        """
        url = os.environ.get('POSTGRES_URL', DEFAULT_POSTGRES_URL)
        LOGGER.debug('Connecting to PostgreSQL: %s', url)
        self._postgres_pool = pool.Pool(
            url,
            minsize=int(
                os.environ.get(
                    'POSTGRES_MIN_POOL_SIZE',
                    DEFAULT_POSTGRES_MIN_POOL_SIZE)),
            maxsize=int(
                os.environ.get(
                    'POSTGRES_MAX_POOL_SIZE',
                    DEFAULT_POSTGRES_MAX_POOL_SIZE)),
            timeout=int(
                os.environ.get(
                    'POSTGRES_CONNECT_TIMEOUT',
                    DEFAULT_POSTGRES_CONNECTION_TIMEOUT)),
            enable_hstore=util.strtobool(
                os.environ.get(
                    'POSTGRES_HSTORE', DEFAULT_POSTGRES_HSTORE)),
            enable_json=util.strtobool(
                os.environ.get('POSTGRES_JSON', DEFAULT_POSTGRES_JSON)),
            enable_uuid=util.strtobool(
                os.environ.get('POSTGRES_UUID', DEFAULT_POSTGRES_UUID)),
            echo=False,
            on_connect=None,
            pool_recycle=int(
                os.environ.get(
                    'POSTGRES_CONNECTION_TTL',
                    DEFAULT_POSTGRES_CONNECTION_TTL)))
        try:
            async with self._postgres_pool._cond:
                await self._postgres_pool._fill_free_pool(False)
        except (psycopg2.OperationalError,
                psycopg2.Error) as error:  # pragma: nocover
            LOGGER.warning('Error connecting to PostgreSQL on startup: %s',
                           error)

    async def _postgres_shutdown(self, _ioloop: ioloop.IOLoop) -> None:
        """Shutdown the Postgres connections and wait for them to close.

        This is invoked by the Application shutdown callback mechanism.

        """
        self._postgres_pool.close()
        await self._postgres_pool.wait_closed()
