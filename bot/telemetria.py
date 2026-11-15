"""
Módulo de Telemetria Fitoeletrônica — Tekó Biotech
Hackathon das Engenharias UERGS 2026 — Desafio 02: Água e Drenagem Rural
"""

import os
from typing import Optional, Dict, Any
import requests

BACKEND_API_URL = os.getenv("BACKEND_API_URL", "http://127.0.0.1:8000").rstrip("/")

DADOS_ESTADOS = {
    "hidratada": {
        "rotulo": "Planta Hidratada (Seiva Normal)",
        "icone": "🟢",
        "tensao_kpa": 21.5,
        "tensao_faixa": "10 a 30 kPa (Capacidade de Campo)",
        "z_50k_kohm": 1.4,
        "z_1k_kohm": 1.1,
        "orp_mv": 310,
        "ce_dsm": 1.2,
        "bomba": "DESLIGADA",
        "economia_litros": 4200,
        "economia_reais": 38.00,
        "mensagem_acao": "Pode deixar a irrigação desligada hoje. A seiva está circulando com vigor.",
        "laudo_proagro": False
    },
    "sede": {
        "rotulo": "Alerta de Sede Precoce (Estiagem)",
        "icone": "🟡",
        "tensao_kpa": 45.0,
        "tensao_faixa": "30 a 60 kPa (Início de Estresse Hídrico)",
        "z_50k_kohm": 4.8,
        "z_1k_kohm": 3.9,
        "orp_mv": 420,
        "ce_dsm": 1.8,
        "bomba": "LIGAR AMANHÃ ÀS 06H",
        "duracao_min": 40,
        "vazao_l_metro": 3.5,
        "economia_litros": 2400,
        "economia_reais": 22.00,
        "mensagem_acao": "Ligue o gotejamento amanhã às 6h da manhã por 40 minutos (3,5 litros por metro) antes do sol forte.",
        "laudo_proagro": False
    },
    "hipoxia": {
        "rotulo": "Alerta de Enchente (Raiz Sufocando / Hipóxia)",
        "icone": "🔴",
        "tensao_kpa": 4.2,
        "tensao_faixa": "< 10 kPa (Solo 100% Encharcado / Asfixia)",
        "z_50k_kohm": 5.9,
        "z_1k_kohm": 5.1,
        "orp_mv": -140,
        "ce_dsm": 0.6,
        "bomba": "NÃO LIGAR - RISCO DE PERDA TOTAL",
        "economia_litros": 4200,
        "economia_reais": 38.00,
        "mensagem_acao": "Solo 100% encharcado e raiz sem oxigênio (-140 mV). Abra valetas de drenagem e emita o Laudo PROAGRO.",
        "laudo_proagro": True
    }
}


SOLOS_INFO = {
    "arenoso": {
        "id": "arenoso",
        "nome": "Solo Arenoso (Leve / Litoral)",
        "icone": "🏖️",
        "cc_kpa": 10.0,
        "estresse_kpa": 30.0,
        "descricao": "Drena rápido por gravidade. Estresse hídrico inicia cedo (30 kPa). Irrigação mais frequente."
    },
    "franco_arenoso": {
        "id": "franco_arenoso",
        "nome": "Solo Franco-Arenoso (Médio-Leve)",
        "icone": "🌾",
        "cc_kpa": 15.0,
        "estresse_kpa": 40.0,
        "descricao": "Textura média leve com boa drenagem e aeração equilibrada."
    },
    "franco": {
        "id": "franco",
        "nome": "Solo Franco / Médio",
        "icone": "🌾",
        "cc_kpa": 22.0,
        "estresse_kpa": 45.0,
        "descricao": "Textura média equilibrada. Retenção de água e aeração ideais."
    },
    "argiloso": {
        "id": "argiloso",
        "nome": "Solo Argiloso (Terra Roxa / Várzea)",
        "icone": "🧱",
        "cc_kpa": 33.0,
        "estresse_kpa": 65.0,
        "descricao": "Microporos retêm água com força. A capacidade de campo é em 33 kPa; não requer irrigação em 30 kPa."
    }
}


def calcular_economia_hectares(hectares: float) -> dict:
    """Calcula economia proporcional de água e energia por hectare monitorado."""
    hectares = max(1.0, min(15.0, float(hectares)))
    sensores = int(hectares * 1)  # 1 Planta Sentinela por talhão/hectare
    litros_poupados_mes = int(hectares * 4200 * 8)  # Média de 8 dias/mês de bomba desligada desnecessariamente
    reais_economizados_mes = round(hectares * 38.0 * 8, 2)

    return {
        "hectares": hectares,
        "sensores_sentinelas": sensores,
        "litros_poupados_mes": litros_poupados_mes,
        "reais_economizados_mes": reais_economizados_mes
    }


def obter_telemetria_tempo_real(backend_url: Optional[str] = None, tipo_solo: Optional[str] = None) -> Dict[str, Any]:
    """
    Consulta o backend FastAPI em busca da leitura em tempo real transmitida pelo ESP32 físico.
    Permite passar tipo_solo para que os limiares agronômicos sejam calibrados dinamicamente.
    Se o backend estiver offline ou inacessível, realiza fallback seguro para os dados locais simulados.
    """
    url_base = (backend_url or BACKEND_API_URL).rstrip("/")
    endpoint = f"{url_base}/api/telemetria/atual"
    params = {}
    if tipo_solo:
        params["tipo_solo"] = tipo_solo

    try:
        resp = requests.get(endpoint, params=params, timeout=1.5)
        if resp.status_code == 200:
            dados = resp.json()
            return {
                "online": True,
                "origem": dados.get("fonte", "fisico"),
                "sensor_fisico_online": dados.get("sensor_fisico_online", False),
                "node_id": dados.get("node_id", "sentinela-01"),
                "tipo_solo": dados.get("tipo_solo", tipo_solo or "franco"),
                "solo_nome": dados.get("solo_nome", "Solo Franco / Médio"),
                "agua_disponivel_pct": dados.get("agua_disponivel_pct", 85),
                "tensao_kpa": dados.get("tensao_kpa", 21.5),
                "z_50k_ohms": dados.get("z_50k_ohms", 1400.0),
                "z_1k_ohms": dados.get("z_1k_ohms", 1100.0),
                "orp_mv": dados.get("orp_mv", 310.0),
                "ce_dsm": dados.get("ce_dsm", 1.2),
                "estado": dados.get("estado", "hidratada"),
                "status_bomba": dados.get("status_bomba", "BOMBA DESLIGADA"),
                "acao_recomendada": dados.get("acao_recomendada", ""),
                "segundos_desde_leitura": dados.get("segundos_desde_leitura", 0.0)
            }
    except Exception:
        # Fallback resiliente
        pass

    solo_cfg = SOLOS_INFO.get(tipo_solo or "franco", SOLOS_INFO["franco"])
    return {
        "online": False,
        "origem": "fallback_local",
        "sensor_fisico_online": False,
        "node_id": "sentinela-01",
        "tipo_solo": tipo_solo or "franco",
        "solo_nome": solo_cfg["nome"],
        "agua_disponivel_pct": 85,
        "tensao_kpa": 21.5,
        "z_50k_ohms": 1400.0,
        "z_1k_ohms": 1100.0,
        "orp_mv": 310.0,
        "ce_dsm": 1.2,
        "estado": "hidratada",
        "status_bomba": "BOMBA DESLIGADA",
        "acao_recomendada": "Manter bomba desligada hoje. Seiva normal.",
        "segundos_desde_leitura": 0.0
    }


def obter_diagnostico_llm(
    telemetria: Dict[str, Any],
    pergunta: Optional[str] = None,
    backend_url: Optional[str] = None
) -> Dict[str, Any]:
    """
    Obtém diagnóstico fitoeletrônico inteligente para a mensagem de voz.
    Tenta conexão com o backend FastAPI (/api/llm/diagnostico).
    Caso o backend esteja inacessível ou em modo offline, invoca o motor
    especialista de fallback local (executar_diagnostico_fallback) em < 5ms.
    """
    url_base = (backend_url or BACKEND_API_URL).rstrip("/")
    endpoint = f"{url_base}/api/llm/diagnostico"

    # Clamping preventivo para tensao_kpa entre 0.0 e 250.0 (regra Pydantic)
    raw_tensao = telemetria.get("tensao_kpa", 21.5)
    try:
        tensao_kpa = max(0.0, min(250.0, float(raw_tensao)))
    except (TypeError, ValueError):
        tensao_kpa = 21.5

    payload = {
        "tensao_kpa": tensao_kpa,
        "tipo_solo": telemetria.get("tipo_solo", "franco"),
        "z_50k_ohms": float(telemetria.get("z_50k_ohms", 1400.0)),
        "z_1k_ohms": float(telemetria.get("z_1k_ohms", 1200.0)),
        "orp_mv": float(telemetria.get("orp_mv", 310.0)),
        "cultura": telemetria.get("cultura", "Milho"),
        "pergunta": pergunta or "Solicitação de diagnóstico da lavoura via áudio"
    }

    try:
        resp = requests.post(endpoint, json=payload, timeout=1.5)
        if resp.status_code == 200:
            dados = resp.json()
            diagnostico_texto = dados.get("diagnostico_texto", "")
            recomendacao = dados.get("recomendacao_manejo", "")
            resposta_formatada = f"{diagnostico_texto}\n\n💡 <b>Recomendação de Manejo:</b>\n{recomendacao}"
            return {
                "sucesso": True,
                "resposta": resposta_formatada,
                "dados": dados,
                "origem": dados.get("motor_utilizado", "backend_api")
            }
    except Exception:
        pass

    # Fallback fitoeletrônico instantâneo em memória (<5ms)
    try:
        from llm_engine import executar_diagnostico_fallback
    except ImportError:
        try:
            from backend.llm_engine import executar_diagnostico_fallback
        except ImportError:
            import sys
            _root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
            if _root not in sys.path:
                sys.path.insert(0, _root)
            from backend.llm_engine import executar_diagnostico_fallback

    fb = executar_diagnostico_fallback(
        tensao_kpa=payload["tensao_kpa"],
        tipo_solo=payload["tipo_solo"],
        z_50k_ohms=payload["z_50k_ohms"],
        z_1k_ohms=payload["z_1k_ohms"],
        orp_mv=payload["orp_mv"],
        cultura=payload["cultura"],
        pergunta=payload["pergunta"]
    )

    diagnostico_texto = fb.get("diagnostico_texto", "")
    recomendacao = fb.get("recomendacao_manejo", "")
    resposta_formatada = f"{diagnostico_texto}\n\n💡 <b>Recomendação de Manejo:</b>\n{recomendacao}"

    return {
        "sucesso": True,
        "resposta": resposta_formatada,
        "dados": fb,
        "origem": "fallback_local"
    }

