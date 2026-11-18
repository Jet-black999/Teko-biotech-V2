"""Cliente e worker reais contra API ASGI/SQLite; apenas Telegram é simulado."""
import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock
from urllib.parse import urlencode, urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'bot'))
from backend_client import BackendClient
from monitoring import Monitoring, NotificationWorker
from alert_support import AlertTestCase


class BotIntegrationTests(AlertTestCase):
    async def asyncSetUp(self):
        # O executor restrito precisa de um timer para despertar threads ASGI.
        loop = asyncio.get_running_loop()
        def pulse():
            self.pulse_handle = loop.call_later(0.01, pulse)
        pulse()
        await super().asyncSetUp()

    def _tearDownAsyncioRunner(self):
        try:
            super()._tearDownAsyncioRunner()
        finally:
            if hasattr(self, 'pulse_handle'):
                self.pulse_handle.cancel()

    async def test_readings_occurrence_delivery_and_recovery(self):
        await self.integrated_flow(False)

    async def test_simulator_readings_reach_bot_and_notifications(self):
        await self.integrated_flow(True)

    async def integrated_flow(self, simulator):
        from dataclasses import replace
        from uuid import uuid4
        from unittest.mock import patch
        from app.services.simulator import prepare
        from app.security import issue_token
        from app.timeutils import iso_utc
        if simulator:
            self.app.state.settings = replace(self.app.state.settings, simulator_enabled=True)
            prepare(self.database)
            token = issue_token(self.database, 'gateway-simulator')
        async def send_values(values):
            if not simulator:
                return await self.values(values)
            with patch('app.services.simulator.utc_now', return_value=iso_utc(self.clock)):
                response = await self.request('/api/v1/simulator/readings', data={'request_id': str(uuid4()), 'values': values}, token=token)
            self.assertEqual(response[0], 200, response)
        await send_values([20, 21, 22])
        loop = asyncio.get_running_loop()
        case = self

        class Transport:
            def request(self, method, url, **kwargs):
                path = urlsplit(url).path
                if kwargs.get('params'):
                    path += '?' + urlencode(kwargs['params'])
                token = kwargs['headers']['Authorization'].removeprefix('Bearer ')
                future = asyncio.run_coroutine_threadsafe(case.request(
                    path, data=kwargs.get('json'), method=method, token=token), loop)
                status, body, _ = future.result(timeout=10)
                return SimpleNamespace(status_code=status, json=lambda: body)

        api = BackendClient('http://asgi', self.bot_token, Transport())
        monitor = Monitoring(api)
        sender = MagicMock(return_value=SimpleNamespace(message_id=987))
        worker = NotificationWorker(api, sender, 'phytosense-integration')

        async def execute(call):
            # Desperta o loop também no executor restrito, sem alterar a API.
            task = asyncio.create_task(asyncio.to_thread(call))
            while not task.done():
                await asyncio.sleep(0.01)
            return await task

        status = await execute(monitor.status)
        self.assertIn('22,0 %', status)
        self.assertIn('simulação', status)
        self.assertIn('Sinal fictício' if simulator else self.rule.label, await execute(monitor.alerts))
        await execute(worker.tick)
        sender.assert_called_once()
        self.assertIn(f"mode=live&node={'node-simulator' if simulator else 'node-demo-01'}&channel=signal-01#alerts", sender.call_args.args[1])
        diagnostic = await self.request('/api/v1/internal/notifications', method='GET', token=self.bot_token)
        self.assertEqual(diagnostic[1]['items'][0]['status'], 'sent')
        self.assertEqual(diagnostic[1]['items'][0]['telegram_message_id'], 987)
        await execute(worker.tick)
        sender.assert_called_once()
        await send_values([36, 37, 38])
        await execute(worker.tick)
        self.assertEqual(sender.call_count, 2)
        self.assertIn('Nenhuma ocorrência ativa', await execute(monitor.alerts))
