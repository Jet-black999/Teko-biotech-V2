from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import Field

from ..schemas.readings import StrictModel
from ..security import authenticated_gateway
from ..services.simulator import GATEWAY, NODE, CHANNEL, SimulatorConflict, submit

router = APIRouter(prefix='/api/v1/simulator', tags=['Simulação integrada'])


class Submission(StrictModel):
    request_id: UUID
    values: Annotated[list[Annotated[float, Field(strict=True, ge=0, le=100, allow_inf_nan=False)]], Field(min_length=1, max_length=6)]


@router.get('/config')
def config(request: Request):
    enabled = request.app.state.settings.simulator_enabled
    with request.app.state.database.connection(readonly=True) as c:
        prepared = c.execute('SELECT 1 FROM channels WHERE node_id=? AND id=?', (NODE, CHANNEL)).fetchone() is not None
        rule = c.execute("SELECT enabled FROM alert_rules WHERE id='simulator-low-signal'").fetchone()
    return {'rule_enabled': bool(rule and rule['enabled']), 'enabled': enabled, 'prepared': prepared, 'node_id': NODE, 'channel_id': CHANNEL}


@router.post('/readings')
def readings(body: Submission, request: Request, gateway: str = Depends(authenticated_gateway)):
    if not request.app.state.settings.simulator_enabled:
        raise HTTPException(403, 'Simulação desabilitada. Configure SIMULATOR_ENABLED=true e reinicie a API.')
    if gateway != GATEWAY:
        raise HTTPException(403, 'Use somente a credencial do gateway-simulator.')
    try:
        return submit(request.app.state.database, body.request_id, body.values)
    except SimulatorConflict as exc:
        raise HTTPException(409, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
