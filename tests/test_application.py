import asyncio
import json
import os
from unittest import mock
import uuid

import psycopg2
from psycopg2 import errors
from sprockets.http import app, testing
from tornado import web

import sprockets_postgres


class CallprocRequestHandler(web.RequestHandler):

    async def get(self):
        result = await self.application.postgres_callproc('uuid_generate_v4')
        await self.finish({'value': str(result['uuid_generate_v4'])})


class ExecuteRequestHandler(web.RequestHandler):

    GET_SQL = 'SELECT %s::TEXT AS value;'

    async def get(self):
        result = await self.application.postgres_execute(
            'get', self.GET_SQL, self.get_argument('value'))
        await self.finish({'value': result['value'] if result else None})


class MultiRowRequestHandler(web.RequestHandler):

    GET_SQL = 'SELECT * FROM information_schema.enabled_roles;'

    async def get(self):
        rows = await self.application.postgres_execute('get', self.GET_SQL)
        await self.finish({'rows': [row['role_name'] for row in rows]})


class NoRowRequestHandler(web.RequestHandler):

    GET_SQL = """\
    SELECT * FROM information_schema.tables WHERE table_schema = 'public';"""

    async def get(self):
        rows = await self.application.postgres_execute('get', self.GET_SQL)
        await self.finish({'rows': rows})


class StatusRequestHandler(web.RequestHandler):

    async def get(self):
        result = await self.application.postgres_status()
        if not result['available']:
            self.set_status(503, 'Database Unavailable')
        await self.finish(dict(result))


class Application(sprockets_postgres.ApplicationMixin,
                  app.Application):
    pass


class ExecuteTestCase(testing.SprocketsHttpTestCase):

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
            web.url('/execute', ExecuteRequestHandler),
            web.url('/multi-row', MultiRowRequestHandler),
            web.url('/no-row', NoRowRequestHandler),
            web.url('/status', StatusRequestHandler)
        ])
        return self.app


    def test_postgres_status(self):
        response = self.fetch('/status')
        data = json.loads(response.body)
        self.assertTrue(data['available'])
        self.assertGreaterEqual(data['pool_size'], 1)
        self.assertGreaterEqual(data['pool_free'], 1)

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

    def test_postgres_execute(self):
        expectation = str(uuid.uuid4())
        response = self.fetch('/execute?value={}'.format(expectation))
        self.assertEqual(response.code, 200)
        self.assertEqual(json.loads(response.body)['value'], expectation)

    def test_postgres_multirow(self):
        response = self.fetch('/multi-row')
        self.assertEqual(response.code, 200)
        body = json.loads(response.body)
        self.assertIsInstance(body['rows'], list)
        self.assertIn('postgres', body['rows'])

    def test_postgres_norow(self):
        response = self.fetch('/no-row')
        self.assertEqual(response.code, 200)
        body = json.loads(response.body)
        self.assertIsNone(body['rows'])

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

    def test_postgres_programming_error(self):
        with mock.patch.object(self.app, '_postgres_query_results') as pqr:
            pqr.side_effect = psycopg2.ProgrammingError()
            response = self.fetch('/execute?value=1')
            self.assertEqual(response.code, 200)
            self.assertIsNone(json.loads(response.body)['value'])

    @mock.patch('aiopg.connection.Connection.cursor')
    def test_postgres_cursor_raises(self, cursor):
        cursor.side_effect = asyncio.TimeoutError()
        response = self.fetch('/execute?value=1')
        self.assertEqual(response.code, 503)
