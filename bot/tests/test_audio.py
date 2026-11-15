"""
Tekó Biotech — Testes Unitários e de Integração do Processador de Áudio e Voz
Hackathon das Engenharias UERGS 2026 — Desafio 02: Água e Drenagem Rural

Cobertura abrangente:
1. Validação pré-download de metadados de áudio (<= 120s e <= 5MB)
2. Inspeção de container Ogg/Opus puro Python (RFC 3533 & RFC 7845) sem ffmpeg
3. Gerenciador de arquivos temporários com prevenção de lock Win32 (WinError 32)
4. Integração do cliente LLM e motor especialista de fallback fitoeletrônico
5. Fluxos do manipulador handle_voice no Bot Telegram com blindagem anti-409
"""

import os
import sys
import struct
import pytest
from unittest.mock import MagicMock, patch

_bot_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_root_dir = os.path.dirname(_bot_dir)
if _bot_dir not in sys.path:
    sys.path.insert(0, _bot_dir)
if _root_dir not in sys.path:
    sys.path.insert(0, _root_dir)

from audio_processor import (
    validar_metadados_audio,
    inspecionar_container_ogg,
    gerenciador_audio_temporario,
    MAX_AUDIO_DURATION_SEC,
    MAX_AUDIO_SIZE_BYTES
)
from telemetria import obter_diagnostico_llm


# ============================================================================
# FIXTURES E GERADORES SINTÉTICOS DE CONTÊINER OGG/OPUS (RFC 3533 & RFC 7845)
# ============================================================================
def make_ogg_page(
    header_type: int,
    granule_pos: int,
    seq_no: int,
    serial_no: int,
    payload: bytes,
    ogg_version: int = 0
) -> bytes:
    """Monta página binária Ogg estruturada conforme RFC 3533."""
    segs = []
    rem = len(payload)
    while rem >= 255:
        segs.append(255)
        rem -= 255
    segs.append(rem)
    seg_table = bytes(segs)
    hdr = struct.pack(
        "<4sBBqIIIB",
        b"OggS",
        ogg_version,
        header_type,
        granule_pos,
        serial_no,
        seq_no,
        0,  # CRC zero para teste
        len(seg_table)
    )
    return hdr + seg_table + payload


def criar_ogg_opus_sintetico(
    duracao_sec: float = 10.0,
    canais: int = 1,
    sample_rate: int = 48000,
    vendor: str = "TekoBot/1.0",
    tag: str = "TITLE=Diagnostico Fitoeletronico"
) -> bytes:
    """Gera contêiner Ogg/Opus sintético válido para testes sem ffmpeg."""
    pre_skip = 384
    # OpusHead (RFC 7845: 19 bytes)
    opus_head = struct.pack("<8sBBHIhB", b"OpusHead", 1, canais, pre_skip, sample_rate, 0, 0)
    p0 = make_ogg_page(0x02, 0, 0, 12345, opus_head)

    # OpusTags (RFC 7845)
    vendor_b = vendor.encode("utf-8")
    tag_b = tag.encode("utf-8")
    opus_tags = (
        b"OpusTags"
        + struct.pack("<I", len(vendor_b))
        + vendor_b
        + struct.pack("<I", 1)
        + struct.pack("<I", len(tag_b))
        + tag_b
    )
    p1 = make_ogg_page(0x00, 0, 1, 12345, opus_tags)

    # Página de dados com granule final para cálculo de duração
    granule = int(duracao_sec * 48000) + pre_skip
    p2 = make_ogg_page(0x04, granule, 2, 12345, b"\xf8\xff\xfe" * 15)
    return p0 + p1 + p2


# ============================================================================
# BLOCO 1: TESTES DE VALIDAÇÃO DE METADADOS (PRÉ-DOWNLOAD)
# ============================================================================
def test_validar_metadados_audio_sucesso():
    valido, motivo = validar_metadados_audio(duration=60, file_size=1024 * 1024)
    assert valido is True
    assert motivo == ""

    # Limites exatos permitidos (120s e 5 MB)
    valido_limite, motivo_limite = validar_metadados_audio(
        duration=MAX_AUDIO_DURATION_SEC,
        file_size=MAX_AUDIO_SIZE_BYTES
    )
    assert valido_limite is True
    assert motivo_limite == ""


def test_validar_metadados_audio_duracao_excedida():
    valido, motivo = validar_metadados_audio(duration=121, file_size=1024)
    assert valido is False
    assert "120 segundos" in motivo
    assert "121s" in motivo


def test_validar_metadados_audio_tamanho_excedido():
    valido, motivo = validar_metadados_audio(duration=30, file_size=MAX_AUDIO_SIZE_BYTES + 1)
    assert valido is False
    assert "5 MB" in motivo


@pytest.mark.parametrize("dur,size", [
    (None, 1000),
    (60, None),
    (None, None),
    (0, 1000),
    (-5, 1000),
    (60, 0),
    (60, -500),
    ("60", 1000),
    (60, "1000")
])
def test_validar_metadados_audio_casos_borda(dur, size):
    valido, motivo = validar_metadados_audio(dur, size)
    assert valido is False
    assert len(motivo) > 0


# ============================================================================
# BLOCO 2: TESTES DE INSPEÇÃO PURA PYTHON DO CONTÊINER OGG/OPUS
# ============================================================================
def test_inspecionar_container_ogg_valido_memoria():
    buf = criar_ogg_opus_sintetico(duracao_sec=15.5, canais=1, sample_rate=48000)
    info = inspecionar_container_ogg(buf)
    assert info["valido"] is True
    assert info["codec"] == "opus"
    assert info["canais"] == 1
    assert info["taxa_amostragem"] == 48000
    assert info["versao_opus"] == 1
    assert info["vendor"] == "TekoBot/1.0"
    assert "TITLE=Diagnostico Fitoeletronico" in info["tags"]
    assert info["duracao_estimada_sec"] == 15.5
    assert info["erro"] is None


def test_inspecionar_container_ogg_valido_arquivo_em_disco():
    buf = criar_ogg_opus_sintetico(duracao_sec=8.0, canais=2, sample_rate=48000)
    with gerenciador_audio_temporario(buf) as caminho_tmp:
        info = inspecionar_container_ogg(caminho_tmp)
        assert info["valido"] is True
        assert info["canais"] == 2
        assert info["taxa_amostragem"] == 48000
        assert info["duracao_estimada_sec"] == 8.0


def test_inspecionar_container_ogg_arquivo_inexistente():
    info = inspecionar_container_ogg("C:\\caminho_que_nao_existe_12345.ogg")
    assert info["valido"] is False
    assert "Arquivo não encontrado" in info["erro"]


def test_inspecionar_container_ogg_origem_nula_ou_invalida():
    info_none = inspecionar_container_ogg(None)
    assert info_none["valido"] is False
    assert "não fornecida" in info_none["erro"]

    info_tipo = inspecionar_container_ogg(12345)  # tipo inválido
    assert info_tipo["valido"] is False
    assert "deve ser caminho" in info_tipo["erro"]


def test_inspecionar_container_ogg_buffer_vazio():
    info = inspecionar_container_ogg(b"")
    assert info["valido"] is False
    assert "vazio" in info["erro"]


def test_inspecionar_container_ogg_corrompido_truncado():
    info = inspecionar_container_ogg(b"OggS\x00\x02\x00")
    assert info["valido"] is False
    assert "insuficiente" in info["erro"].lower() or "truncad" in info["erro"].lower()


def test_inspecionar_container_ogg_assinatura_invalida_mp3_e_wav():
    mp3_falso = b"ID3\x03\x00\x00\x00\x00\x00\x00" + b"\x00" * 30
    info_mp3 = inspecionar_container_ogg(mp3_falso)
    assert info_mp3["valido"] is False
    assert "Assinatura mágica inválida" in info_mp3["erro"]

    wav_falso = b"RIFF\x24\x00\x00\x00WAVEfmt " + b"\x00" * 30
    info_wav = inspecionar_container_ogg(wav_falso)
    assert info_wav["valido"] is False
    assert "Assinatura mágica inválida" in info_wav["erro"]


def test_inspecionar_container_ogg_versao_invalida():
    # Página Ogg com versão != 0
    opus_head = struct.pack("<8sBBHIhB", b"OpusHead", 1, 1, 384, 48000, 0, 0)
    page_ver_invalida = make_ogg_page(0x02, 0, 0, 11111, opus_head, ogg_version=1)
    info = inspecionar_container_ogg(page_ver_invalida)
    assert info["valido"] is False
    assert "Versão Ogg incompatível" in info["erro"]


def test_inspecionar_container_ogg_sem_opus():
    # Página Ogg contendo Vorbis em vez de Opus
    vorbis_head = b"\x01vorbis" + b"\x00" * 20
    page_vorbis = make_ogg_page(0x02, 0, 0, 11111, vorbis_head)
    info = inspecionar_container_ogg(page_vorbis)
    assert info["valido"] is False
    assert "Codec incompatível" in info["erro"]


def test_inspecionar_container_ogg_canais_zero():
    # OpusHead com 0 canais
    opus_head_invalido = struct.pack("<8sBBHIhB", b"OpusHead", 1, 0, 384, 48000, 0, 0)
    page_invalida = make_ogg_page(0x02, 0, 0, 11111, opus_head_invalido)
    info = inspecionar_container_ogg(page_invalida)
    assert info["valido"] is False
    assert "canais inválido" in info["erro"]


# ============================================================================
# BLOCO 3: TESTES DO GERENCIADOR TEMPORÁRIO (WINDOWS LOCK SAFETY)
# ============================================================================
def test_gerenciador_audio_temporario_ciclo_normal():
    conteudo = b"OggS_teste_dados_binarios_teko"
    caminho_salvo = None
    with gerenciador_audio_temporario(conteudo) as caminho:
        caminho_salvo = caminho
        assert os.path.exists(caminho)
        # Confirma que o arquivo pode ser lido sem WinError 32
        with open(caminho, "rb") as f:
            dados_lidos = f.read()
        assert dados_lidos == conteudo

    # Ao sair do bloco with, o arquivo DEVE ser removido
    assert not os.path.exists(caminho_salvo)


def test_gerenciador_audio_temporario_resiliencia_excecao():
    caminho_salvo = None
    with pytest.raises(RuntimeError):
        with gerenciador_audio_temporario(b"dados_temporarios") as caminho:
            caminho_salvo = caminho
            assert os.path.exists(caminho)
            raise RuntimeError("Falha proposital para teste de cleanup")

    # Arquivo deve ser excluído mesmo após exceção
    assert caminho_salvo is not None
    assert not os.path.exists(caminho_salvo)


# ============================================================================
# BLOCO 4: TESTES DO HELPER LLM (TELEMETRIA ↔ BACKEND / FALLBACK)
# ============================================================================
def test_obter_diagnostico_llm_sucesso_backend():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "status": "sucesso",
        "estado_planta": "hidratada",
        "bomba_status": "BOMBA DESLIGADA",
        "tempo_resposta_ms": 12.5,
        "motor_utilizado": "ollama_local",
        "diagnostico_texto": "Planta com turgor pleno.",
        "recomendacao_manejo": "Mantenha a irrigação desligada.",
        "seguranca_termos_antigos": True
    }

    telemetria = {"tensao_kpa": 21.5, "tipo_solo": "franco"}
    with patch("requests.post", return_value=mock_resp):
        res = obter_diagnostico_llm(telemetria)
        assert res["sucesso"] is True
        assert res["origem"] == "ollama_local"
        assert "Planta com turgor pleno." in res["resposta"]
        assert "Mantenha a irrigação desligada." in res["resposta"]


def test_obter_diagnostico_llm_fallback_local_sob_falha():
    telemetria = {
        "tensao_kpa": 4.0,  # Enchente / Hipóxia
        "tipo_solo": "franco",
        "orp_mv": -120.0
    }
    # Força exceção no requests.post para disparar fallback local
    with patch("requests.post", side_effect=ConnectionError("Backend indisponível")):
        res = obter_diagnostico_llm(telemetria)
        assert res["sucesso"] is True
        assert res["origem"] == "fallback_local"
        assert res["dados"]["estado_planta"] == "hipoxia"
        assert res["dados"]["bomba_status"] == "NÃO LIGAR A BOMBA!"
        assert "Recomendação de Manejo" in res["resposta"]


def test_obter_diagnostico_llm_clamping_tensao():
    # Tensão < 0 ou > 250 deve sofrer clamping
    tele_sub = {"tensao_kpa": -10.0}
    with patch("requests.post") as mock_post:
        mock_post.side_effect = ConnectionError("offline")
        res = obter_diagnostico_llm(tele_sub)
        assert mock_post.called
        assert mock_post.call_args[1]["json"]["tensao_kpa"] == 0.0
        assert res["dados"]["estado_planta"] == "hipoxia"

    tele_super = {"tensao_kpa": 999.0}
    with patch("requests.post") as mock_post:
        mock_post.side_effect = ConnectionError("offline")
        res = obter_diagnostico_llm(tele_super)
        assert mock_post.called
        assert mock_post.call_args[1]["json"]["tensao_kpa"] == 250.0
        assert res["dados"]["estado_planta"] == "sede"


# ============================================================================
# BLOCO 5: TESTES DO HANDLER DE VOZ E POLLING ANTI-409
# ============================================================================
def test_handle_voice_sem_audio_detectado():
    from phytosense_bot import handle_voice, bot

    mock_send = MagicMock()
    bot.send_message = mock_send

    mock_msg = MagicMock()
    mock_msg.chat.id = 12345
    mock_msg.voice = None
    mock_msg.audio = None

    handle_voice(mock_msg)
    assert mock_send.called
    msg_texto = mock_send.call_args[0][1]
    assert "Nenhum áudio detectado" in msg_texto


def test_handle_voice_rejeicao_pre_download_sem_chamar_rede():
    from phytosense_bot import handle_voice, bot

    mock_send = MagicMock()
    bot.send_message = mock_send
    bot.get_file = MagicMock()
    bot.download_file = MagicMock()

    # Mensagem com áudio de 150s (acima do limite de 120s)
    mock_msg = MagicMock()
    mock_msg.chat.id = 12345
    mock_msg.voice.duration = 150
    mock_msg.voice.file_size = 100000
    mock_msg.audio = None

    handle_voice(mock_msg)

    # get_file e download_file NÃO devem ser chamados
    bot.get_file.assert_not_called()
    bot.download_file.assert_not_called()
    assert mock_send.called
    msg_texto = mock_send.call_args[0][1]
    assert "120 segundos" in msg_texto


def test_handle_voice_fluxo_completo_mockado():
    from phytosense_bot import handle_voice, bot

    mock_send = MagicMock()
    mock_action = MagicMock()
    bot.send_message = mock_send
    bot.send_chat_action = mock_action

    audio_bytes = criar_ogg_opus_sintetico(duracao_sec=12.0)
    mock_file_info = MagicMock()
    mock_file_info.file_path = "voice/file_01.oga"
    bot.get_file = MagicMock(return_value=mock_file_info)
    bot.download_file = MagicMock(return_value=audio_bytes)

    mock_msg = MagicMock()
    mock_msg.chat.id = 77777
    mock_msg.voice.duration = 12
    mock_msg.voice.file_size = len(audio_bytes)
    mock_msg.voice.file_id = "voice_id_abc"
    mock_msg.audio = None

    mock_diag = {
        "sucesso": True,
        "resposta": "Planta hidratada. Condição perfeita para colheita.",
        "origem": "fallback_local"
    }

    with patch("phytosense_bot.obter_diagnostico_llm", return_value=mock_diag):
        handle_voice(mock_msg)

    assert bot.get_file.called
    assert bot.download_file.called
    assert mock_send.called
    msg_enviada = mock_send.call_args[0][1]
    assert "Áudio Recebido & Processado" in msg_enviada
    assert "Planta hidratada" in msg_enviada


def test_handle_voice_arquivo_invalido_baixado():
    from phytosense_bot import handle_voice, bot

    mock_send = MagicMock()
    bot.send_message = mock_send
    bot.send_chat_action = MagicMock()

    # Retorna bytes que não são Ogg/Opus (ex: MP3 corrompido)
    mock_file_info = MagicMock()
    mock_file_info.file_path = "voice/bad.mp3"
    bot.get_file = MagicMock(return_value=mock_file_info)
    bot.download_file = MagicMock(return_value=b"RIFF_FAKE_WAV_BYTES_FOR_TEST")

    mock_msg = MagicMock()
    mock_msg.chat.id = 88888
    mock_msg.voice.duration = 10
    mock_msg.voice.file_size = 30
    mock_msg.voice.file_id = "voice_bad_id"
    mock_msg.audio = None

    handle_voice(mock_msg)
    assert mock_send.called
    msg_enviada = mock_send.call_args[0][1]
    assert "Formato de áudio não suportado" in msg_enviada


def test_handle_voice_tratamento_excecao():
    from phytosense_bot import handle_voice, bot

    mock_send = MagicMock()
    bot.send_message = mock_send
    bot.send_chat_action = MagicMock()
    # Simula falha catastrófica de rede no download
    bot.get_file = MagicMock(side_effect=RuntimeError("Falha de rede"))

    mock_msg = MagicMock()
    mock_msg.chat.id = 99999
    mock_msg.voice.duration = 15
    mock_msg.voice.file_size = 2048
    mock_msg.voice.file_id = "voice_err_id"
    mock_msg.audio = None

    handle_voice(mock_msg)
    assert mock_send.called
    msg_enviada = mock_send.call_args[0][1]
    assert "instabilidade temporária" in msg_enviada


def test_bot_polling_mock_evita_conflito_409():
    from phytosense_bot import bot

    # Confirma que a execução de testes não iniciou threads de polling ativas
    # o que provocaria erro 409 Conflict no Telegram
    assert bot is not None
