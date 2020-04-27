import asyncio
import json
import os
import typing
import unittest
import uuid
from unittest import mock

import psycopg2
from psycopg2 import errors
from sprockets.http import app, testing
from tornado import ioloop, web

import sprockets_postgres


class RequestHandler(sprockets_postgres.RequestHandlerMixin,
                     web.RequestHandler):
    """Base RequestHandler for test endpoints"""

    def cast_data(self, data: typing.Union[dict, list, None]) \
            -> typing.Union[dict, list, None]:
        if data is None:
            return None
        elif isinstance(data, list):
            return [self.cast_data(row) for row in data]
        return {k: str(v) for k, v in data.items()}


class CallprocRequestHandler(RequestHandler):

    async def get(self):
        result = await self.postgres_callproc(
            'uuid_generate_v4', metric_name='uuid')
        await self.finish({'value': str(result.row['uuid_generate_v4'])})


class CountRequestHandler(RequestHandler):

    GET_SQL = """\
    SELECT last_updated_at, count
      FROM public.query_count
     WHERE key = 'test';"""

    async def get(self):
        result = await self.postgres_execute(self.GET_SQL)
        assert '<QueryResult row_count=1>' == repr(result)
        assert result.rows[0] == result.row
        await self.finish(self.cast_data(result.row))


class ErrorRequestHandler(RequestHandler):

    GET_SQL = """\
    SELECT last_updated_at, count
      FROM public.query_count
     WHERE key = 'test';"""

    async def get(self):
        await self.postgres_execute(self.GET_SQL)
        self.set_status(204)

    def _on_postgres_error(self,
                           metric_name: str,
                           exc: Exception) -> typing.Optional[Exception]:
        return RuntimeError()


class ErrorPassthroughRequestHandler(RequestHandler):

    async def get(self):
        exc = self._on_postgres_error('test', RuntimeError())
        if isinstance(exc, RuntimeError):
            self.set_status(204)
        else:
            raise web.HTTPError(500, 'Did not pass through')


class ExecuteRequestHandler(RequestHandler):

    GET_SQL = 'SELECT %s::TEXT AS value;'

    async def get(self):
        timeout = self.get_argument('timeout', None)
        if timeout is not None:
            timeout = int(timeout)
        result = await self.postgres_execute(
            self.GET_SQL, [self.get_argument('value')], timeout=timeout)
        await self.finish({
            'value': result.row['value'] if result.row else None})


class InfluxDBRequestHandler(ExecuteRequestHandler):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.influxdb = self.application.influxdb
        self.influxdb.add_field = mock.Mock()


class MetricsMixinRequestHandler(ExecuteRequestHandler):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.record_timing = self.application.record_timing


class MultiRowRequestHandler(RequestHandler):

    GET_SQL = 'SELECT * FROM public.test_rows;'

    UPDATE_SQL = """\
    UPDATE public.test_rows
       SET toggle = %(to_value)s,
           last_modified_at = CURRENT_TIMESTAMP
     WHERE toggle IS %(from_value)s"""

    async def get(self):
        result = await self.postgres_execute(self.GET_SQL)
        await self.finish({
            'count': result.row_count,
            'rows': self.cast_data(result.rows),
            'iterator_rows': [self.cast_data(r) for r in result]})

    async def post(self):
        body = json.loads(self.request.body.decode('utf-8'))
        result = await self.postgres_execute(
            self.UPDATE_SQL, {
                'to_value': body['value'], 'from_value': not body['value']})
        await self.finish({
            'count': result.row_count,
            'rows': self.cast_data(result.rows)})


class NoErrorRequestHandler(ErrorRequestHandler):

    def _on_postgres_error(self,
                           metric_name: str,
                           exc: Exception) -> typing.Optional[Exception]:
        return None


class NoRowRequestHandler(RequestHandler):

    GET_SQL = """\
    SELECT * FROM information_schema.tables WHERE table_schema = 'foo';"""

    async def get(self):
        result = await self.postgres_execute(self.GET_SQL)
        assert len(result) == result.row_count
        await self.finish({
            'count': result.row_count,
            'rows': self.cast_data(result.rows)})


class StatusRequestHandler(RequestHandler):

    async def get(self):
        status = await self.application.postgres_status()
        if not status['available']:
            self.set_status(503, 'Database Unavailable')
        await self.finish(status)


class TransactionRequestHandler(RequestHandler):

    GET_SQL = """\
    SELECT id, created_at, last_modified_at, value
      FROM public.test
     WHERE id = %(id)s;"""

    POST_SQL = """\
    INSERT INTO public.test (id, created_at, value)
         VALUES (%(id)s, CURRENT_TIMESTAMP, %(value)s)
      RETURNING id, created_at, value;"""

    UPDATE_COUNT_SQL = """\
        UPDATE public.query_count
           SET count = count + 1,
               last_updated_at = CURRENT_TIMESTAMP
         WHERE key = 'test'
     RETURNING last_updated_at, count;"""

    async def get(self, test_id):
        result = await self.postgres_execute(self.GET_SQL, {'id': test_id})
        if not result.row_count:
            raise web.HTTPError(404, 'Not Found')
        await self.finish(self.cast_data(result.row))

    async def post(self):
        body = json.loads(self.request.body.decode('utf-8'))
        async with self.postgres_transaction() as postgres:

            # This should roll back on the second call to this endopoint
            self.application.first_txn = await postgres.execute(
                self.POST_SQL, {'id': str(uuid.uuid4()),
                                'value': str(uuid.uuid4())})

            # This should roll back on the second call to this endopoint
            count = await postgres.execute(self.UPDATE_COUNT_SQL)

            # This will trigger an error on the second call to this endpoint
            user = await postgres.execute(self.POST_SQL, body)

        await self.finish({
            'count': self.cast_data(count.row),
            'user': self.cast_data(user.row)})


class Application(sprockets_postgres.ApplicationMixin,
                  app.Application):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.influxdb = mock.Mock()
        self.record_timing = mock.Mock()
        self.first_txn: typing.Optional[sprockets_postgres.QueryResult] = None


class TestCase(testing.SprocketsHttpTestCase):

    @classmethod
    def setUpClass(cls):
        with open('build/test-environment') as f:
            for line in f:
                if line.startswith('export '):
                    line = line[7:]
                name, _, value = line.strip().partition('=')
                os.environ[name] = value

    def get_app(self):
        self.app = Application(handlers=[
            web.url('/callproc', CallprocRequestHandler),
            web.url('/count', CountRequestHandler),
            web.url('/error', ErrorRequestHandler),
            web.url('/error-passthrough', ErrorPassthroughRequestHandler),
            web.url('/execute', ExecuteRequestHandler),
            web.url('/influxdb', InfluxDBRequestHandler),
            web.url('/metrics-mixin', MetricsMixinRequestHandler),
            web.url('/multi-row', MultiRowRequestHandler),
            web.url('/no-error', NoErrorRequestHandler),
            web.url('/no-row', NoRowRequestHandler),
            web.url('/status', StatusRequestHandler),
            web.url('/transaction', TransactionRequestHandler),
            web.url('/transaction/(?P<test_id>.*)', TransactionRequestHandler)
        ])
        return self.app


class RequestHandlerMixinTestCase(TestCase):

    def test_postgres_status(self):
        response = self.fetch('/status')
        data = json.loads(response.body)
        self.assertTrue(data['available'])
        self.assertGreaterEqual(data['pool_size'], 1)
        self.assertGreaterEqual(data['pool_free'], 1)

    @mock.patch('aiopg.pool.Pool.acquire')
    def test_postgres_status_connect_error(self, acquire):
        acquire.side_effect = asyncio.TimeoutError()
        response = self.fetch('/status')
        self.assertEqual(response.code, 503)
        self.assertFalse(json.loads(response.body)['available'])

    @mock.patch('aiopg.cursor.Cursor.execute')
    def test_postgres_status_error(self, execute):
        execute.side_effect = asyncio.TimeoutError()
        response = self.fetch('/status')
        self.assertEqual(response.code, 503)
        self.assertFalse(json.loads(response.body)['available'])

    def test_postgres_callproc(self):
        response = self.fetch('/callproc')
        self.assertEqual(response.code, 200)
        self.assertIsInstance(
            uuid.UUID(json.loads(response.body)['value']), uuid.UUID)

    @mock.patch('aiopg.cursor.Cursor.execute')
    def test_postgres_error(self, execute):
        execute.side_effect = asyncio.TimeoutError
        response = self.fetch('/error')
        self.assertEqual(response.code, 500)
        self.assertIn(b'Internal Server Error', response.body)

    @mock.patch('aiopg.pool.Pool.acquire')
    def test_postgres_error_on_connect(self, acquire):
        acquire.side_effect = asyncio.TimeoutError
        response = self.fetch('/error')
        self.assertEqual(response.code, 500)
        self.assertIn(b'Internal Server Error', response.body)

    def test_postgres_error_passthrough(self):
        response = self.fetch('/error-passthrough')
        self.assertEqual(response.code, 204)

    def test_postgres_execute(self):
        expectation = str(uuid.uuid4())
        response = self.fetch('/execute?value={}'.format(expectation))
        self.assertEqual(response.code, 200)
        self.assertEqual(json.loads(response.body)['value'], expectation)

    def test_postgres_execute_with_timeout(self):
        expectation = str(uuid.uuid4())
        response = self.fetch(
            '/execute?value={}&timeout=5'.format(expectation))
        self.assertEqual(response.code, 200)
        self.assertEqual(json.loads(response.body)['value'], expectation)

    def test_postgres_influxdb(self):
        expectation = str(uuid.uuid4())
        response = self.fetch(
            '/influxdb?value={}'.format(expectation))
        self.assertEqual(response.code, 200)
        self.assertEqual(json.loads(response.body)['value'], expectation)
        self.app.influxdb.set_field.assert_called_once()

    def test_postgres_metrics_mixin(self):
        expectation = str(uuid.uuid4())
        response = self.fetch(
            '/metrics-mixin?value={}'.format(expectation))
        self.assertEqual(response.code, 200)
        self.assertEqual(json.loads(response.body)['value'], expectation)
        self.app.record_timing.assert_called_once()

    def test_postgres_multirow_get(self):
        response = self.fetch('/multi-row')
        self.assertEqual(response.code, 200)
        body = json.loads(response.body)
        self.assertEqual(body['count'], 5)
        self.assertIsInstance(body['rows'], list)

    def test_postgres_multirow_no_data(self):
        for value in [True, False]:
            response = self.fetch(
                '/multi-row', method='POST', body=json.dumps({'value': value}))
            self.assertEqual(response.code, 200)
            body = json.loads(response.body)
            self.assertEqual(body['count'], 5)
            self.assertListEqual(body['rows'], [])

    def test_postgres_norow(self):
        response = self.fetch('/no-row')
        self.assertEqual(response.code, 200)
        body = json.loads(response.body)
        self.assertEqual(body['count'], 0)
        self.assertListEqual(body['rows'], [])

    @mock.patch('aiopg.cursor.Cursor.execute')
    def test_postgres_execute_timeout_error(self, execute):
        execute.side_effect = asyncio.TimeoutError()
        response = self.fetch('/execute?value=1')
        self.assertEqual(response.code, 500)
        self.assertIn(b'Query Timeout', response.body)

    @mock.patch('aiopg.cursor.Cursor.execute')
    def test_postgres_execute_unique_violation(self, execute):
        execute.side_effect = errors.UniqueViolation()
        response = self.fetch('/execute?value=1')
        self.assertEqual(response.code, 409)
        self.assertIn(b'Unique Violation', response.body)

    @mock.patch('aiopg.cursor.Cursor.execute')
    def test_postgres_execute_error(self, execute):
        execute.side_effect = psycopg2.Error()
        response = self.fetch('/execute?value=1')
        self.assertEqual(response.code, 500)
        self.assertIn(b'Database Error', response.body)

    @mock.patch('aiopg.cursor.Cursor.fetchone')
    def test_postgres_programming_error(self, fetchone):
        fetchone.side_effect = psycopg2.ProgrammingError()
        response = self.fetch('/execute?value=1')
        self.assertEqual(response.code, 200)
        self.assertIsNone(json.loads(response.body)['value'])

    @mock.patch('aiopg.connection.Connection.cursor')
    def test_postgres_cursor_raises(self, cursor):
        cursor.side_effect = asyncio.TimeoutError()
        response = self.fetch('/execute?value=1')
        self.assertEqual(response.code, 503)


class TransactionTestCase(TestCase):

    def test_transactions(self):
        test_body = {
            'id': str(uuid.uuid4()),
            'value': str(uuid.uuid4())
        }
        response = self.fetch(
            '/transaction', method='POST', body=json.dumps(test_body))
        self.assertEqual(response.code, 200)
        record = json.loads(response.body.decode('utf-8'))
        self.assertEqual(record['user']['id'], test_body['id'])
        self.assertEqual(record['user']['value'], test_body['value'])
        count = record['count']['count']
        last_updated = record['count']['last_updated_at']

        response = self.fetch(
            '/transaction', method='POST', body=json.dumps(test_body))
        self.assertEqual(response.code, 409)

        response = self.fetch(
            '/transaction/{}'.format(self.app.first_txn.row['id']))
        self.assertEqual(response.code, 404)

        response = self.fetch('/count')
        self.assertEqual(response.code, 200)
        record = json.loads(response.body.decode('utf-8'))
        self.assertEqual(record['count'], count)
        self.assertEqual(record['last_updated_at'], last_updated)


class MissingURLTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        with open('build/test-environment') as f:
            for line in f:
                if line.startswith('export '):
                    line = line[7:]
                name, _, value = line.strip().partition('=')
                if name != 'POSTGRES_URL':
                    os.environ[name] = value
        if 'POSTGRES_URL' in os.environ:
            del os.environ['POSTGRES_URL']

    def test_that_stop_is_invoked(self):
        io_loop = ioloop.IOLoop.current()
        obj = Application()
        obj.stop = mock.Mock(wraps=obj.stop)
        obj.start(io_loop)
        io_loop.start()
        obj.stop.assert_called_once()
