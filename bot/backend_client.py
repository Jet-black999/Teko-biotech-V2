"""Cliente do contrato v1. O bot não acessa SQLite nem inventa leituras."""
from urllib.parse import quote, urlsplit

import requests


class BackendError(Exception):
    """Erro público sem corpo da resposta, URL ou credenciais."""


class BackendClient:
    def __init__(self, base_url, token, transport=None):
        parsed = urlsplit(base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError("BACKEND_API_URL deve ser HTTP/HTTPS sem credenciais, query ou fragmento.")
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.transport = transport or requests

    def request(self, method, path, **kwargs):
        try:
            response = self.transport.request(
                method, self.base_url + path,
                headers={"Authorization": f"Bearer {self.token}", "Accept": "application/json"},
                timeout=(3, 5), allow_redirects=False, **kwargs,
            )
            if response.status_code != 200:
                raise BackendError(f"Backend respondeu HTTP {response.status_code}.")
            body = response.json()
            if not isinstance(body, dict):
                raise BackendError("Resposta incompatível do backend.")
            return body
        except (requests.RequestException, ValueError) as exc:
            raise BackendError("Não foi possível consultar o backend.") from None

    def config(self):
        body = self.request("GET", "/api/v1/internal/bot-config")
        chat = body.get("authorized_chat_id")
        if chat is not None and (not isinstance(chat, str) or not chat.lstrip("-").isdigit() or int(chat) == 0):
            raise BackendError("Configuração de chat inválida no backend.")
        return body

    def items(self, path, **params):
        body = self.request("GET", path, params=params)
        if not isinstance(body.get("items"), list):
            raise BackendError("Lista incompatível do backend.")
        return body

    def latest(self, node_id):
        return self.request("GET", f"/api/v1/devices/{quote(node_id, safe='')}/latest")

    def claim(self, worker_id):
        return self.request("POST", "/api/v1/internal/notifications/claim", json={"worker_id": worker_id, "limit": 1})["items"]

    def settle(self, item, worker_id, action, **fields):
        return self.request("POST", f"/api/v1/internal/notifications/{quote(item['id'], safe='')}/{action}",
                            json={"worker_id": worker_id, "lease_token": item["lease_token"], **fields})
