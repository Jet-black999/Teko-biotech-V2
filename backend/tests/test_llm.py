"""
Suíte de Testes Automatizados para Motor LLM Local e Fallback Fitoeletrônico
Hackathon das Engenharias UERGS 2026 — Desafio 02: Água e Drenagem Rural
Milestone 3 / PR 2 (feat/llm-local-biossensor)

Cobre:
1. Classificação agronômica e fitoeletrônica (Hidratada, Sede, Hipóxia / Paradoxo da Enchente).
2. Diferenciação hidrofísica por tipo de solo (arenoso, franco, argiloso, 11 classes Van Genuchten).
3. Resiliência do cliente Ollama (sucesso mockado, conexão recusada, timeout, JSON inválido).
4. Desempenho e latência do fallback determinístico (< 50ms SLA, benchmark < 5ms).
5. Sanitização léxica estrita contra termos legados proibidos (agrosponge, casca de arroz, saco biodegradável).
6. Conformidade com contratos de API FastAPI (POST /api/llm/diagnostico, validações Pydantic V2 422 e tolerância a falhas sem erro 500).
"""

import asyncio
import os
import sys
import time
import unicodedata
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient

# Adiciona o diretório raiz do projeto ao sys.path
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from backend.llm_engine import (
    TABELA_SOLOS_PARAMETROS,
    chamar_ollama_local,
    construir_prompt_fitoeletronico,
    executar_diagnostico_fallback,
    normalizar_tipo_solo,
    processar_diagnostico_llm,
    sanitizar_texto,
    verificar_seguranca_termos,
)
from backend.server import DiagnosticoLLMIn, DiagnosticoLLMOut, app

client = TestClient(app)


# ============================================================================
# 1. TESTES DO MOTOR ESPECIALISTA FITOELETRÔNICO (FALLBACK DETERMINÍSTICO)
# ============================================================================

def test_fallback_hidratada_solo_franco():
    """Solo franco na Capacidade de Campo (22 kPa), células túrgidas (1400 Ω) e ORP positivo."""
    res = executar_diagnostico_fallback(
        tensao_kpa=22.0,
        tipo_solo="franco",
        z_50k_ohms=1400.0,
        z_1k_ohms=1200.0,
        orp_mv=310.0,
        cultura="Milho"
    )
    assert res["status"] == "sucesso"
    assert res["estado_planta"] == "hidratada"
    assert res["bomba_status"] == "BOMBA DESLIGADA"
    assert res["motor_utilizado"] == "motor_especialista_fallback"
    assert res["seguranca_termos_antigos"] is True
    assert "equilíbrio fisiológico" in res["diagnostico_texto"].lower()


def test_fallback_hidratada_solo_arenoso():
    """Solo arenoso com alta umidade (8.0 kPa <= 10.0 kPa CC)."""
    res = executar_diagnostico_fallback(
        tensao_kpa=8.0,
        tipo_solo="arenoso",
        z_50k_ohms=1300.0,
        z_1k_ohms=1100.0,
        orp_mv=280.0
    )
    assert res["estado_planta"] == "hidratada"
    assert res["bomba_status"] == "BOMBA DESLIGADA"


def test_fallback_hidratada_solo_argiloso():
    """Solo argiloso com retenção ideal (28.0 kPa <= 33.0 kPa CC)."""
    res = executar_diagnostico_fallback(
        tensao_kpa=28.0,
        tipo_solo="argiloso",
        z_50k_ohms=1500.0,
        z_1k_ohms=1300.0,
        orp_mv=320.0
    )
    assert res["estado_planta"] == "hidratada"
    assert res["bomba_status"] == "BOMBA DESLIGADA"


def test_fallback_sede_precoce_solo_franco():
    """Déficit hídrico no solo franco (> 45 kPa) e desidratação celular in-planta (Z_50k >= 4500 Ω)."""
    res = executar_diagnostico_fallback(
        tensao_kpa=48.0,
        tipo_solo="franco",
        z_50k_ohms=4600.0,
        z_1k_ohms=3200.0,
        orp_mv=350.0,
        cultura="Milho"
    )
    assert res["estado_planta"] == "sede"
    assert res["bomba_status"] == "LIGAR AMANHÃ ÀS 06H"
    assert "seca invisível" in res["diagnostico_texto"].lower()


def test_fallback_sede_precoce_solo_arenoso():
    """No solo arenoso, 32 kPa já ultrapassa o ponto crítico de estresse (30 kPa)."""
    res = executar_diagnostico_fallback(
        tensao_kpa=32.0,
        tipo_solo="arenoso",
        z_50k_ohms=3800.0,
        orp_mv=310.0
    )
    assert res["estado_planta"] == "sede"
    assert res["bomba_status"] == "LIGAR AMANHÃ ÀS 06H"


def test_fallback_sede_severa_argiloso():
    """Estresse hídrico severo com plasmólise celular (Z_50k >= 5500 Ω e tensão > 65 kPa)."""
    res = executar_diagnostico_fallback(
        tensao_kpa=75.0,
        tipo_solo="argiloso",
        z_50k_ohms=5800.0,
        z_1k_ohms=3900.0,
        orp_mv=380.0
    )
    assert res["estado_planta"] == "sede"
    assert res["bomba_status"] == "LIGAR AMANHÃ ÀS 06H"
    assert "severo" in res["diagnostico_texto"].lower()


def test_fallback_hipoxia_orp_negativo():
    """Anóxia na rizosfera pós-enchente detectada por ORP colapsado (-140 mV < -100 mV)."""
    res = executar_diagnostico_fallback(
        tensao_kpa=12.0,
        tipo_solo="franco",
        z_50k_ohms=2800.0,
        orp_mv=-140.0,
        cultura="Tomate"
    )
    assert res["estado_planta"] == "hipoxia"
    assert res["bomba_status"] == "NÃO LIGAR A BOMBA!"
    assert "asfixia radicular" in res["diagnostico_texto"].lower()
    assert "drenagem" in res["recomendacao_manejo"].lower()


def test_fallback_hipoxia_saturacao_zero_kpa():
    """Saturação completa do solo pós-inundação (0.0 kPa < limite hipóxia)."""
    res = executar_diagnostico_fallback(
        tensao_kpa=0.0,
        tipo_solo="argiloso",
        orp_mv=-80.0
    )
    assert res["estado_planta"] == "hipoxia"
    assert res["bomba_status"] == "NÃO LIGAR A BOMBA!"


def test_fallback_hipoxia_paradoxo_enchente_prioridade_absoluta():
    """
    PARADOXO DA ENCHENTE (SECA FISIOLÓGICA):
    Mesmo com Z_50k alto (>= 4500 Ω) simulando desidratação foliar, se o ORP for < -100 mV
    a causa é a asfixia radicular (falta de ATP fechando aquaporinas).
    A bomba NUNCA deve ser ligada!
    """
    res = executar_diagnostico_fallback(
        tensao_kpa=2.0,
        tipo_solo="franco",
        z_50k_ohms=5200.0,  # Impedância elevada por perda de turgor fisiológico
        orp_mv=-150.0       # Anóxia severa pós-enchente
    )
    assert res["estado_planta"] == "hipoxia"
    assert res["bomba_status"] == "NÃO LIGAR A BOMBA!"
    assert "aquaporinas" in res["diagnostico_texto"].lower()


def test_fallback_latencia_estrita_menor_50ms():
    """O motor especialista de fallback deve responder em estritos < 50ms (benchmark < 5ms)."""
    tempos = []
    for _ in range(50):
        t0 = time.perf_counter()
        res = executar_diagnostico_fallback(
            tensao_kpa=35.0,
            tipo_solo="franco",
            z_50k_ohms=2200.0,
            orp_mv=290.0
        )
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        tempos.append(elapsed_ms)
        assert res["tempo_resposta_ms"] < 50.0

    media_ms = sum(tempos) / len(tempos)
    assert media_ms < 5.0, f"Média de fallback ({media_ms:.3f} ms) excedeu benchmark de 5 ms"


# ============================================================================
# 2. TESTES DE NORMALIZAÇÃO DE SOLOS E ROBUSTEZ HIDROFÍSICA
# ============================================================================

def test_normalizacao_solos_van_genuchten():
    """Mapeamento das 11 classes texturais Embrapa/Van Genuchten para os 3 regimes de manejo."""
    assert normalizar_tipo_solo("Areia") == "arenoso"
    assert normalizar_tipo_solo("Areia Franca") == "arenoso"
    assert normalizar_tipo_solo("Franco-Arenoso") == "arenoso"
    assert normalizar_tipo_solo("Franco") == "franco"
    assert normalizar_tipo_solo("Silte") == "franco"
    assert normalizar_tipo_solo("Franco-Siltoso") == "franco"
    assert normalizar_tipo_solo("Franco-Argilo-Arenoso") == "franco"
    assert normalizar_tipo_solo("Franco-Argiloso") == "argiloso"
    assert normalizar_tipo_solo("Franco-Argilo-Siltoso") == "argiloso"
    assert normalizar_tipo_solo("Argilo-Arenoso") == "argiloso"
    assert normalizar_tipo_solo("Argiloso") == "argiloso"
    assert normalizar_tipo_solo("Latossolo") == "argiloso"
    assert normalizar_tipo_solo("Terra Roxa") == "argiloso"


def test_normalizacao_solo_desconhecido_fallback_seguro():
    """Solo desconhecido ou nulo adota 'franco' por segurança regional."""
    assert normalizar_tipo_solo("pedregoso") == "franco"
    assert normalizar_tipo_solo(None) == "franco"
    assert normalizar_tipo_solo("") == "franco"


# ============================================================================
# 3. TESTES DA POLÍTICA ANTI-TERMOS PROIBIDOS E SANITIZAÇÃO LÉXICA
# ============================================================================

def test_sanitizacao_termos_proibidos_agrosponge():
    """Identifica e substitui agrosponge e suas variações com traço, espaço e caixa alta."""
    textos = [
        "Instalamos o agrosponge na raiz.",
        "O AgroSponge RS foi calibrado.",
        "Utilize o AGRO-SPONGE no vaso.",
        "Verifique o agro sponge no solo."
    ]
    for txt in textos:
        san = sanitizar_texto(txt)
        assert "agrosponge" not in san.lower()
        assert "agro sponge" not in san.lower()
        assert "agro-sponge" not in san.lower()
        assert verificar_seguranca_termos(san) is True


def test_sanitizacao_termos_proibidos_casca_arroz():
    """Identifica e substitui casca(s) de arroz."""
    textos = [
        "Misture casca de arroz carbonizada.",
        "Uso de cascas de arroz no plantio."
    ]
    for txt in textos:
        san = sanitizar_texto(txt)
        assert "casca de arroz" not in san.lower()
        assert "cascas de arroz" not in san.lower()
        assert verificar_seguranca_termos(san) is True


def test_sanitizacao_termos_proibidos_saco_biodegradavel():
    """Identifica e substitui variações no singular, plural, com e sem acento."""
    textos = [
        "Coloque no saco biodegradável com água.",
        "Uso de saco biodegradavel no campo.",
        "Aplicação de sacos biodegradáveis nas covas.",
        "Reutilize os sacos biodegradaveis."
    ]
    for txt in textos:
        san = sanitizar_texto(txt)
        assert "saco biodegradavel" not in san.lower()
        assert "saco biodegradável" not in san.lower()
        assert "sacos biodegradaveis" not in san.lower()
        assert "sacos biodegradáveis" not in san.lower()
        assert verificar_seguranca_termos(san) is True


def test_sanitizacao_unicode_nfd():
    """Valida neutralização de caracteres combinantes NFD para prevenir evasão por diacríticos."""
    termo_nfd = unicodedata.normalize("NFD", "saco biodegradável")
    sanitizado = sanitizar_texto(termo_nfd)
    assert "saco biodegradavel" not in sanitizado.lower()
    assert "saco biodegradável" not in sanitizado.lower()
    assert verificar_seguranca_termos(sanitizado) is True

    # Outros casos NFD e acentuações compostas
    casca_nfd = unicodedata.normalize("NFD", "cascas de arroz")
    san_casca = sanitizar_texto(casca_nfd)
    assert "casca de arroz" not in san_casca.lower()
    assert verificar_seguranca_termos(san_casca) is True

    agro_acento = "ÁgroSpônge"
    san_agro = sanitizar_texto(agro_acento)
    assert "agrosponge" not in san_agro.lower()
    assert "agro sponge" not in san_agro.lower()
    assert verificar_seguranca_termos(san_agro) is True


def test_sanitizacao_injecao_adversarial_na_pergunta():
    """Se o produtor rural ou LLM injetar termos proibidos, o motor sanitiza antes de retornar."""
    pergunta_maliciosa = "O agrosponge com casca de arroz e saco biodegradavel vai salvar minha lavoura?"
    res = executar_diagnostico_fallback(
        tensao_kpa=22.0,
        pergunta=pergunta_maliciosa
    )
    assert res["seguranca_termos_antigos"] is True
    assert "agrosponge" not in res["diagnostico_texto"].lower()
    assert "casca de arroz" not in res["diagnostico_texto"].lower()
    assert "saco biodegradavel" not in res["diagnostico_texto"].lower()
    assert "saco biodegradável" not in res["diagnostico_texto"].lower()


def test_verificar_seguranca_termos_texto_limpo():
    """Textos puramente técnicos Tekó Biotech passam com True sem alteração."""
    texto_teko = "Biossensor fitoeletrônico in-planta Tekó com clipe biocompatível KCl e sonda redox ORP."
    assert verificar_seguranca_termos(texto_teko) is True
    assert sanitizar_texto(texto_teko) == texto_teko


# ============================================================================
# 4. TESTES DO CLIENTE OLLAMA LOCAL E ORQUESTRADOR COM TOLERÂNCIA A FALHAS
# ============================================================================

def test_construir_prompt_fitoeletronico():
    """Verifica formatação do prompt e presença das diretivas inegociáveis."""
    prompt = construir_prompt_fitoeletronico(
        tensao_kpa=45.0,
        tipo_solo="franco",
        z_50k_ohms=4800.0,
        z_1k_ohms=3600.0,
        orp_mv=310.0,
        cultura="Milho",
        pergunta="Devo ligar a bomba hoje?"
    )
    assert "Tekó Biotech" in prompt
    assert "Devo ligar a bomba hoje?" in prompt
    assert "NUNCA utilize termos como agrosponge" in prompt
    assert "45.0 kPa" in prompt


@pytest.mark.anyio
async def test_ollama_sucesso_mockado():
    """Simula resposta JSON válida do Ollama local."""
    resposta_simulada = {
        "response": '{"estado_planta": "sede", "bomba_status": "LIGAR AMANHÃ ÀS 06H", "diagnostico_texto": "Estresse moderado.", "recomendacao_manejo": "Irrigação matinal programada."}'
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = resposta_simulada

    with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp

        dados = DiagnosticoLLMIn(
            tensao_kpa=48.0,
            tipo_solo="franco",
            z_50k_ohms=4600.0,
            orp_mv=310.0
        )
        res = await processar_diagnostico_llm(dados)

        assert res["status"] == "sucesso"
        assert res["motor_utilizado"] == "ollama_local"
        assert res["estado_planta"] == "sede"
        assert res["bomba_status"] == "LIGAR AMANHÃ ÀS 06H"
        assert res["seguranca_termos_antigos"] is True


@pytest.mark.anyio
async def test_ollama_indisponivel_fallback_imediato():
    """Simula Ollama desligado (ConnectError) -> aciona fallback sem delay e sem 500."""
    with patch.object(httpx.AsyncClient, "post", side_effect=httpx.ConnectError("Connection refused")):
        dados = DiagnosticoLLMIn(
            tensao_kpa=22.0,
            tipo_solo="franco",
            z_50k_ohms=1400.0,
            orp_mv=310.0
        )
        res = await processar_diagnostico_llm(dados)

        assert res["status"] == "sucesso"
        assert res["motor_utilizado"] == "motor_especialista_fallback"
        assert res["estado_planta"] == "hidratada"
        assert res["bomba_status"] == "BOMBA DESLIGADA"


@pytest.mark.anyio
async def test_ollama_timeout_fallback():
    """Simula timeout da LLM (> 1.0s) -> chaveia imediatamente para fallback."""
    with patch.object(httpx.AsyncClient, "post", side_effect=httpx.TimeoutException("Read timed out")):
        dados = DiagnosticoLLMIn(
            tensao_kpa=5.0,
            orp_mv=-120.0
        )
        res = await processar_diagnostico_llm(dados)

        assert res["motor_utilizado"] == "motor_especialista_fallback"
        assert res["estado_planta"] == "hipoxia"
        assert res["bomba_status"] == "NÃO LIGAR A BOMBA!"


@pytest.mark.anyio
async def test_ollama_retorno_invalido_fallback():
    """Simula resposta não-JSON ou erro 500 do Ollama -> fallback resiliente."""
    mock_resp = MagicMock()
    mock_resp.status_code = 500
    mock_resp.json.return_value = {"error": "model out of memory"}

    with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp

        dados = DiagnosticoLLMIn(tensao_kpa=22.0)
        res = await processar_diagnostico_llm(dados)

        assert res["motor_utilizado"] == "motor_especialista_fallback"
        assert res["status"] == "sucesso"


@pytest.mark.anyio
async def test_seguranca_termos_antigos_dinamico():
    """Valida cálculo dinâmico da flag seguranca_termos_antigos tanto no fallback quanto na LLM."""
    # Cenário seguro determinístico (fallback)
    res_fallback_seguro = executar_diagnostico_fallback(tensao_kpa=22.0)
    assert res_fallback_seguro["seguranca_termos_antigos"] is True

    # Cenário seguro com Ollama
    with patch("backend.llm_engine.chamar_ollama_local", new_callable=AsyncMock) as mock_ollama:
        mock_ollama.return_value = {
            "estado_planta": "hidratada",
            "bomba_status": "BOMBA DESLIGADA",
            "diagnostico_texto": "Equilíbrio hídrico com biossensores Tekó Biotech.",
            "recomendacao_manejo": "Manter monitoramento de rotina."
        }
        res_llm_seguro = await processar_diagnostico_llm(DiagnosticoLLMIn(tensao_kpa=22.0))
        assert res_llm_seguro["seguranca_termos_antigos"] is True

    # Cenário dinâmico caso a verificação aponte resíduo proibido
    with patch("backend.llm_engine.chamar_ollama_local", new_callable=AsyncMock) as mock_ollama, \
         patch("backend.llm_engine.verificar_seguranca_termos", return_value=False):
        mock_ollama.return_value = {
            "estado_planta": "hidratada",
            "bomba_status": "BOMBA DESLIGADA",
            "diagnostico_texto": "Texto qualquer",
            "recomendacao_manejo": "Manejo qualquer"
        }
        res_llm_inseguro = await processar_diagnostico_llm(DiagnosticoLLMIn(tensao_kpa=22.0))
        assert res_llm_inseguro["seguranca_termos_antigos"] is False


@pytest.mark.anyio
async def test_paradoxo_enchente_trava_soberana_contra_alucinacao_ollama():
    """
    Valida a Trava Soberana Físico-Agronômica do Paradoxo da Enchente:
    Mesmo que o Ollama alucine 'sede' e 'LIGAR AMANHÃ ÀS 06H', sob ORP < -100 mV
    o sistema impõe incondicionalmente estado 'hipoxia' e bomba 'NÃO LIGAR A BOMBA!',
    anexando o alerta do Paradoxo da Enchente à recomendação.
    """
    with patch("backend.llm_engine.chamar_ollama_local", new_callable=AsyncMock) as mock_ollama:
        mock_ollama.return_value = {
            "estado_planta": "sede",
            "bomba_status": "LIGAR AMANHÃ ÀS 06H",
            "diagnostico_texto": "Folhas murchas por falta aparente de água. Irrigar urgentemente.",
            "recomendacao_manejo": "Ligar a motobomba às 06h para recuperação do turgor."
        }
        dados = DiagnosticoLLMIn(
            tensao_kpa=12.0,
            tipo_solo="franco",
            z_50k_ohms=6000.0,
            z_1k_ohms=4800.0,
            orp_mv=-140.0,
            cultura="Milho"
        )
        res = await processar_diagnostico_llm(dados)

        assert res["estado_planta"] == "hipoxia", "Estado não foi forçado para hipóxia sob ORP < -100 mV!"
        assert res["bomba_status"] == "NÃO LIGAR A BOMBA!", "Bomba foi autorizada sob hipóxia / anóxia radicular!"
        assert "Paradoxo da Enchente" in res["recomendacao_manejo"]
        assert "NÃO LIGAR A BOMBA!" in res["recomendacao_manejo"] or "DESLIGADA" in res["recomendacao_manejo"]
        assert res["seguranca_termos_antigos"] is True


# ============================================================================
# 5. TESTES DE INTEGRAÇÃO DO ENDPOINT FASTAPI (POST /api/llm/diagnostico)
# ============================================================================

def test_endpoint_api_diagnostico_sucesso_post():
    """Valida chamada completa via TestClient com fallback instantâneo."""
    with patch("backend.llm_engine.chamar_ollama_local", new_callable=AsyncMock) as mock_ollama:
        mock_ollama.return_value = None
        payload = {
            "tensao_kpa": 22.0,
            "tipo_solo": "franco",
            "z_50k_ohms": 1400.0,
            "z_1k_ohms": 1200.0,
            "orp_mv": 310.0,
            "cultura": "Milho",
            "pergunta": "Como está o solo hoje?"
        }
        resp = client.post("/api/llm/diagnostico", json=payload)
        assert resp.status_code == 200
        dados = resp.json()
        assert dados["status"] == "sucesso"
        assert dados["estado_planta"] == "hidratada"
        assert dados["bomba_status"] == "BOMBA DESLIGADA"
        assert dados["tempo_resposta_ms"] < 50.0
        assert dados["motor_utilizado"] == "motor_especialista_fallback"
        assert dados["seguranca_termos_antigos"] is True


def test_endpoint_api_diagnostico_payload_minimo():
    """Valida chamada enviando apenas tensao_kpa (demais campos com defaults seguros)."""
    with patch("backend.llm_engine.chamar_ollama_local", new_callable=AsyncMock) as mock_ollama:
        mock_ollama.return_value = None
        payload = {"tensao_kpa": 48.0}
        resp = client.post("/api/llm/diagnostico", json=payload)
        assert resp.status_code == 200
        dados = resp.json()
        assert dados["estado_planta"] == "sede"
        assert dados["bomba_status"] == "LIGAR AMANHÃ ÀS 06H"


def test_endpoint_api_validacao_campo_obrigatorio_ausente_422():
    """Payload sem o campo obrigatório 'tensao_kpa' deve retornar HTTP 422."""
    payload = {"tipo_solo": "franco"}
    resp = client.post("/api/llm/diagnostico", json=payload)
    assert resp.status_code == 422


def test_endpoint_api_validacao_tipo_invalido_422():
    """Payload com tipo string não conversível em float deve retornar HTTP 422."""
    payload = {"tensao_kpa": "muito_seco"}
    resp = client.post("/api/llm/diagnostico", json=payload)
    assert resp.status_code == 422


def test_endpoint_api_validacao_tensao_negativa_422():
    """Tensão matricial negativa (ge=0.0) viola validação física e deve retornar HTTP 422."""
    payload = {"tensao_kpa": -10.0}
    resp = client.post("/api/llm/diagnostico", json=payload)
    assert resp.status_code == 422


def test_endpoint_api_tolerancia_falha_camada_3():
    """
    Camada 3 de proteção: mesmo se processar_diagnostico_llm lançar RuntimeError inesperado,
    o router FastAPI captura e aciona o fallback de emergência retornando HTTP 200.
    """
    with patch("backend.server.processar_diagnostico_llm", side_effect=RuntimeError("Bug imprevisto")):
        payload = {"tensao_kpa": 50.0}
        resp = client.post("/api/llm/diagnostico", json=payload)
        assert resp.status_code == 200
        dados = resp.json()
        assert dados["status"] == "sucesso"
        assert dados["motor_utilizado"] == "motor_especialista_fallback"


def test_raiz_contem_endpoint_llm():
    """Valida inclusão de /api/llm/diagnostico (POST) na rota raiz GET /."""
    resp = client.get("/")
    assert resp.status_code == 200
    endpoints = resp.json().get("endpoints", [])
    assert "/api/llm/diagnostico (POST)" in endpoints
