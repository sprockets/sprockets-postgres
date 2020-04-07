import asyncio
import contextlib
import dataclasses
import logging
import os
import time
import typing
from distutils import util

import aiopg
import psycopg2
from aiopg import pool
from psycopg2 import errors, extras
from tornado import ioloop, web

LOGGER = logging.getLogger('sprockets-postgres')

DEFAULT_POSTGRES_CONNECTION_TIMEOUT = 10
DEFAULT_POSTGRES_CONNECTION_TTL = 300
DEFAULT_POSTGRES_HSTORE = 'FALSE'
DEFAULT_POSTGRES_JSON = 'FALSE'
DEFAULT_POSTGRES_MAX_POOL_SIZE = 0
DEFAULT_POSTGRES_MIN_POOL_SIZE = 1
DEFAULT_POSTGRES_QUERY_TIMEOUT = 120
DEFAULT_POSTGRES_UUID = 'TRUE'

QueryParameters = typing.Union[dict, list, tuple, None]
Timeout = typing.Union[int, float, None]


@dataclasses.dataclass
class QueryResult:
    row_count: int
    row: typing.Optional[dict]
    rows: typing.Optional[typing.List[dict]]


class PostgresConnector:

    def __init__(self,
                 cursor: aiopg.Cursor,
                 on_error: typing.Callable,
                 record_duration: typing.Optional[typing.Callable] = None,
                 timeout: Timeout = None):
        self.cursor = cursor
        self._on_error = on_error
        self._record_duration = record_duration
        self._timeout = timeout or int(
            os.environ.get(
                'POSTGRES_QUERY_TIMEOUT',
                DEFAULT_POSTGRES_QUERY_TIMEOUT))

    async def callproc(self,
                       name: str,
                       parameters: QueryParameters = None,
                       metric_name: str = '',
                       *,
                       timeout: Timeout = None) -> QueryResult:
        return await self._query(
            self.cursor.callproc,
            metric_name,
            procname=name,
            parameters=parameters,
            timeout=timeout)

    async def execute(self,
                      sql: str,
                      parameters: QueryParameters = None,
                      metric_name: str = '',
                      *,
                      timeout: Timeout = None) -> QueryResult:
        return await self._query(
            self.cursor.execute,
            metric_name,
            operation=sql,
            parameters=parameters,
            timeout=timeout)

    @contextlib.asynccontextmanager
    async def transaction(self) \
            -> typing.AsyncContextManager['PostgresConnector']:
        async with self.cursor.begin():
            yield self

    async def _query(self,
                     method: typing.Callable,
                     metric_name: str,
                     **kwargs):
        if kwargs['timeout'] is None:
            kwargs['timeout'] = self._timeout
        start_time = time.monotonic()
        try:
            await method(**kwargs)
        except (asyncio.TimeoutError, psycopg2.Error) as err:
            exc = self._on_error(metric_name, err)
            if exc:
                raise exc
        else:
            if self._record_duration:
                self._record_duration(
                    metric_name, time.monotonic() - start_time)
        return await self._query_results()

    async def _query_results(self) -> QueryResult:
        count, row, rows = self.cursor.rowcount, None, None
        if self.cursor.rowcount == 1:
            try:
                row = dict(await self.cursor.fetchone())
            except psycopg2.ProgrammingError:
                pass
        elif self.cursor.rowcount > 1:
            try:
                rows = [dict(row) for row in await self.cursor.fetchall()]
            except psycopg2.ProgrammingError:
                pass
        return QueryResult(count, row, rows)


class ConnectionException(Exception):
    """Raised when the connection to Postgres can not be established"""


class ApplicationMixin:
    """
    :class:`sprockets.http.app.Application` mixin for handling the connection
    to Postgres and exporting functions for querying the database,
    getting the status, and proving a cursor.

    Automatically creates and shuts down :class:`aio.pool.Pool` on startup
    and shutdown.

    """
    POSTGRES_STATUS_TIMEOUT = 3

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._postgres_pool: typing.Optional[pool.Pool] = None
        self.runner_callbacks['on_start'].append(self._postgres_setup)
        self.runner_callbacks['shutdown'].append(self._postgres_shutdown)

    @contextlib.asynccontextmanager
    async def postgres_connector(self,
                                 on_error: typing.Callable,
                                 record_duration: typing.Optional[
                                     typing.Callable] = None,
                                 timeout: Timeout = None) \
            -> typing.AsyncContextManager[PostgresConnector]:
        try:
            async with self._postgres_pool.acquire() as conn:
                async with conn.cursor(
                        cursor_factory=extras.RealDictCursor,
                        timeout=timeout) as cursor:
                    yield PostgresConnector(
                        cursor, on_error, record_duration, timeout)
        except (asyncio.TimeoutError, psycopg2.Error) as err:
            on_error('postgres_connector', ConnectionException(str(err)))

    async def postgres_status(self) -> dict:
        """Invoke from the ``/status`` RequestHandler to check that there is
         a Postgres connection handler available and return info about the
         pool.

        """
        query_error = asyncio.Event()

        def on_error(_metric_name, _exc) -> None:
            query_error.set()
            return None

        async with self.postgres_connector(
                on_error,
                timeout=self.POSTGRES_STATUS_TIMEOUT) as connector:
            await connector.execute('SELECT 1')
        return {
            'available': not query_error.is_set(),
            'pool_size': self._postgres_pool.size,
            'pool_free': self._postgres_pool.freesize
        }

    async def _postgres_setup(self,
                              _app: web.Application,
                              loop: ioloop.IOLoop) -> None:
        """Setup the Postgres pool of connections and log if there is an error.

        This is invoked by the Application on start callback mechanism.

        """
        if 'POSTGRES_URL' not in os.environ:
            LOGGER.critical('Missing POSTGRES_URL environment variable')
            return self.stop(loop)
        self._postgres_pool = pool.Pool(
            os.environ['POSTGRES_URL'],
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


class RequestHandlerMixin:
    """
    RequestHandler mixin class exposing functions for querying the database,
    recording the duration to either `sprockets-influxdb` or
    `sprockets.mixins.metrics`, and handling exceptions.

    """
    async def postgres_callproc(self,
                                name: str,
                                parameters: QueryParameters = None,
                                metric_name: str = '',
                                *,
                                timeout: Timeout = None) -> QueryResult:
        async with self.application.postgres_connector(
                self._on_postgres_error,
                self._on_postgres_timing,
                timeout) as connector:
            return await connector.callproc(
                name, parameters, metric_name, timeout=timeout)

    async def postgres_execute(self,
                               sql: str,
                               parameters: QueryParameters = None,
                               metric_name: str = '',
                               *,
                               timeout: Timeout = None) -> QueryResult:
        """Execute a query, specifying a name for the query, the SQL statement,
        and optional positional arguments to pass in with the query.

        Parameters may be provided as sequence or mapping and will be
        bound to variables in the operation.  Variables are specified
        either with positional ``%s`` or named ``%({name})s`` placeholders.

        """
        async with self.application.postgres_connector(
                self._on_postgres_error,
                self._on_postgres_timing,
                timeout) as connector:
            return await connector.execute(
                sql, parameters, metric_name, timeout=timeout)

    @contextlib.asynccontextmanager
    async def postgres_transaction(self, timeout: Timeout = None) \
            -> typing.AsyncContextManager[PostgresConnector]:
        """Yields a :class:`PostgresConnector` instance in a transaction.
        Will automatically commit or rollback based upon exception.

        """
        async with self.application.postgres_connector(
                self._on_postgres_error,
                self._on_postgres_timing,
                timeout) as connector:
            async with connector.transaction():
                yield connector

    def _on_postgres_error(self,
                           metric_name: str,
                           exc: Exception) -> typing.Optional[Exception]:
        """Override for different error handling behaviors"""
        LOGGER.error('%s in %s for %s (%s)',
                     exc.__class__.__name__, self.__class__.__name__,
                     metric_name, str(exc).split('\n')[0])
        if isinstance(exc, ConnectionException):
            raise web.HTTPError(503, reason='Database Connection Error')
        elif isinstance(exc, asyncio.TimeoutError):
            raise web.HTTPError(500, reason='Query Timeout')
        elif isinstance(exc, errors.UniqueViolation):
            raise web.HTTPError(409, reason='Unique Violation')
        elif isinstance(exc, psycopg2.Error):
            raise web.HTTPError(500, reason='Database Error')
        return exc

    def _on_postgres_timing(self,
                            metric_name: str,
                            duration: float) -> None:
        """Override for custom metric recording"""
        if hasattr(self, 'influxdb'):  # sprockets-influxdb
            self.influxdb.set_field(metric_name, duration)
        elif hasattr(self, 'record_timing'):  # sprockets.mixins.metrics
            self.record_timing(metric_name, duration)
        else:
            LOGGER.debug('Postgres query %s duration: %s',
                         metric_name, duration)
