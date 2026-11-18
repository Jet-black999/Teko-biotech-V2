"""Respostas simples para o agricultor e entrega da outbox persistente."""
import logging
from datetime import datetime
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from backend_client import BackendError

logger = logging.getLogger(__name__)


def dashboard_link(url):
    if not url:
        return None
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
        return None
    params = dict(parse_qsl(parsed.query, keep_blank_values=True))
    params["mode"] = "live"
    return urlunsplit(parsed._replace(query=urlencode(params)))


def when(value):
    if not value:
        return "horário desconhecido"
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).strftime("%d/%m/%Y %H:%M %z")
    except ValueError:
        return "horário desconhecido"


def reading_text(channel, profiles):
    reading = channel.get("reading")
    if not reading:
        return f"• {channel['name']}: sem leitura disponível."
    profile = profiles.get((reading["profile_id"], reading["profile_version"]), {})
    result = reading.get("result")
    if reading["quality"] == "sensor_error":
        value = "erro de aquisição"
    elif result is None:
        value = "sem resultado"
    elif result["kind"] == "numeric":
        value = f"{result['value']:.{profile.get('decimals', 1)}f}".replace(".", ",")
        value += f" {profile.get('unit', '')}".rstrip()
    elif result["kind"] == "boolean":
        value = profile.get("labels", {}).get("yes" if result["value"] else "no", "Sim" if result["value"] else "Não")
    else:
        value = profile.get("choices", {}).get(result["value"], {}).get("label", result["value"])
    origin = "simulação" if reading["source"] == "simulation" else "sensor físico"
    freshness = {"fresh": "leitura recente", "stale": "leitura antiga", "unknown": "recência desconhecida", "no_data": "sem leitura"}.get(channel["freshness"]["status"], "recência desconhecida")
    return f"• {channel['name']}: {value}\n  {origin} · {freshness}\n  Coleta: {when(reading.get('measured_at'))}"


class Monitoring:
    def __init__(self, api):
        self.api = api

    def status(self):
        nodes = [d for d in self.api.items("/api/v1/devices")["items"] if d["role"] == "node"]
        profiles = {(p["id"], p["version"]): p for p in self.api.items("/api/v1/profiles")["items"]}
        if not nodes:
            return "🌱 Ainda não há pontos cadastrados."
        parts = ["🌱 Leituras da lavoura"]
        for node in nodes:
            channels = self.api.latest(node["id"])["channels"]
            parts.append(f"\n{node['name']} · {node['area_id']}")
            parts.extend(reading_text(c, profiles) for c in channels)
            if not channels:
                parts.append("Sem canais cadastrados.")
        parts.append("\nValores de simulação são fictícios. Consulte os detalhes no painel.")
        return "\n".join(parts)

    def sensors(self):
        devices = self.api.items("/api/v1/devices")["items"]
        parts = ["📡 Pontos de monitoramento"]
        for node in devices:
            if node["role"] != "node":
                continue
            contact = {"fresh": "contato recente", "stale": "contato atrasado", "unknown": "contato desconhecido", "no_data": "sem contato"}.get(node["radio_contact"]["status"], "sem informação")
            parts.append(f"\n• {node['name']} · {node['area_id']}\n  {contact} · {len(node['channels'])} canal(is)")
        if len(parts) == 1:
            parts.append("Ainda não há pontos cadastrados.")
        parts.append("\nContato por rádio e horário da leitura são informações diferentes.")
        return "\n".join(parts)

    def alerts(self):
        page = self.api.items("/api/v1/alerts", status="active", limit=10)
        if not page["items"]:
            return "🔔 Nenhuma ocorrência ativa registrada.\nIsso depende das regras cadastradas e das leituras recebidas; confira também a atualização dos pontos."
        parts = ["🔔 Ocorrências ativas registradas"]
        for alert in page["items"]:
            rule = alert["rule"]
            origin = "simulação" if rule["source"] == "simulation" else "sensor físico"
            parts.append(f"\n• {rule['label']}\n  {alert['node_id']} · {alert['channel_id']} · {origin}\n  Início: {when(alert['opened_at'])}")
        parts.append("\nVeja o histórico e os detalhes no painel.")
        if page.get("next_cursor"):
            parts.append("Há outras ocorrências disponíveis no painel.")
        return "\n".join(parts)


class NotificationWorker:
    def __init__(self, api, sender, worker_id):
        self.api, self.sender, self.worker_id = api, sender, worker_id
        # Se só a confirmação HTTP falhar, repetir a confirmação sem reenviar.
        self.pending_ack = None

    def tick(self):
        if self.pending_ack:
            item, action, fields = self.pending_ack
            self._settle(item, action, fields)
            return
        config = self.api.config()
        if not config.get("authorized_chat_id"):
            raise BackendError("Chat autorizado ainda não configurado no backend.")
        for item in self.api.claim(self.worker_id):
            if str(item["chat_id"]) != config["authorized_chat_id"]:
                self._settle(item, "failed", {"error": "destination_changed"})
                continue
            try:
                message = self.sender(item["chat_id"], item["text"])
            except Exception:
                # Exceções do SDK podem conter URLs com o token do Telegram.
                self._settle(item, "failed", {"error": "telegram_send_failed"})
            else:
                self._settle(item, "delivered", {"telegram_message_id": message.message_id})

    def _settle(self, item, action, fields):
        self.pending_ack = (item, action, fields)
        try:
            self.api.settle(item, self.worker_id, action, **fields)
        except BackendError:
            # Ao vencer o lease a API assume a retentativa; não travar o worker.
            expiry = datetime.fromisoformat(item["lease_expires_at"].replace("Z", "+00:00"))
            if datetime.now(expiry.tzinfo) >= expiry:
                self.pending_ack = None
            raise
        self.pending_ack = None

    def run(self, stop, interval=5):
        while not stop.is_set():
            try:
                self.tick()
            except Exception:
                logger.warning("Fila de notificações indisponível; nova consulta agendada.")
            stop.wait(interval)
