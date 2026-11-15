"""
Tekó Biotech — Módulo de Processamento e Inspeção de Áudio Ogg/Opus
Hackathon das Engenharias UERGS 2026 — Desafio 02: Água e Drenagem Rural

Implementação 100% em Python puro (RFC 3533 & RFC 7845) sem dependência
de binários externos (ffmpeg/ffprobe) no PATH do Windows.
"""

from __future__ import annotations

import contextlib
import os
import struct
import tempfile
from typing import Any, Dict, List, Optional, Tuple

# Limites operacionais de voz do Tekó Biotech
MAX_AUDIO_DURATION_SEC: int = 120  # 2 minutos
MAX_AUDIO_SIZE_BYTES: int = 5 * 1024 * 1024  # 5.242.880 bytes (5 MB)


def validar_metadados_audio(
    duration: int | float | None,
    file_size: int | float | None
) -> Tuple[bool, str]:
    """
    Valida metadados de áudio antes de realizar download da mensagem de voz.
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


def _carregar_bytes_origem(
    origem: str | bytes | bytearray | memoryview | os.PathLike | None
) -> Tuple[Optional[bytes], Optional[str]]:
    """Carrega os bytes a partir de caminho em disco ou buffer em memória."""
    if origem is None:
        return None, "Origem não fornecida (None)."

    if isinstance(origem, (str, os.PathLike)):
        if not os.path.exists(origem):
            return None, f"Arquivo não encontrado: {origem}"
        try:
            with open(origem, "rb") as f:
                data = f.read()
        except OSError as exc:
            return None, f"Erro de I/O ao ler arquivo de áudio: {exc}"
    elif isinstance(origem, (bytes, bytearray, memoryview)):
        data = bytes(origem)
    else:
        return None, "Origem deve ser caminho de arquivo (str/Path) ou sequência de bytes."

    if len(data) == 0:
        return None, "Arquivo ou buffer vazio (0 bytes)."
    if len(data) < 27:
        return None, f"Tamanho insuficiente para cabeçalho Ogg ({len(data)} bytes, mínimo 27)."

    return data, None


def _desempacotar_pagina_ogg(
    data: bytes,
    offset: int,
    eh_primeira: bool
) -> Tuple[Optional[Dict[str, Any]], int, Optional[str]]:
    """Desempacota uma única página Ogg a partir do offset informado (RFC 3533)."""
    total_len = len(data)
    capture, ver, h_type, granule, serial, seq, _, segs = struct.unpack(
        "<4sBBqIIIB", data[offset : offset + 27]
    )
    if capture != b"OggS":
        erro = (
            f"Assinatura mágica inválida (esperado b'OggS', recebido {capture!r}). Não é um container Ogg."
            if eh_primeira
            else None
        )
        return None, offset, erro

    if ver != 0 and eh_primeira:
        return None, offset, f"Versão Ogg incompatível: {ver} (RFC 3533 define versão 0)."

    if offset + 27 + segs > total_len:
        erro = "Tabela de segmentos da página Ogg truncada." if eh_primeira else None
        return None, offset, erro

    seg_table = data[offset + 27 : offset + 27 + segs]
    payload_len = sum(seg_table)
    poff = offset + 27 + segs

    if poff + payload_len > total_len:
        erro = "Payload da página Ogg truncado." if eh_primeira else None
        return None, offset, erro

    pagina = {
        "header_type": h_type,
        "granule_pos": granule,
        "serial_no": serial,
        "seq_no": seq,
        "payload": data[poff : poff + payload_len]
    }
    return pagina, poff + payload_len, None


def _extrair_paginas_ogg(data: bytes) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """Itera sobre o buffer extraindo todas as páginas Ogg válidas."""
    offset = 0
    pages: List[Dict[str, Any]] = []
    total_len = len(data)

    while offset + 27 <= total_len:
        pagina, novo_offset, erro = _desempacotar_pagina_ogg(data, offset, len(pages) == 0)
        if erro:
            return [], erro
        if pagina is None:
            break
        pages.append(pagina)
        offset = novo_offset

    if not pages:
        return [], "Nenhuma página Ogg completa encontrada."
    return pages, None


def _decodificar_bloco_opustags(p1_payload: bytes) -> Tuple[Optional[str], List[str]]:
    """Extrai vendor e lista de tags de um payload OpusTags."""
    if len(p1_payload) < 12:
        return None, []
    v_len = struct.unpack("<I", p1_payload[8:12])[0]
    if len(p1_payload) < 12 + v_len:
        return None, []

    vendor = p1_payload[12 : 12 + v_len].decode("utf-8", errors="replace")
    cur = 12 + v_len
    if len(p1_payload) < cur + 4:
        return vendor, []

    n_comments = struct.unpack("<I", p1_payload[cur : cur + 4])[0]
    cur += 4
    tags: List[str] = []
    for _ in range(n_comments):
        if len(p1_payload) < cur + 4:
            break
        c_len = struct.unpack("<I", p1_payload[cur : cur + 4])[0]
        cur += 4
        if len(p1_payload) < cur + c_len:
            break
        tags.append(p1_payload[cur : cur + c_len].decode("utf-8", errors="replace"))
        cur += c_len

    return vendor, tags


def _buscar_opustags(pages: List[Dict[str, Any]]) -> Tuple[bool, Optional[str], List[str]]:
    """Procura página OpusTags nas páginas subsequentes à página 0."""
    for p in pages[1:]:
        if p["payload"].startswith(b"OpusTags"):
            vendor, tags = _decodificar_bloco_opustags(p["payload"])
            return True, vendor, tags
    return False, None, []


def inspecionar_container_ogg(
    origem: str | bytes | bytearray | memoryview | os.PathLike | None
) -> Dict[str, Any]:
    """
    Inspeciona contêiner Ogg e valida cabeçalhos OpusHead e OpusTags (RFC 3533 / RFC 7845).
    Funciona 100% em memória ou a partir de arquivo em disco sem invocar ffmpeg.
    """
    data, erro_leitura = _carregar_bytes_origem(origem)
    if erro_leitura or data is None:
        return {"valido": False, "erro": erro_leitura}

    pages, erro_paginas = _extrair_paginas_ogg(data)
    if erro_paginas:
        return {"valido": False, "erro": erro_paginas}

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

    _, opus_ver, channels, pre_skip, sample_rate, gain_q8, mapping = struct.unpack(
        "<8sBBHIhB", p0_payload[:19]
    )

    if channels == 0:
        return {"valido": False, "erro": "Número de canais inválido em OpusHead (0 canais)."}

    tem_opustags, vendor, tags = _buscar_opustags(pages)
    max_granule = max(p["granule_pos"] for p in pages)
    duracao_estimada_sec = round((max_granule - pre_skip) / 48000.0, 3) if max_granule > pre_skip else 0.0

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
    conteudo_bytes: bytes | None = None,
    prefixo: str = "teko_audio_",
    sufixo: str = ".ogg"
):
    """
    Gerenciador de contexto que cria e garante a exclusão determinística
    de arquivos de áudio temporários via bloco try/finally.
    """
    tmp = tempfile.NamedTemporaryFile(delete=False, prefix=prefixo, suffix=sufixo)
    caminho = os.path.abspath(tmp.name)
    try:
        if conteudo_bytes:
            tmp.write(conteudo_bytes)
        tmp.flush()
        tmp.close()
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
