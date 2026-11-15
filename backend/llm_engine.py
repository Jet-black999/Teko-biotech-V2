"""
Tekó Biotech — Motor de Inferência LLM Local e Fallback Fitoeletrônico Especialista
Hackathon das Engenharias UERGS 2026 — Desafio 02: Água e Drenagem Rural

Este módulo fornece:
1. Cliente HTTP leve e assíncrono para LLM local (Ollama / Qwen 2.5 0.5B) com timeout estrito de 1.0s.
2. Motor especialista fitoeletrônico determinístico em memória (<50ms SLA, típico <5ms)
   baseado em modelos hidrofísicos Van Genuchten/Embrapa, bioimpedância dupla frequência
   (1 kHz apoplástico vs 50 kHz simplástico) e potencial redox (ORP) rizosférico.
3. Sanitização léxica ativa contra termos legados proibidos, garantindo conformidade
   com a identidade oficial da Tekó Biotech.
4. Resiliência de 3 camadas garantindo ausência de erros HTTP 500 mesmo sob indisponibilidade
   completa do servidor Ollama.
"""

import asyncio
import json
import math
import os
import re
import sys
import time
import unicodedata
from typing import Any, Dict, Optional, Tuple

import httpx

# Garante sincronização de sys.modules para interoperabilidade transparente
# entre execuções diretas ('llm_engine') e modulares ('backend.llm_engine')
_current_mod = sys.modules.get(__name__)
if _current_mod is not None:
    sys.modules.setdefault("llm_engine", _current_mod)
    sys.modules.setdefault("backend.llm_engine", _current_mod)

# ============================================================================
# CONFIGURAÇÕES E AMBIENTE (OLLAMA LOCAL)
# ============================================================================
OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "qwen2.5:0.5b").strip()
OLLAMA_TIMEOUT_SECONDS: float = float(os.getenv("OLLAMA_TIMEOUT_SECONDS", "1.0"))

_httpx_async_client: Optional[httpx.AsyncClient] = None

# ============================================================================
# CONSTANTES DE COMANDO HIDRÁULICO (SONAR S1192)
# ============================================================================
STATUS_BOMBA_NAO_LIGAR: str = "NÃO LIGAR A BOMBA!"
STATUS_BOMBA_LIGAR_06H: str = "LIGAR AMANHÃ ÀS 06H"
STATUS_BOMBA_DESLIGADA: str = "BOMBA DESLIGADA"

# ============================================================================
# POLÍTICA DE SEGURANÇA LÉXICA — FILTRO ANTI-TERMOS PROIBIDOS (SONAR S5843)
# ============================================================================
REGEX_TERMOS_PROIBIDOS = re.compile(
    r"\b(?:[aáàâã]?gro[- ]?sponge|cascas? de arroz|sacos? biodegrad[aá]ve[li]s?)\b",
    re.IGNORECASE
)

PADROES_TERMOS_PROIBIDOS = (
    (re.compile(r"\b[aáàâã]?gro[- ]?sp[oóôõ]nge\b", re.IGNORECASE), "biossensor fitoeletrônico in-planta Tekó"),
    (re.compile(r"\bcascas?\s+de\s+arroz\b", re.IGNORECASE), "substrato orgânico calibrado"),
    (re.compile(r"\bsacos?\s+biodegrad[aáàâã]ve(?:l|is)\b", re.IGNORECASE), "módulo de monitoramento"),
)

TERMOS_NORMALIZADOS_BLOQUEADOS = [
    "agrosponge",
    "agro sponge",
    "agro-sponge",
    "casca de arroz",
    "cascas de arroz",
    "saco biodegradavel",
    "sacos biodegradaveis",
]


def _substituir_termo_proibido(match: re.Match) -> str:
    termo = unicodedata.normalize("NFKD", match.group(0).lower())
    termo_sem_acento = "".join(c for c in termo if not unicodedata.combining(c))
    if "sponge" in termo_sem_acento:
        return "biossensor fitoeletrônico in-planta Tekó"
    if "arroz" in termo_sem_acento:
        return "substrato orgânico calibrado"
    if "biodegrad" in termo_sem_acento:
        return "módulo de monitoramento"
    return "tecnologia Tekó Biotech"


def sanitizar_texto(texto: str) -> str:
    """
    Substitui ativamente qualquer termo legado proibido por terminologia
    oficial da Tekó Biotech e valida a ausência de resíduos via normalização NFD/NFC.
    """
    if not texto:
        return ""
    atual = unicodedata.normalize("NFC", texto)
    for _ in range(3):
        if not REGEX_TERMOS_PROIBIDOS.search(atual):
            break
        atual = REGEX_TERMOS_PROIBIDOS.sub(_substituir_termo_proibido, atual)

    for padrao_compilado, subst in PADROES_TERMOS_PROIBIDOS:
        atual = padrao_compilado.sub(subst, atual)

    if not verificar_seguranca_termos(atual):
        for padrao in TERMOS_NORMALIZADOS_BLOQUEADOS:
            padrao_nfc = unicodedata.normalize("NFC", padrao)
            atual = re.sub(re.escape(padrao_nfc), "biossensor Tekó", atual, flags=re.IGNORECASE)
            padrao_com_acento = padrao_nfc.replace("biodegradavel", "biodegradável").replace(
                "biodegradaveis", "biodegradáveis"
            )
            atual = re.sub(re.escape(padrao_com_acento), "biossensor Tekó", atual, flags=re.IGNORECASE)

    return atual


def verificar_seguranca_termos(texto: str) -> bool:
    """
    Verifica de forma estrita e sem diacríticos (Unicode NFD) se o texto
    está 100% isento de termos obsoletos proibidos.
    """
    if not texto:
        return True
    if REGEX_TERMOS_PROIBIDOS.search(texto):
        return False
    for padrao_compilado, _ in PADROES_TERMOS_PROIBIDOS:
        if padrao_compilado.search(texto):
            return False
    nfkd = unicodedata.normalize("NFKD", texto)
    sem_acentos = "".join([c for c in nfkd if not unicodedata.combining(c)]).lower()
    if REGEX_TERMOS_PROIBIDOS.search(sem_acentos):
        return False
    for padrao in TERMOS_NORMALIZADOS_BLOQUEADOS:
        if padrao in sem_acentos:
            return False
    return True


# ============================================================================
# PARÂMETROS AGRONÔMICOS E HIDROFÍSICOS (VAN GENUCHTEN & EMBRAPA)
# ============================================================================
TABELA_SOLOS_PARAMETROS: Dict[str, Dict[str, Any]] = {
    "arenoso": {
        "nome": "Solo Arenoso (Leve / Litoral)",
        "cc_kpa": 10.0,
        "estresse_kpa": 30.0,
        "severo_kpa": 60.0,
        "murcha_kpa": 1500.0,
        "orientacao_bomba": "Irrigue com turnos frequentes e curtos (15-20 min). Em 30 kPa já necessita de irrigação preventiva."
    },
    "franco": {
        "nome": "Solo Franco / Médio",
        "cc_kpa": 22.0,
        "estresse_kpa": 45.0,
        "severo_kpa": 60.0,
        "murcha_kpa": 1500.0,
        "orientacao_bomba": "Gotejamento matinal programado para às 06h da manhã (35-45 min)."
    },
    "argiloso": {
        "nome": "Solo Argiloso (Terra Roxa / Várzea)",
        "cc_kpa": 33.0,
        "estresse_kpa": 65.0,
        "severo_kpa": 120.0,
        "murcha_kpa": 1500.0,
        "orientacao_bomba": "Alta retenção capilar. Irrigações espaçadas e drenagem preventiva."
    }
}

MAPEAMENTO_SOLOS_ALIAS: Dict[str, str] = {
    "areia": "arenoso",
    "arenoso": "arenoso",
    "areia franca": "arenoso",
    "franco-arenoso": "arenoso",
    "franco": "franco",
    "silte": "franco",
    "franco-siltoso": "franco",
    "franco-argilo-arenoso": "franco",
    "medio": "franco",
    "médio": "franco",
    "argiloso": "argiloso",
    "franco-argiloso": "argiloso",
    "franco-argilo-siltoso": "argiloso",
    "argilo-arenoso": "argiloso",
    "argila": "argiloso",
    "latossolo": "argiloso",
    "terra roxa": "argiloso"
}


def normalizar_tipo_solo(tipo_solo: Optional[str]) -> str:
    """Normaliza nomes de solo (11 classes Van Genuchten ou grupos genéricos) para arenoso, franco ou argiloso."""
    if not tipo_solo:
        return "franco"
    chave = tipo_solo.strip().lower()
    for alias in sorted(MAPEAMENTO_SOLOS_ALIAS.keys(), key=len, reverse=True):
        if alias in chave:
            return MAPEAMENTO_SOLOS_ALIAS[alias]
    return "franco"


def _calcular_agua_disponivel_pct(tensao: float, cfg_solo: Dict[str, Any]) -> int:
    """Calcula a porcentagem de água disponível (AD %) com base na curva de retenção."""
    if tensao <= cfg_solo["cc_kpa"]:
        return 100
    if tensao <= cfg_solo["estresse_kpa"]:
        fator = (tensao - cfg_solo["cc_kpa"]) / (cfg_solo["estresse_kpa"] - cfg_solo["cc_kpa"])
        return max(50, min(100, round(100.0 - (fator * 50.0))))
    if tensao <= cfg_solo["murcha_kpa"]:
        log_atual = math.log10(max(1.0, tensao))
        log_estresse = math.log10(cfg_solo["estresse_kpa"])
        log_murcha = math.log10(cfg_solo["murcha_kpa"])
        fator = (log_atual - log_estresse) / (log_murcha - log_estresse)
        return max(0, min(50, round(50.0 - (fator * 50.0))))
    return 0


def _montar_textos_sede(
    cultura_nome: str,
    cfg_solo: Dict[str, Any],
    tensao: float,
    z_50k: float,
    itr: float,
    ad_pct: int
) -> Tuple[str, str]:
    """Gera diagnóstico e recomendação para condição de estresse hídrico."""
    if z_50k >= 5500.0 or tensao >= cfg_solo["severo_kpa"]:
        diagnostico = (
            f"Estresse hídrico severo detectado em lavoura de {cultura_nome} ({cfg_solo['nome']}). "
            f"Bioimpedância simplástica crítica em {z_50k:.0f} Ω (>= 5.5 kΩ indica colapso/plasmólise celular), "
            f"tensão matricial em {tensao:.1f} kPa (limite crítico: {cfg_solo['estresse_kpa']:.1f} kPa) "
            f"e ITR: {itr}. Apenas {ad_pct}% de água disponível restante no solo."
        )
        recomendacao = (
            f"{STATUS_BOMBA_LIGAR_06H}. Aplicar lâmina de recuperação hídrica nas primeiras horas da manhã. "
            f"{cfg_solo['orientacao_bomba']}"
        )
        return diagnostico, recomendacao

    diagnostico = (
        f"Seca invisível detectada em lavoura de {cultura_nome} ({cfg_solo['nome']}). "
        f"Bioimpedância a 50 kHz atingiu {z_50k:.0f} Ω (>= 4.5 kΩ), sinalizando início de "
        f"desidratação celular e perda de turgor (ITR: {itr}) antes de qualquer murchamento visível das folhas. "
        f"Tensão do solo: {tensao:.1f} kPa com {ad_pct}% de água disponível."
    )
    recomendacao = (
        f"{STATUS_BOMBA_LIGAR_06H}. Programar turno de irrigação matinal às 06:00 para evitar estresse térmico. "
        f"{cfg_solo['orientacao_bomba']}"
    )
    return diagnostico, recomendacao


# ============================================================================
# MOTOR ESPECIALISTA FITOELETRÔNICO DETERMINÍSTICO (FALLBACK < 50ms)
# ============================================================================
def executar_diagnostico_fallback(
    tensao_kpa: float,
    tipo_solo: Optional[str] = "franco",
    z_50k_ohms: Optional[float] = 1400.0,
    z_1k_ohms: Optional[float] = 1200.0,
    orp_mv: Optional[float] = 310.0,
    cultura: Optional[str] = "Milho",
    pergunta: Optional[str] = None,
    t_inicio: Optional[float] = None
) -> Dict[str, Any]:
    """
    Executa diagnóstico fitoeletrônico determinístico em memória local.
    SLA < 50ms (benchmark típico < 5ms).
    """
    if t_inicio is None:
        t_inicio = time.perf_counter()

    tensao = max(0.0, float(tensao_kpa))
    z_50k = max(10.0, float(z_50k_ohms if z_50k_ohms is not None else 1400.0))
    z_1k = max(10.0, float(z_1k_ohms if z_1k_ohms is not None else 1200.0))
    orp = float(orp_mv if orp_mv is not None else 310.0)
    cultura_nome = cultura.strip() if cultura else "Milho"

    solo_chave = normalizar_tipo_solo(tipo_solo)
    cfg_solo = TABELA_SOLOS_PARAMETROS[solo_chave]
    itr = round(z_1k / z_50k, 3)
    ad_pct = _calcular_agua_disponivel_pct(tensao, cfg_solo)

    limite_hipoxia_kpa = cfg_solo["cc_kpa"] * 0.45
    eh_hipoxia = (orp < -100.0) or (tensao < limite_hipoxia_kpa)
    eh_sede = (tensao > cfg_solo["estresse_kpa"]) or (z_50k >= 4500.0)

    if eh_hipoxia:
        estado_planta = "hipoxia"
        bomba_status = STATUS_BOMBA_NAO_LIGAR
        diagnostico_texto = (
            f"Alerta crítico de asfixia radicular em lavoura de {cultura_nome} "
            f"({cfg_solo['nome']}). Potencial Redox rizosférico colapsou para {orp:.1f} mV "
            f"(referência normal: >= +200 mV) e tensão matricial em {tensao:.1f} kPa. "
            f"O solo está saturado e anóxico. As aquaporinas das raízes foram desativadas "
            f"por falta de ATP celular, gerando seca fisiológica. Z_50k: {z_50k:.0f} Ω, ITR: {itr}."
        )
        recomendacao_manejo = (
            "NÃO LIGAR A BOMBA! Risco iminente de perda radicular total e infecção por patógenos "
            "anaeróbios (Phytophthora/Pythium). Ação corretiva imediata: abrir valetas de "
            "drenagem na cabeceira da lavoura e preparar laudo pericial para o PROAGRO."
        )
    elif eh_sede:
        estado_planta = "sede"
        bomba_status = STATUS_BOMBA_LIGAR_06H
        diagnostico_texto, recomendacao_manejo = _montar_textos_sede(
            cultura_nome, cfg_solo, tensao, z_50k, itr, ad_pct
        )
    else:
        estado_planta = "hidratada"
        bomba_status = STATUS_BOMBA_DESLIGADA
        diagnostico_texto = (
            f"Lavoura de {cultura_nome} em pleno equilíbrio fisiológico e hídrico ({cfg_solo['nome']}). "
            f"Tensão matricial ótima em {tensao:.1f} kPa (Capacidade de Campo: {cfg_solo['cc_kpa']:.1f} kPa), "
            f"água disponível em {ad_pct}%, Z_50k em {z_50k:.0f} Ω (células túrgidas, faixa 1.2-1.8 kΩ), "
            f"ITR em {itr} e rizosfera oxigenada (ORP: {orp:.1f} mV)."
        )
        recomendacao_manejo = (
            "BOMBA DESLIGADA. Solo com reserva hídrica ideal e aeração adequada. "
            "Manter irrigação desligada para economia de recursos hídricos e energia elétrica."
        )

    if pergunta:
        diagnostico_texto = f"Consulta: '{pergunta.strip()}'. {diagnostico_texto}"

    diagnostico_limpo = sanitizar_texto(diagnostico_texto)
    recomendacao_limpa = sanitizar_texto(recomendacao_manejo)

    if estado_planta == "hipoxia":
        bomba_status = STATUS_BOMBA_NAO_LIGAR

    seguranca_ok = bool(
        verificar_seguranca_termos(diagnostico_limpo)
        and verificar_seguranca_termos(recomendacao_limpa)
    )
    tempo_resposta_ms = round((time.perf_counter() - t_inicio) * 1000.0, 3)

    return {
        "status": "sucesso",
        "estado_planta": estado_planta,
        "bomba_status": bomba_status,
        "tempo_resposta_ms": tempo_resposta_ms,
        "motor_utilizado": "motor_especialista_fallback",
        "diagnostico_texto": diagnostico_limpo,
        "recomendacao_manejo": recomendacao_limpa,
        "seguranca_termos_antigos": seguranca_ok
    }


# ============================================================================
# CLIENTE HTTP LEVE PARA OLLAMA LOCAL
# ============================================================================
def construir_prompt_fitoeletronico(
    tensao_kpa: float,
    tipo_solo: str,
    z_50k_ohms: float,
    z_1k_ohms: float,
    orp_mv: float,
    cultura: str,
    pergunta: Optional[str] = None
) -> str:
    """Monta prompt técnico estruturado orientando a LLM a retornar JSON estrito."""
    itr = round(z_1k_ohms / max(1.0, z_50k_ohms), 3)
    consulta_secao = f"\nPergunta do Produtor: '{pergunta.strip()}'" if pergunta else ""

    return (
        "Você é o especialista fitoeletrônico da Tekó Biotech. "
        "Analise os dados in-planta e retorne APENAS um objeto JSON válido (sem blocos markdown adicionais):\n"
        "Regras fisiológicas inegociáveis:\n"
        f"- Hipóxia/Alagamento (ORP < -100 mV ou solo alagado): estado_planta='hipoxia', bomba_status='{STATUS_BOMBA_NAO_LIGAR}' (Paradoxo da enchente: falta de ATP celular fecha aquaporinas gerando seca fisiológica; irrigar mata raízes).\n"
        f"- Seca/Estresse hídrico (Tensão elevada ou Z_50k >= 4500 Ω): estado_planta='sede', bomba_status='{STATUS_BOMBA_LIGAR_06H}'.\n"
        f"- Turgidez ideal (Z_50k entre 1200 e 1800 Ω, solo na capacidade de campo): estado_planta='hidratada', bomba_status='{STATUS_BOMBA_DESLIGADA}'.\n"
        "POLÍTICA TERMINOLÓGICA: NUNCA utilize termos como agrosponge, casca de arroz ou saco biodegradavel. Utilize apenas biossensor fitoeletrônico in-planta Tekó e substrato orgânico calibrado.\n\n"
        f"Dados de Telemetria:\n"
        f"- Cultura: {cultura}\n"
        f"- Solo: {tipo_solo}\n"
        f"- Tensão Matricial: {tensao_kpa:.1f} kPa\n"
        f"- Bioimpedância Simplástica (50 kHz): {z_50k_ohms:.0f} Ohms\n"
        f"- Bioimpedância Apoplástica (1 kHz): {z_1k_ohms:.0f} Ohms (ITR: {itr})\n"
        f"- Potencial Redox (ORP): {orp_mv:.1f} mV\n"
        f"{consulta_secao}\n\n"
        'Responda no formato JSON exato: {"estado_planta": "hidratada|sede|hipoxia", "bomba_status": "BOMBA DESLIGADA|LIGAR AMANHÃ ÀS 06H|NÃO LIGAR A BOMBA!", "diagnostico_texto": "...", "recomendacao_manejo": "..."}'
    )


def _limpar_markdown_json(corpo_resposta: str) -> str:
    limpo = corpo_resposta.strip()
    if limpo.startswith("```json"):
        limpo = limpo[7:]
    elif limpo.startswith("```"):
        limpo = limpo[3:]
    if limpo.endswith("```"):
        limpo = limpo[:-3]
    return limpo.strip()


async def chamar_ollama_local(
    prompt: str,
    base_url: Optional[str] = None,
    model: Optional[str] = None,
    timeout_s: Optional[float] = None
) -> Optional[Dict[str, Any]]:
    """
    Executa chamada HTTP assíncrona para a API do Ollama local (`POST /api/generate`).
    """
    url_base = (base_url or OLLAMA_BASE_URL).rstrip("/")
    endpoint = f"{url_base}/api/generate"
    modelo = model or OLLAMA_MODEL
    timeout_val = timeout_s if timeout_s is not None else OLLAMA_TIMEOUT_SECONDS

    payload = {
        "model": modelo,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.2, "num_predict": 220}
    }

    try:
        timeout_cfg = httpx.Timeout(timeout_val, connect=0.5)
        async with httpx.AsyncClient(timeout=timeout_cfg) as client:
            resposta = await client.post(endpoint, json=payload)
            if resposta.status_code != 200:
                return None
            corpo_resposta = resposta.json().get("response", "")
            if not corpo_resposta:
                return None
            parsed = json.loads(_limpar_markdown_json(corpo_resposta))
            return parsed if isinstance(parsed, dict) else None
    except Exception:
        return None


# ============================================================================
# AUXILIARES DE ORQUESTRAÇÃO E TRAVA SOBERANA (SONAR S3776)
# ============================================================================
def _extrair_parametros_entrada(dados: Any) -> Optional[Dict[str, Any]]:
    """Extrai e normaliza parâmetros de modelo Pydantic ou dicionário."""
    if hasattr(dados, "tensao_kpa"):
        return {
            "tensao_kpa": float(dados.tensao_kpa),
            "tipo_solo": getattr(dados, "tipo_solo", "franco") or "franco",
            "z_50k_ohms": float(getattr(dados, "z_50k_ohms", 1400.0) or 1400.0),
            "z_1k_ohms": float(getattr(dados, "z_1k_ohms", 1200.0) or 1200.0),
            "orp_mv": float(getattr(dados, "orp_mv", 310.0) or 310.0),
            "cultura": getattr(dados, "cultura", "Milho") or "Milho",
            "pergunta": getattr(dados, "pergunta", None),
        }
    if isinstance(dados, dict):
        return {
            "tensao_kpa": float(dados.get("tensao_kpa", 22.0)),
            "tipo_solo": dados.get("tipo_solo", "franco") or "franco",
            "z_50k_ohms": float(dados.get("z_50k_ohms", 1400.0) or 1400.0),
            "z_1k_ohms": float(dados.get("z_1k_ohms", 1200.0) or 1200.0),
            "orp_mv": float(dados.get("orp_mv", 310.0) or 310.0),
            "cultura": dados.get("cultura", "Milho") or "Milho",
            "pergunta": dados.get("pergunta"),
        }
    return None


def _normalizar_estado_e_bomba(
    resultado_llm: Dict[str, Any],
    eh_hipoxia_fisica: bool,
    tensao_kpa: float,
    z_50k_ohms: float,
    estresse_kpa: float
) -> Tuple[str, str]:
    """Normaliza o estado fisiológico e o comando de bomba caso a LLM retorne valores fora do contrato."""
    estado = str(resultado_llm.get("estado_planta", "")).strip().lower()
    if estado not in ("hidratada", "sede", "hipoxia"):
        if eh_hipoxia_fisica:
            estado = "hipoxia"
        elif tensao_kpa > estresse_kpa or z_50k_ohms >= 4500.0:
            estado = "sede"
        else:
            estado = "hidratada"

    mapa_bomba_padrao = {
        "hipoxia": STATUS_BOMBA_NAO_LIGAR,
        "sede": STATUS_BOMBA_LIGAR_06H,
        "hidratada": STATUS_BOMBA_DESLIGADA,
    }
    bomba = str(resultado_llm.get("bomba_status", "")).strip().upper()
    if bomba not in (STATUS_BOMBA_DESLIGADA, STATUS_BOMBA_LIGAR_06H, STATUS_BOMBA_NAO_LIGAR):
        bomba = mapa_bomba_padrao[estado]

    return estado, bomba


def _aplicar_trava_soberana_hipoxia(
    resultado_llm: Dict[str, Any],
    diagnostico_limpo: str,
    recomendacao_limpa: str
) -> Tuple[str, str]:
    """Aplica o aviso do Paradoxo da Enchente se a LLM sugeriu irrigação sob hipóxia."""
    aviso_paradoxo = (
        "Alerta: sob anóxia/hipóxia radicular (ORP < -100 mV), as aquaporinas estão inibidas "
        "(Paradoxo da Enchente). A motobomba deve permanecer estritamente DESLIGADA."
    )
    termos_irrigacao = ("ligar", "irrig", "regar", "acionar bomba", "lâmina", "lamina")
    recomendou_irrigar = (
        str(resultado_llm.get("bomba_status", "")).strip().upper() == STATUS_BOMBA_LIGAR_06H
        or str(resultado_llm.get("estado_planta", "")).strip().lower() == "sede"
        or any(t in recomendacao_limpa.lower() for t in termos_irrigacao)
        or any(t in diagnostico_limpo.lower() for t in termos_irrigacao[:4])
    )
    if recomendou_irrigar:
        if aviso_paradoxo not in recomendacao_limpa:
            recomendacao_limpa = f"{aviso_paradoxo} {recomendacao_limpa}".strip()
        if aviso_paradoxo not in diagnostico_limpo:
            diagnostico_limpo = f"{aviso_paradoxo} {diagnostico_limpo}".strip()
    return diagnostico_limpo, recomendacao_limpa


# ============================================================================
# ORQUESTRADOR CENTRAL DE DIAGNÓSTICO LLM COM TOLERÂNCIA A FALHAS
# ============================================================================
async def processar_diagnostico_llm(
    dados: Any,
    t_inicio: Optional[float] = None
) -> Dict[str, Any]:
    """
    Ponto de entrada principal para inferência agronômica com fallback <50ms.
    """
    if t_inicio is None:
        t_inicio = time.perf_counter()

    params = _extrair_parametros_entrada(dados)
    if params is None:
        return executar_diagnostico_fallback(tensao_kpa=22.0, t_inicio=t_inicio)

    solo_chave = normalizar_tipo_solo(params["tipo_solo"])
    cfg_solo = TABELA_SOLOS_PARAMETROS[solo_chave]
    eh_hipoxia_fisica = (params["orp_mv"] < -100.0) or (params["tensao_kpa"] < cfg_solo["cc_kpa"] * 0.45)

    prompt = construir_prompt_fitoeletronico(**params)
    try:
        resultado_llm = await chamar_ollama_local(prompt)
    except Exception:
        resultado_llm = None

    if not isinstance(resultado_llm, dict):
        return executar_diagnostico_fallback(**params, t_inicio=t_inicio)

    diagnostico_raw = str(resultado_llm.get("diagnostico_texto", "")).strip()
    recomendacao_raw = str(resultado_llm.get("recomendacao_manejo", "")).strip()
    if not diagnostico_raw or not recomendacao_raw:
        return executar_diagnostico_fallback(**params, t_inicio=t_inicio)

    estado, bomba = _normalizar_estado_e_bomba(
        resultado_llm, eh_hipoxia_fisica, params["tensao_kpa"], params["z_50k_ohms"], cfg_solo["estresse_kpa"]
    )
    diagnostico_limpo = sanitizar_texto(diagnostico_raw)
    recomendacao_limpa = sanitizar_texto(recomendacao_raw)

    if eh_hipoxia_fisica:
        estado = "hipoxia"
        bomba = STATUS_BOMBA_NAO_LIGAR
        diagnostico_limpo, recomendacao_limpa = _aplicar_trava_soberana_hipoxia(
            resultado_llm, diagnostico_limpo, recomendacao_limpa
        )

    if estado == "hipoxia":
        bomba = STATUS_BOMBA_NAO_LIGAR

    seguranca_ok = bool(
        verificar_seguranca_termos(diagnostico_limpo)
        and verificar_seguranca_termos(recomendacao_limpa)
    )
    tempo_ms = round((time.perf_counter() - t_inicio) * 1000.0, 3)

    return {
        "status": "sucesso",
        "estado_planta": estado,
        "bomba_status": bomba,
        "tempo_resposta_ms": tempo_ms,
        "motor_utilizado": "ollama_local",
        "diagnostico_texto": diagnostico_limpo,
        "recomendacao_manejo": recomendacao_limpa,
        "seguranca_termos_antigos": seguranca_ok
    }


# ============================================================================
# CICLO DE VIDA (LIFESPAN COMPLIANCE)
# ============================================================================
async def inicializar_llm_engine():
    """Inicialização não-bloqueante no lifespan do FastAPI."""
    global _httpx_async_client
    try:
        await asyncio.sleep(0)
        _httpx_async_client = httpx.AsyncClient(timeout=httpx.Timeout(OLLAMA_TIMEOUT_SECONDS, connect=0.5))
        print(f"[LLM Engine] Motor inicializado (Ollama: {OLLAMA_BASE_URL}, Modelo: {OLLAMA_MODEL}). Fallback ativo.")
    except Exception as exc:
        print(f"[LLM Engine] Inicialização em modo fallback determinístico: {exc}")


async def fechar_llm_engine():
    """Liberação de recursos no encerramento da aplicação."""
    global _httpx_async_client
    if _httpx_async_client is not None:
        try:
            await _httpx_async_client.aclose()
        except Exception:
            pass
        _httpx_async_client = None
