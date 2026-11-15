"""
Tekó Biotech — Módulo de Processamento e Inspeção de Áudio Ogg/Opus
Hackathon das Engenharias UERGS 2026 — Desafio 02: Água e Drenagem Rural

Implementação 100% em Python puro (RFC 3533 & RFC 7845) sem dependência
de binários externos (ffmpeg/ffprobe) no PATH do Windows.
"""

import os
import struct
import tempfile
import contextlib
from typing import Tuple, Dict, Any, Union, Optional

# Limites operacionais de voz do Tekó Biotech
MAX_AUDIO_DURATION_SEC: int = 120  # 2 minutos
MAX_AUDIO_SIZE_BYTES: int = 5 * 1024 * 1024  # 5.242.880 bytes (5 MB)


def validar_metadados_audio(
    duration: Optional[Union[int, float]],
    file_size: Optional[Union[int, float]]
) -> Tuple[bool, str]:
    """
    Valida metadados de áudio antes de realizar download da mensagem de voz.

    Regras:
    - duration não pode ser None, <= 0 ou > 120 segundos.
    - file_size não pode ser None, <= 0 ou > 5242880 bytes (5 MB).

    Retorna:
        Tuple[bool, str]: (True, "") se válido, ou (False, motivo) com mensagem amigável.
    """
    if duration is None:
        return False, "Duração do áudio não informada."
    if not isinstance(duration, (int, float)):
        return False, "Duração do áudio deve ser um valor numérico."
    if duration <= 0:
        return False, "Duração do áudio deve ser maior que zero."
    if duration > MAX_AUDIO_DURATION_SEC:
        return (
            False,
            f"Áudio excede o limite máximo de 120 segundos ({int(duration)}s recebidos). "
            "Por favor, envie uma mensagem mais curta de até 2 minutos."
        )

    if file_size is None:
        return False, "Tamanho do arquivo não informado."
    if not isinstance(file_size, (int, float)):
        return False, "Tamanho do arquivo deve ser um valor numérico."
    if file_size <= 0:
        return False, "Tamanho do arquivo de áudio deve ser maior que zero."
    if file_size > MAX_AUDIO_SIZE_BYTES:
        tamanho_mb = round(file_size / (1024 * 1024), 2)
        return (
            False,
            f"Arquivo excede o limite máximo de 5 MB ({tamanho_mb} MB recebidos). "
            "Por favor, envie um áudio mais leve."
        )

    return True, ""


def inspecionar_container_ogg(origem: Union[str, bytes, bytearray, memoryview, os.PathLike]) -> Dict[str, Any]:
    """
    Inspeciona contêiner Ogg e valida cabeçalhos OpusHead e OpusTags (RFC 3533 / RFC 7845).
    Funciona 100% em memória ou a partir de arquivo em disco sem invocar ffmpeg.

    Retorna dicionário estruturado com informações acústicas, duração estimada e validação.
    """
    if origem is None:
        return {"valido": False, "erro": "Origem não fornecida (None)."}

    data: bytes
    if isinstance(origem, (str, os.PathLike)):
        if not os.path.exists(origem):
            return {"valido": False, "erro": f"Arquivo não encontrado: {origem}"}
        try:
            with open(origem, "rb") as f:
                data = f.read()
        except OSError as exc:
            return {"valido": False, "erro": f"Erro de I/O ao ler arquivo de áudio: {exc}"}
    elif isinstance(origem, (bytes, bytearray, memoryview)):
        data = bytes(origem)
    else:
        return {
            "valido": False,
            "erro": "Origem deve ser caminho de arquivo (str/Path) ou sequência de bytes."
        }

    if len(data) == 0:
        return {"valido": False, "erro": "Arquivo ou buffer vazio (0 bytes)."}

    # RFC 3533: Cabeçalho fixo da página Ogg tem 27 bytes
    if len(data) < 27:
        return {
            "valido": False,
            "erro": f"Tamanho insuficiente para cabeçalho Ogg ({len(data)} bytes, mínimo 27)."
        }

    # Desempacotamento de todas as páginas Ogg presentes no buffer
    offset = 0
    pages = []
    total_len = len(data)

    while offset + 27 <= total_len:
        capture, ver, h_type, granule, serial, seq, crc, segs = struct.unpack(
            "<4sBBqIIIB", data[offset : offset + 27]
        )
        if capture != b"OggS":
            if not pages:
                return {
                    "valido": False,
                    "erro": f"Assinatura mágica inválida (esperado b'OggS', recebido {capture!r}). Não é um container Ogg."
                }
            break

        if ver != 0 and not pages:
            return {
                "valido": False,
                "erro": f"Versão Ogg incompatível: {ver} (RFC 3533 define versão 0)."
            }

        if offset + 27 + segs > total_len:
            if not pages:
                return {"valido": False, "erro": "Tabela de segmentos da página Ogg truncada."}
            break

        seg_table = data[offset + 27 : offset + 27 + segs]
        payload_len = sum(seg_table)
        poff = offset + 27 + segs

        if poff + payload_len > total_len:
            if not pages:
                return {"valido": False, "erro": "Payload da página Ogg truncado."}
            break

        payload = data[poff : poff + payload_len]
        pages.append({
            "header_type": h_type,
            "granule_pos": granule,
            "serial_no": serial,
            "seq_no": seq,
            "payload": payload
        })
        offset = poff + payload_len

    if not pages:
        return {"valido": False, "erro": "Nenhuma página Ogg completa encontrada."}

    # Análise da Página 0 (Identificação do Codec Opus - RFC 7845)
    p0 = pages[0]
    p0_payload = p0["payload"]

    if not p0_payload.startswith(b"OpusHead"):
        magic_found = p0_payload[:8] if len(p0_payload) >= 8 else p0_payload
        return {
            "valido": False,
            "erro": f"Codec incompatível (esperado b'OpusHead', recebido {magic_found!r}). O container Ogg não contém Opus."
        }

    if len(p0_payload) < 19:
        return {
            "valido": False,
            "erro": f"Cabeçalho OpusHead incompleto ({len(p0_payload)} bytes, mínimo 19)."
        }

    magic, opus_ver, channels, pre_skip, sample_rate, gain_q8, mapping = struct.unpack(
        "<8sBBHIhB", p0_payload[:19]
    )

    if channels == 0:
        return {"valido": False, "erro": "Número de canais inválido em OpusHead (0 canais)."}

    # Análise de OpusTags (comentários Vorbis no Opus)
    tem_opustags = False
    vendor = None
    tags = []

    for p in pages[1:]:
        if p["payload"].startswith(b"OpusTags"):
            tem_opustags = True
            p1_payload = p["payload"]
            if len(p1_payload) >= 12:
                v_len = struct.unpack("<I", p1_payload[8:12])[0]
                if len(p1_payload) >= 12 + v_len:
                    vendor = p1_payload[12 : 12 + v_len].decode("utf-8", errors="replace")
                    cur = 12 + v_len
                    if len(p1_payload) >= cur + 4:
                        n_comments = struct.unpack("<I", p1_payload[cur : cur + 4])[0]
                        cur += 4
                        for _ in range(n_comments):
                            if len(p1_payload) >= cur + 4:
                                c_len = struct.unpack("<I", p1_payload[cur : cur + 4])[0]
                                cur += 4
                                if len(p1_payload) >= cur + c_len:
                                    tags.append(p1_payload[cur : cur + c_len].decode("utf-8", errors="replace"))
                                    cur += c_len
            break

    # Cálculo da duração estimada via posição do grânulo (RFC 7845 Seção 4: relógio de referência a 48000 Hz)
    max_granule = max(p["granule_pos"] for p in pages)
    duracao_estimada_sec = 0.0
    if max_granule > pre_skip:
        duracao_estimada_sec = round((max_granule - pre_skip) / 48000.0, 3)

    return {
        "valido": True,
        "formato": "ogg/opus",
        "codec": "opus",
        "canais": channels,
        "taxa_amostragem": sample_rate,
        "versao_opus": opus_ver,
        "pre_skip": pre_skip,
        "ganho_saida_db": round(gain_q8 / 256.0, 2),
        "familia_mapeamento": mapping,
        "serial_stream": p0["serial_no"],
        "num_paginas_analisadas": len(pages),
        "tem_opustags": tem_opustags,
        "vendor": vendor,
        "tags": tags,
        "duracao_estimada_sec": duracao_estimada_sec,
        "erro": None
    }


@contextlib.contextmanager
def gerenciador_audio_temporario(
    conteudo_bytes: Optional[bytes] = None,
    prefixo: str = "teko_audio_",
    sufixo: str = ".ogg"
):
    """
    Gerenciador de contexto que cria e garante a exclusão determinística
    de arquivos de áudio temporários via bloco try/finally.

    Prevenção do WinError 32: Fecha explicitamente o descritor do arquivo
    antes do yield para permitir leitura/escrita simultânea e exclusão limpa no Windows.
    """
    tmp = tempfile.NamedTemporaryFile(delete=False, prefix=prefixo, suffix=sufixo)
    caminho = os.path.abspath(tmp.name)
    try:
        if conteudo_bytes:
            tmp.write(conteudo_bytes)
        tmp.flush()
        tmp.close()  # Libera o handle no Windows antes do yield
        yield caminho
    finally:
        if not tmp.closed:
            try:
                tmp.close()
            except OSError:
                pass
        if os.path.exists(caminho):
            try:
                os.remove(caminho)
            except OSError:
                pass
