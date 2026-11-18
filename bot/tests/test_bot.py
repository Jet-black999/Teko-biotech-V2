"""Integração atual: contrato HTTP, autorização e confirmação de notificações."""
import copy
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
import requests

from backend_client import BackendClient, BackendError
from monitoring import Monitoring, NotificationWorker, dashboard_link, reading_text
import phytosense_bot as entry


def config():
    return {"authorized_chat_id": "123456", "dashboard_url": "http://notebook:5173", "lease_seconds": 60}


def message(text="/status", chat_id=123456):
    return SimpleNamespace(text=text, chat=SimpleNamespace(id=chat_id, type="private"))


def item():
    return {"id": "notification-1", "chat_id": "123456", "text": "Simulação: valor < 30 & condição",
            "lease_token": "segredo-da-reserva", "lease_expires_at": (datetime.now(timezone.utc) + timedelta(seconds=60)).isoformat()}


def channel(value=0, kind="numeric"):
    return {"name": "Sinal", "freshness": {"status": "stale"}, "reading": {
        "profile_id": "signal-demo", "profile_version": 1, "source": "simulation", "quality": "valid",
        "measured_at": None, "result": {"kind": kind, "value": value}}}


def test_http_uses_internal_token_timeout_and_no_redirects():
    transport = MagicMock()
    transport.request.return_value.status_code = 200
    transport.request.return_value.json.return_value = config()
    client = BackendClient("http://backend:8000/", "internal-secret", transport)
    assert client.config() == config()
    args, kwargs = transport.request.call_args
    assert args == ("GET", "http://backend:8000/api/v1/internal/bot-config")
    assert kwargs["headers"]["Authorization"] == "Bearer internal-secret"
    assert kwargs["allow_redirects"] is False
    assert kwargs["timeout"] == (3, 5)


@pytest.mark.parametrize("code", [301, 401, 503])
def test_http_failure_contains_no_token_or_body(code):
    transport = MagicMock()
    transport.request.return_value.status_code = code
    with pytest.raises(BackendError) as error:
        BackendClient("http://backend", "secret", transport).config()
    assert "secret" not in str(error.value)
    transport.request.return_value.json.assert_not_called()


def test_network_failure_has_no_fallback():
    transport = MagicMock()
    transport.request.side_effect = requests.ConnectionError("secret url")
    with pytest.raises(BackendError, match="Não foi possível"):
        BackendClient("http://backend", "secret", transport).config()


def test_missing_chat_fails_closed():
    api = BackendClient("http://backend", "secret")
    with patch.object(api, "request", return_value={"authorized_chat_id": None}):
        assert api.config()["authorized_chat_id"] is None


def test_zero_false_categories_error_and_time_unknown():
    profiles = {("signal-demo", 1): {"unit": "%", "decimals": 1, "labels": {"no": "Não detectado"}, "choices": {"a": {"label": "Classe A"}}}}
    assert "0,0 %" in reading_text(channel(), profiles)
    assert "Não detectado" in reading_text(channel(False, "boolean"), profiles)
    assert "Classe A" in reading_text(channel("a", "categorical"), profiles)
    text = reading_text(channel(), profiles)
    assert "simulação" in text and "leitura antiga" in text and "horário desconhecido" in text
    failed = channel(); failed["reading"].update(quality="sensor_error", result=None)
    assert "erro de aquisição" in reading_text(failed, profiles)
    assert "sem leitura" in reading_text({"name": "Sinal", "reading": None}, profiles)


@pytest.mark.parametrize("command", ["/status", "/sensores", "/alertas", "/painel", "/start"])
def test_unauthorized_chat_cannot_query_monitoring(command):
    with patch.object(entry, "api") as api, patch.object(entry, "monitor") as monitor, patch.object(entry.bot, "send_message") as send:
        api.config.return_value = config()
        entry.handle_questions(message(command, chat_id=999))
        assert "não está autorizado" in send.call_args.args[1]
        assert not monitor.mock_calls


def test_unconfigured_chat_can_retrieve_id_for_setup_without_data_access():
    with patch.object(entry, "api") as api, patch.object(entry, "monitor") as monitor, patch.object(entry.bot, "send_message") as send:
        api.config.return_value = {"authorized_chat_id": None, "dashboard_url": None}
        entry.handle_questions(message("/start", chat_id=987654))
        assert "987654" in send.call_args.args[1]
        assert "configure este ID" in send.call_args.args[1]
        assert not monitor.mock_calls
        api.claim.assert_not_called()


def test_backend_offline_reports_unavailability_without_measurements():
    with patch.object(entry, "api") as api, patch.object(entry.bot, "send_message") as send:
        api.config.side_effect = BackendError("offline")
        entry.handle_questions(message())
        assert "Não consegui consultar" in send.call_args.args[1]
        assert "hidratada" not in send.call_args.args[1]


def test_status_alias_calls_monitor():
    with patch.object(entry, "api") as api, patch.object(entry, "monitor") as monitor, patch.object(entry.bot, "send_message") as send:
        api.config.return_value = config(); monitor.status.return_value = "Leitura simulada 0 %"
        entry.handle_questions(message("/planta@TekoBot"))
        monitor.status.assert_called_once()
        assert send.call_args.kwargs["parse_mode"] is None


def test_local_panel_uses_ordinary_link_and_live_mode():
    with patch.object(entry, "api") as api, patch.object(entry.bot, "send_message") as send:
        api.config.return_value = config()
        entry.handle_questions(message("/painel"))
        button = send.call_args.kwargs["reply_markup"].keyboard[0][0]
        assert button.url == "http://notebook:5173?mode=live"
        assert button.web_app is None
        assert "mesma rede" in send.call_args.args[1]


def test_https_panel_uses_mini_app_in_private_chat_only():
    cfg = {**config(), "dashboard_url": "https://painel.example/?node=node-1#history"}
    assert entry.panel_keyboard(cfg).keyboard[0][0].web_app.url == "https://painel.example/?node=node-1&mode=live#history"
    assert entry.panel_keyboard(cfg, private=False).keyboard[0][0].web_app is None
    assert dashboard_link(None) is None
    assert dashboard_link("javascript:alert(1)") is None


def test_audio_does_not_download_or_invent_diagnosis():
    with patch.object(entry, "api") as api, patch.object(entry.bot, "send_message") as send, patch.object(entry.bot, "get_file") as download:
        api.config.return_value = config()
        entry.handle_voice(message())
        download.assert_not_called()
        assert "não é interpretado" in send.call_args.args[1]


def test_delivery_confirmed_after_send_with_real_message_id():
    api = MagicMock(); api.config.return_value = config(); api.claim.return_value = [item()]
    calls = []
    sender = MagicMock(side_effect=lambda *args: (calls.append("send"), SimpleNamespace(message_id=42))[1])
    api.settle.side_effect = lambda *args, **kwargs: calls.append("ack")
    NotificationWorker(api, sender, "worker-1").tick()
    assert calls == ["send", "ack"]
    assert api.settle.call_args.args[2] == "delivered"
    assert api.settle.call_args.kwargs == {"telegram_message_id": 42}
    assert sender.call_args.args[1] == item()["text"]


def test_send_failure_is_recorded_without_sensitive_exception():
    api = MagicMock(); api.config.return_value = config(); api.claim.return_value = [item()]
    sender = MagicMock(side_effect=RuntimeError("https://api.telegram.org/botSECRET"))
    NotificationWorker(api, sender, "worker-1").tick()
    assert api.settle.call_args.args[2] == "failed"
    assert api.settle.call_args.kwargs == {"error": "telegram_send_failed"}


def test_ack_retry_does_not_send_twice():
    api = MagicMock(); api.config.return_value = config(); api.claim.return_value = [item()]
    api.settle.side_effect = [BackendError("offline"), {}]
    sender = MagicMock(return_value=SimpleNamespace(message_id=42))
    worker = NotificationWorker(api, sender, "worker-1")
    with pytest.raises(BackendError):
        worker.tick()
    worker.tick()
    sender.assert_called_once()
    api.claim.assert_called_once()
    assert api.settle.call_count == 2


def test_expired_ack_releases_worker_for_next_claim():
    api = MagicMock(); api.config.return_value = config()
    expired = item(); expired["lease_expires_at"] = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
    api.claim.return_value = [expired]; api.settle.side_effect = BackendError("expired")
    worker = NotificationWorker(api, MagicMock(return_value=SimpleNamespace(message_id=42)), "w")
    with pytest.raises(BackendError): worker.tick()
    assert worker.pending_ack is None


def test_destination_mismatch_is_not_sent():
    api = MagicMock(); api.config.return_value = config()
    wrong = item(); wrong["chat_id"] = "999"; api.claim.return_value = [wrong]
    sender = MagicMock()
    NotificationWorker(api, sender, "worker-1").tick()
    sender.assert_not_called()
    assert api.settle.call_args.kwargs["error"] == "destination_changed"


def test_unconfigured_chat_does_not_claim():
    api = MagicMock(); api.config.side_effect = BackendError("no chat")
    with pytest.raises(BackendError): NotificationWorker(api, MagicMock(), "w").tick()
    api.claim.assert_not_called()
