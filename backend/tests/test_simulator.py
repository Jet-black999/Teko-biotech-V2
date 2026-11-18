import asyncio
import sqlite3
from unittest.mock import patch
from dataclasses import replace
from uuid import uuid4

from app.security import issue_token, issue_bot_token
from app.services.simulator import prepare, NODE
from support import ASGITestCase


class SimulatorTests(ASGITestCase):
    settings_overrides = {'simulator_enabled': True, 'authorized_telegram_chat_id': '123456'}

    async def asyncSetUp(self):
        loop = asyncio.get_running_loop()
        def pulse(): self.pulse_handle = loop.call_later(.01, pulse)
        pulse()
        await super().asyncSetUp()
        prepare(self.database)
        self.simulator_token = issue_token(self.database, 'gateway-simulator')
        self.bot_token = issue_bot_token(self.database)

    def _tearDownAsyncioRunner(self):
        try: super()._tearDownAsyncioRunner()
        finally:
            if hasattr(self, 'pulse_handle'): self.pulse_handle.cancel()

    async def send_values(self, values, request_id=None, **kwargs):
        return await self.request('/api/v1/simulator/readings', data={'request_id': request_id or str(uuid4()), 'values': values}, token=kwargs.pop('token', self.simulator_token), **kwargs)

    async def test_shared_readings_alert_and_recovery_queue(self):
        response = await self.send_values([20, 21, 22])
        self.assertEqual(response[0], 200, response)
        latest = (await self.request(f'/api/v1/devices/{NODE}/latest', method='GET', token=False))[1]
        reading = latest['channels'][0]['reading']
        self.assertEqual(reading['result']['value'], 22)
        self.assertEqual(reading['source'], 'simulation')
        alerts = (await self.request(f'/api/v1/alerts?node_id={NODE}&status=active', method='GET', token=False))[1]
        self.assertEqual(len(alerts['items']), 1)
        await self.send_values([36, 37, 38])
        alerts = (await self.request(f'/api/v1/alerts?node_id={NODE}', method='GET', token=False))[1]
        self.assertEqual(alerts['items'][0]['status'], 'resolved')
        queue = await self.request('/api/v1/internal/notifications/claim', data={'worker_id': 'simulator-test', 'limit': 2}, token=self.bot_token)
        self.assertEqual([i['event'] for i in queue[1]['items']], ['opened', 'resolved'])
        self.assertTrue(all('simulação' in i['text'] for i in queue[1]['items']))

    async def test_idempotent_retry_conflict_and_restart(self):
        request_id = str(uuid4())
        first = await self.send_values([20, 21, 22], request_id)
        second = await self.send_values([20, 21, 22], request_id)
        self.assertEqual(first[1]['reading_ids'], second[1]['reading_ids'])
        self.assertTrue(second[1]['duplicate'])
        self.assertEqual(self.count(), 3)
        self.assertEqual((await self.send_values([45], request_id))[0], 409)
        self.database.initialize()
        self.assertTrue((await self.send_values([20, 21, 22], request_id))[1]['duplicate'])
        await self.send_values([36, 37, 38])
        self.assertEqual(self.count(), 6)

    async def test_concurrent_retries_have_one_commit(self):
        identity = str(uuid4())
        replies = await asyncio.gather(self.send_values([20, 21, 22], identity), self.send_values([20, 21, 22], identity))
        self.assertTrue(all(r[0] == 200 for r in replies), replies)
        self.assertEqual(sorted(r[1]['duplicate'] for r in replies), [False, True])
        self.assertEqual(self.count(), 3)

    async def test_disabled_and_wrong_credentials_do_not_write(self):
        self.assertEqual((await self.send_values([20], token=False))[0], 401)
        self.assertEqual((await self.send_values([20], token=self.token))[0], 403)
        self.assertEqual((await self.send_values([20], token=self.bot_token))[0], 401)
        self.app.state.settings = replace(self.app.state.settings, simulator_enabled=False)
        self.assertEqual((await self.send_values([20]))[0], 403)
        self.assertEqual(self.count(), 0)

    async def test_invalid_values_and_forged_fields_are_rejected(self):
        for values in ([], [1]*7, [True], [-1], [101], ['20']):
            self.assertEqual((await self.send_values(values))[0], 422, values)
        response = await self.request('/api/v1/simulator/readings', data={'request_id': str(uuid4()), 'values': [20], 'source': 'physical_sensor'}, token=self.simulator_token)
        self.assertEqual(response[0], 422)
        self.assertEqual(self.count(), 0)

    async def test_simulator_token_cannot_ingest_outside_simulator(self):
        response = await self.request(token=self.simulator_token)
        self.assertEqual(response[0], 403)
        self.assertEqual(self.count(), 0)

    async def test_failure_after_ingestion_rolls_back_everything(self):
        from app.services.ingestion import ingest_in_transaction
        def fail_after_ingestion(connection, batch):
            ingest_in_transaction(connection, batch)
            raise sqlite3.OperationalError('falha de armazenamento simulada')
        with self.assertLogs('app.main', level='ERROR'), patch('app.services.simulator.ingest_in_transaction', side_effect=fail_after_ingestion):
            response = await self.send_values([20, 21, 22])
        self.assertEqual(response[0], 503)
        self.assertEqual(self.count(), 0)
        with self.database.connection(readonly=True) as c:
            for table in ('alerts', 'notification_outbox', 'simulator_requests'):
                self.assertEqual(c.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0], 0)

    async def test_prepare_is_repeatable_without_rotating_credentials(self):
        prepare(self.database)
        self.assertEqual((await self.send_values([0]))[0], 200)
        with self.database.connection(readonly=True) as c:
            self.assertEqual(c.execute('SELECT COUNT(*) FROM alert_rules WHERE node_id=?', (NODE,)).fetchone()[0], 1)
            self.assertEqual(c.execute("SELECT COUNT(*) FROM readings WHERE node_id='node-demo-01'").fetchone()[0], 0)
