"""Simulador isolado: dados, estado de alerta e recibo na mesma transação."""
import json
from pathlib import Path

from ..database import utc_now
from ..schemas.alerts import AlertRule
from ..schemas.readings import ReadingBatch
from .ingestion import ingest_in_transaction
from .rules import add_rule

GATEWAY = 'gateway-simulator'
NODE = 'node-simulator'
CHANNEL = 'signal-01'
PROFILE = 'simulator-signal'
BOOT = 'simulator-session-v1'


class SimulatorConflict(ValueError):
    pass


def prepare(database):
    profile = {'id': PROFILE, 'version': 1, 'label': 'Sinal fictício do simulador',
               'description': 'Índice fictício para demonstrar painel, alertas e Telegram; sem interpretação agronômica.',
               'kind': 'numeric', 'unit': '%', 'decimals': 1, 'domain': [0, 100]}
    stamp = utc_now()
    with database.transaction() as c:
        c.execute('INSERT INTO gateways(id,name,created_at) VALUES (?,?,?) ON CONFLICT DO NOTHING', (GATEWAY, 'Simulador web (sem rádio)', stamp))
        c.execute('INSERT INTO profiles(id,version,kind,definition_json,created_at) VALUES (?,1,?,?,?) ON CONFLICT DO NOTHING', (PROFILE, 'numeric', json.dumps(profile), stamp))
        c.execute('INSERT INTO nodes(id,gateway_id,name,area_id,created_at) VALUES (?,?,?,?,?) ON CONFLICT DO NOTHING', (NODE, GATEWAY, 'Ponto de simulação integrada', 'area-simulacao', stamp))
        c.execute('INSERT INTO channels(node_id,id,sensor_id,name,profile_id,profile_version,created_at) VALUES (?,?,?,?,?,1,?) ON CONFLICT DO NOTHING', (NODE, CHANNEL, 'simulator', 'Sinal fictício', PROFILE, stamp))
    rule = json.loads((Path(__file__).resolve().parents[2] / 'examples' / 'alert-rule.json').read_text())
    rule.update(id='simulator-low-signal', label='Sinal fictício abaixo de 30%', node_id=NODE, profile_id=PROFILE)
    add_rule(database, AlertRule.model_validate(rule))
    return {'node_id': NODE, 'channel_id': CHANNEL, 'gateway_id': GATEWAY,
            'note': 'Emita a credencial com issue-token gateway-simulator. Nenhuma leitura foi criada.'}


def submit(database, request_id, values):
    encoded = json.dumps(values, allow_nan=False)
    with database.transaction() as c:
        previous = c.execute('SELECT * FROM simulator_requests WHERE request_id=?', (str(request_id),)).fetchone()
        if previous:
            if previous['values_json'] != encoded:
                raise SimulatorConflict('Este envio já foi registrado com outros valores.')
            return {**json.loads(previous['response_json']), 'duplicate': True}
        channel = c.execute('SELECT sensor_id,profile_id,profile_version FROM channels WHERE node_id=? AND id=?', (NODE, CHANNEL)).fetchone()
        if channel is None or tuple(channel) != ('simulator', PROFILE, 1):
            raise ValueError('Execute prepare-simulator antes de enviar valores.')
        node = c.execute('SELECT gateway_id,current_boot_id FROM nodes WHERE id=?', (NODE,)).fetchone()
        if node['gateway_id'] != GATEWAY or node['current_boot_id'] not in (None, BOOT):
            raise ValueError('O ponto do simulador possui configuração de sessão incompatível.')
        sequence = c.execute('SELECT COALESCE(MAX(sequence),0) FROM readings WHERE node_id=? AND node_boot_id=? AND channel_id=?', (NODE, BOOT, CHANNEL)).fetchone()[0]
        stamp = utc_now()
        readings = [{'node_id': NODE, 'channel_id': CHANNEL, 'sensor_id': 'simulator', 'profile_id': PROFILE,
                     'profile_version': 1, 'node_boot_id': BOOT, 'sequence': sequence+i+1,
                     'result': {'kind': 'numeric', 'value': value}, 'quality': 'valid', 'source': 'simulation',
                     'measured_at': stamp, 'time_quality': 'synchronized', 'node_uptime_ms': 0}
                    for i, value in enumerate(values)]
        receipt = ingest_in_transaction(c, ReadingBatch.model_validate({'schema_version': 1, 'gateway_id': GATEWAY, 'readings': readings}))
        if any(item.status != 'accepted' for item in receipt.results):
            raise ValueError('A configuração do simulador rejeitou a leitura. Nenhum valor foi salvo.')
        response = {'request_id': str(request_id), 'node_id': NODE, 'channel_id': CHANNEL, 'duplicate': False,
                    'values': values, 'measured_at': stamp, 'reading_ids': [r.reading_id for r in receipt.results]}
        c.execute('INSERT INTO simulator_requests VALUES (?,?,?,?)', (str(request_id), encoded, json.dumps(response), stamp))
        return response
