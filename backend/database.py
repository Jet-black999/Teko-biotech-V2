"""
Tekó Biotech — Camada de Persistência SQLite
Hackathon das Engenharias UERGS 2026 — Desafio 02: Água e Estresse Hídrico
"""

import json
import os
import sqlite3
import time
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "phytosense.db")
SEED_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "seed_demo_data.json")

_banco_inicializado = False


def inicializar_banco() -> None:
    """Cria as tabelas do SQLite se não existirem e popula com a carga de seed inicial."""
    global _banco_inicializado
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Tabela 1: Perfis Oficiais Embrapa
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS perfis_cultura (
                id_perfil TEXT PRIMARY KEY,
                cultura TEXT NOT NULL,
                solo TEXT NOT NULL,
                profundidade_raiz_cm INTEGER NOT NULL,
                tensao_capacidade_campo_kpa REAL NOT NULL,
                tensao_alerta_kpa REAL NOT NULL,
                tensao_critica_manejo_kpa REAL NOT NULL,
                tensao_ponto_murcha_kpa REAL NOT NULL,
                fonte_cientifica TEXT NOT NULL
            );
        """)

        # Tabela 2: Leituras Históricas (7 dias simulados + leituras do nó ao vivo)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS leituras_historicas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                no_id TEXT NOT NULL,
                id_perfil TEXT NOT NULL,
                dia_label TEXT NOT NULL,
                timestamp_iso TEXT NOT NULL,
                tensao_kpa REAL NOT NULL,
                temp_c REAL,
                bateria_mv INTEGER,
                is_simulado INTEGER DEFAULT 1,
                FOREIGN KEY (id_perfil) REFERENCES perfis_cultura (id_perfil)
            );
        """)

        # Tabela 3: Alertas Emitidos (Disparos no Telegram)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS alertas_disparados (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp_iso TEXT NOT NULL,
                no_id TEXT NOT NULL,
                id_perfil TEXT NOT NULL,
                tensao_kpa REAL NOT NULL,
                taxa_secagem_kpa_dia REAL NOT NULL,
                dias_restantes REAL NOT NULL,
                status TEXT NOT NULL,
                mensagem TEXT NOT NULL,
                enviado_telegram INTEGER DEFAULT 0
            );
        """)

        # Tabela 4: Parâmetros Hidráulicos de Van Genuchten (11 Solos)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS solos_van_genuchten (
                classe TEXT PRIMARY KEY,
                theta_r REAL NOT NULL,
                theta_s REAL NOT NULL,
                alpha REAL NOT NULL,
                n REAL NOT NULL,
                m REAL NOT NULL,
                cc_kpa REAL NOT NULL,
                pmp_kpa REAL NOT NULL
            );
        """)

        # Tabela 5: Matriz Fenológica das Culturas (Embrapa / FAO-56)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fases_cultura (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cultura_id TEXT NOT NULL,
                fase TEXT NOT NULL,
                raiz_mm INTEGER NOT NULL,
                kc REAL NOT NULL,
                limiar_arenoso_kpa REAL NOT NULL,
                limiar_franco_arenoso_kpa REAL NOT NULL,
                limiar_franco_kpa REAL NOT NULL,
                limiar_franco_argiloso_kpa REAL NOT NULL,
                limiar_argiloso_kpa REAL NOT NULL,
                fonte TEXT NOT NULL
            );
        """)

        conn.commit()

    _banco_inicializado = True
    carregar_seed_se_vazio()


def obter_conexao() -> sqlite3.Connection:
    global _banco_inicializado
    if not _banco_inicializado:
        inicializar_banco()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


DADOS_VAN_GENUCHTEN = [
    {"classe": "Areia (Sand)", "theta_r": 0.045, "theta_s": 0.430, "alpha": 0.145, "n": 2.68, "m": 0.627, "cc_kpa": 10.0, "pmp_kpa": 1500.0},
    {"classe": "Areia Franca (Loamy Sand)", "theta_r": 0.057, "theta_s": 0.410, "alpha": 0.124, "n": 2.28, "m": 0.561, "cc_kpa": 15.0, "pmp_kpa": 1500.0},
    {"classe": "Franco-Arenoso (Sandy Loam)", "theta_r": 0.065, "theta_s": 0.410, "alpha": 0.075, "n": 1.89, "m": 0.471, "cc_kpa": 20.0, "pmp_kpa": 1500.0},
    {"classe": "Franco (Loam)", "theta_r": 0.078, "theta_s": 0.430, "alpha": 0.036, "n": 1.56, "m": 0.359, "cc_kpa": 25.0, "pmp_kpa": 1500.0},
    {"classe": "Silte (Silt)", "theta_r": 0.034, "theta_s": 0.460, "alpha": 0.016, "n": 1.37, "m": 0.270, "cc_kpa": 30.0, "pmp_kpa": 1500.0},
    {"classe": "Franco-Siltoso (Silt Loam)", "theta_r": 0.067, "theta_s": 0.450, "alpha": 0.020, "n": 1.41, "m": 0.291, "cc_kpa": 30.0, "pmp_kpa": 1500.0},
    {"classe": "Franco-Argilo-Arenoso (Sandy Clay Loam)", "theta_r": 0.100, "theta_s": 0.390, "alpha": 0.059, "n": 1.48, "m": 0.324, "cc_kpa": 28.0, "pmp_kpa": 1500.0},
    {"classe": "Franco-Argiloso (Clay Loam)", "theta_r": 0.095, "theta_s": 0.410, "alpha": 0.019, "n": 1.31, "m": 0.237, "cc_kpa": 33.0, "pmp_kpa": 1500.0},
    {"classe": "Franco-Argilo-Siltoso (Silty Clay Loam)", "theta_r": 0.089, "theta_s": 0.430, "alpha": 0.010, "n": 1.23, "m": 0.187, "cc_kpa": 33.0, "pmp_kpa": 1500.0},
    {"classe": "Argilo-Arenoso (Sandy Clay)", "theta_r": 0.100, "theta_s": 0.380, "alpha": 0.027, "n": 1.23, "m": 0.187, "cc_kpa": 35.0, "pmp_kpa": 1500.0},
    {"classe": "Argiloso (Clay / Latossolo)", "theta_r": 0.070, "theta_s": 0.380, "alpha": 0.008, "n": 1.09, "m": 0.083, "cc_kpa": 40.0, "pmp_kpa": 1500.0}
]

FONTE_EMBRAPA_RR_1997 = "Embrapa-RR (1997), Tabela 17"
FONTE_EMBRAPA_HORTALICAS_2008 = "Embrapa Hortaliças (2008), Tab. 3 e 4"
FONTE_EMBRAPA_ARROZ_FEIJAO_FAO56 = "Embrapa Arroz e Feijão / FAO-56"
FONTE_EMBRAPA_HORTALICAS_FAO56 = "Embrapa Hortaliças / FAO-56"

DADOS_FASES_CULTURA = [
    # Milho
    {"cultura_id": "milho", "fase": "Nascendo / Milho na canela", "raiz_mm": 150, "kc": 0.40, "limiar_arenoso_kpa": 20, "limiar_franco_arenoso_kpa": 25, "limiar_franco_kpa": 25, "limiar_franco_argiloso_kpa": 30, "limiar_argiloso_kpa": 35, "fonte": FONTE_EMBRAPA_RR_1997},
    {"cultura_id": "milho", "fase": "Crescendo / Milho na cintura", "raiz_mm": 350, "kc": 0.83, "limiar_arenoso_kpa": 40, "limiar_franco_arenoso_kpa": 45, "limiar_franco_kpa": 45, "limiar_franco_argiloso_kpa": 55, "limiar_argiloso_kpa": 60, "fonte": FONTE_EMBRAPA_RR_1997},
    {"cultura_id": "milho", "fase": "Soltando pendão e boneca", "raiz_mm": 500, "kc": 1.13, "limiar_arenoso_kpa": 30, "limiar_franco_arenoso_kpa": 35, "limiar_franco_kpa": 35, "limiar_franco_argiloso_kpa": 45, "limiar_argiloso_kpa": 50, "fonte": FONTE_EMBRAPA_RR_1997},
    {"cultura_id": "milho", "fase": "Enchendo grão", "raiz_mm": 500, "kc": 0.88, "limiar_arenoso_kpa": 40, "limiar_franco_arenoso_kpa": 45, "limiar_franco_kpa": 45, "limiar_franco_argiloso_kpa": 55, "limiar_argiloso_kpa": 60, "fonte": FONTE_EMBRAPA_RR_1997},
    {"cultura_id": "milho", "fase": "Grão duro / Secando para colheita", "raiz_mm": 500, "kc": 0.58, "limiar_arenoso_kpa": 65, "limiar_franco_arenoso_kpa": 70, "limiar_franco_kpa": 70, "limiar_franco_argiloso_kpa": 80, "limiar_argiloso_kpa": 85, "fonte": FONTE_EMBRAPA_RR_1997},
    # Tomate
    {"cultura_id": "tomate", "fase": "Pegamento das mudas", "raiz_mm": 120, "kc": 0.60, "limiar_arenoso_kpa": 12, "limiar_franco_arenoso_kpa": 15, "limiar_franco_kpa": 15, "limiar_franco_argiloso_kpa": 20, "limiar_argiloso_kpa": 25, "fonte": FONTE_EMBRAPA_HORTALICAS_2008},
    {"cultura_id": "tomate", "fase": "Crescimento vegetativo", "raiz_mm": 250, "kc": 0.80, "limiar_arenoso_kpa": 25, "limiar_franco_arenoso_kpa": 30, "limiar_franco_kpa": 30, "limiar_franco_argiloso_kpa": 35, "limiar_argiloso_kpa": 40, "fonte": FONTE_EMBRAPA_HORTALICAS_2008},
    {"cultura_id": "tomate", "fase": "Floração e frutificação", "raiz_mm": 400, "kc": 1.15, "limiar_arenoso_kpa": 15, "limiar_franco_arenoso_kpa": 20, "limiar_franco_kpa": 20, "limiar_franco_argiloso_kpa": 25, "limiar_argiloso_kpa": 30, "fonte": FONTE_EMBRAPA_HORTALICAS_2008},
    {"cultura_id": "tomate", "fase": "Maturação dos frutos", "raiz_mm": 400, "kc": 0.80, "limiar_arenoso_kpa": 30, "limiar_franco_arenoso_kpa": 35, "limiar_franco_kpa": 35, "limiar_franco_argiloso_kpa": 45, "limiar_argiloso_kpa": 50, "fonte": FONTE_EMBRAPA_HORTALICAS_2008},
    # Feijão
    {"cultura_id": "feijao", "fase": "Germinação e emergência (V0-V2)", "raiz_mm": 100, "kc": 0.40, "limiar_arenoso_kpa": 15, "limiar_franco_arenoso_kpa": 20, "limiar_franco_kpa": 20, "limiar_franco_argiloso_kpa": 25, "limiar_argiloso_kpa": 30, "fonte": FONTE_EMBRAPA_ARROZ_FEIJAO_FAO56},
    {"cultura_id": "feijao", "fase": "Desenvolvimento vegetativo (V3-V4)", "raiz_mm": 250, "kc": 0.75, "limiar_arenoso_kpa": 30, "limiar_franco_arenoso_kpa": 35, "limiar_franco_kpa": 35, "limiar_franco_argiloso_kpa": 40, "limiar_argiloso_kpa": 45, "fonte": FONTE_EMBRAPA_ARROZ_FEIJAO_FAO56},
    {"cultura_id": "feijao", "fase": "Floração e formação de vagens (R5-R7)", "raiz_mm": 350, "kc": 1.10, "limiar_arenoso_kpa": 20, "limiar_franco_arenoso_kpa": 25, "limiar_franco_kpa": 25, "limiar_franco_argiloso_kpa": 30, "limiar_argiloso_kpa": 35, "fonte": FONTE_EMBRAPA_ARROZ_FEIJAO_FAO56},
    {"cultura_id": "feijao", "fase": "Enchimento de grãos e maturação (R8-R9)", "raiz_mm": 350, "kc": 0.65, "limiar_arenoso_kpa": 45, "limiar_franco_arenoso_kpa": 50, "limiar_franco_kpa": 50, "limiar_franco_argiloso_kpa": 60, "limiar_argiloso_kpa": 65, "fonte": FONTE_EMBRAPA_ARROZ_FEIJAO_FAO56},
    # Alface
    {"cultura_id": "alface", "fase": "Pegamento de mudas (Transplante)", "raiz_mm": 80, "kc": 0.70, "limiar_arenoso_kpa": 10, "limiar_franco_arenoso_kpa": 12, "limiar_franco_kpa": 12, "limiar_franco_argiloso_kpa": 15, "limiar_argiloso_kpa": 18, "fonte": FONTE_EMBRAPA_HORTALICAS_FAO56},
    {"cultura_id": "alface", "fase": "Crescimento vegetativo inicial", "raiz_mm": 150, "kc": 0.90, "limiar_arenoso_kpa": 15, "limiar_franco_arenoso_kpa": 18, "limiar_franco_kpa": 18, "limiar_franco_argiloso_kpa": 22, "limiar_argiloso_kpa": 25, "fonte": FONTE_EMBRAPA_HORTALICAS_FAO56},
    {"cultura_id": "alface", "fase": "Formação de cabeça / Enfolhamento pleno", "raiz_mm": 200, "kc": 1.05, "limiar_arenoso_kpa": 12, "limiar_franco_arenoso_kpa": 15, "limiar_franco_kpa": 15, "limiar_franco_argiloso_kpa": 20, "limiar_argiloso_kpa": 22, "fonte": FONTE_EMBRAPA_HORTALICAS_FAO56},
    {"cultura_id": "alface", "fase": "Pré-colheita", "raiz_mm": 200, "kc": 0.95, "limiar_arenoso_kpa": 18, "limiar_franco_arenoso_kpa": 22, "limiar_franco_kpa": 22, "limiar_franco_argiloso_kpa": 28, "limiar_argiloso_kpa": 30, "fonte": FONTE_EMBRAPA_HORTALICAS_FAO56}
]


def carregar_seed_se_vazio() -> None:
    """Popula os perfis Embrapa, solos e matriz fenológica se vazios."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as total FROM perfis_cultura")
        total_perfis = cursor.fetchone()["total"]

        if total_perfis == 0:
            resetar_dados_demonstracao()

        cursor.execute("SELECT COUNT(*) as total FROM solos_van_genuchten")
        if cursor.fetchone()["total"] == 0:
            for s in DADOS_VAN_GENUCHTEN:
                cursor.execute("""
                    INSERT OR REPLACE INTO solos_van_genuchten (
                        classe, theta_r, theta_s, alpha, n, m, cc_kpa, pmp_kpa
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (s["classe"], s["theta_r"], s["theta_s"], s["alpha"], s["n"], s["m"], s["cc_kpa"], s["pmp_kpa"]))

        cursor.execute("SELECT COUNT(*) as total FROM fases_cultura")
        if cursor.fetchone()["total"] == 0:
            for f in DADOS_FASES_CULTURA:
                cursor.execute("""
                    INSERT INTO fases_cultura (
                        cultura_id, fase, raiz_mm, kc,
                        limiar_arenoso_kpa, limiar_franco_arenoso_kpa, limiar_franco_kpa,
                        limiar_franco_argiloso_kpa, limiar_argiloso_kpa, fonte
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    f["cultura_id"], f["fase"], f["raiz_mm"], f["kc"],
                    f["limiar_arenoso_kpa"], f["limiar_franco_arenoso_kpa"], f["limiar_franco_kpa"],
                    f["limiar_franco_argiloso_kpa"], f["limiar_argiloso_kpa"], f["fonte"]
                ))
        conn.commit()


def resetar_dados_demonstracao() -> Dict[str, Any]:
    """
    Restaura o SQLite para o estado original da demonstração de 5 minutos,
    populando 7 dias de histórico e os perfis Embrapa.
    """
    inicializar_banco()
    if not os.path.exists(SEED_PATH):
        return {"status": "erro", "mensagem": "Arquivo seed_demo_data.json não encontrado"}

    with open(SEED_PATH, "r", encoding="utf-8") as f:
        seed = json.load(f)

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("DELETE FROM alertas_disparados")
        cursor.execute("DELETE FROM leituras_historicas")
        cursor.execute("DELETE FROM perfis_cultura")

        # 1. Insere perfis
        for p in seed.get("perfis_cultura_referencia", []):
            cursor.execute("""
                INSERT INTO perfis_cultura (
                    id_perfil, cultura, solo, profundidade_raiz_cm,
                    tensao_capacidade_campo_kpa, tensao_alerta_kpa,
                    tensao_critica_manejo_kpa, tensao_ponto_murcha_kpa,
                    fonte_cientifica
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                p["id_perfil"], p["cultura"], p["solo"], p["profundidade_raiz_cm"],
                p["tensao_capacidade_campo_kpa"], p["tensao_alerta_kpa"],
                p["tensao_critica_manejo_kpa"], p["tensao_ponto_murcha_kpa"],
                p["fonte_cientifica"]
            ))

        # 2. Insere histórico de 7 dias
        agora = time.time()
        for item in seed.get("historico_simulado_leituras", []):
            dias_atras = item.get("dias_atras", 0)
            ts = agora - (dias_atras * 86400)
            iso = datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
            cursor.execute("""
                INSERT INTO leituras_historicas (
                    no_id, id_perfil, dia_label, timestamp_iso, tensao_kpa, temp_c, bateria_mv, is_simulado
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 1)
            """, (
                item["no_id"], item["id_perfil"], item["dia_label"], iso,
                item["tensao_kpa"], item.get("temp_c", 24.0), item.get("bateria_mv", 3300)
            ))

        conn.commit()

    return {
        "status": "sucesso",
        "perfis_carregados": len(seed.get("perfis_cultura_referencia", [])),
        "leituras_carregadas": len(seed.get("historico_simulado_leituras", []))
    }


def obter_perfis_cultura() -> List[Dict[str, Any]]:
    with obter_conexao() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM perfis_cultura ORDER BY cultura")
        rows = cursor.fetchall()
        return [dict(r) for r in rows]


def obter_perfil_por_id(id_perfil: str) -> Optional[Dict[str, Any]]:
    with obter_conexao() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM perfis_cultura WHERE id_perfil = ?", (id_perfil,))
        row = cursor.fetchone()
        return dict(row) if row else None


def obter_historico_leituras(no_id: Optional[str] = None, id_perfil: Optional[str] = None) -> List[Dict[str, Any]]:
    with obter_conexao() as conn:
        cursor = conn.cursor()
        query = "SELECT * FROM leituras_historicas WHERE 1=1"
        params: List[Any] = []
        if no_id:
            query += " AND no_id = ?"
            params.append(no_id)
        if id_perfil:
            query += " AND id_perfil = ?"
            params.append(id_perfil)
        query += " ORDER BY id ASC"
        cursor.execute(query, tuple(params))
        rows = cursor.fetchall()
        return [dict(r) for r in rows]


def salvar_nova_leitura(
    no_id: str,
    id_perfil: str,
    tensao_kpa: float,
    temp_c: float = 25.0,
    bateria_mv: int = 3300,
    dia_label: str = "Ao Vivo",
    is_simulado: int = 0
) -> Dict[str, Any]:
    iso = datetime.now(timezone.utc).isoformat()
    with obter_conexao() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO leituras_historicas (
                no_id, id_perfil, dia_label, timestamp_iso, tensao_kpa, temp_c, bateria_mv, is_simulado
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (no_id, id_perfil, dia_label, iso, tensao_kpa, temp_c, bateria_mv, is_simulado))
        novo_id = cursor.lastrowid
        conn.commit()

        cursor.execute("SELECT * FROM leituras_historicas WHERE id = ?", (novo_id,))
        return dict(cursor.fetchone())


def registrar_alerta_banco(
    no_id: str,
    id_perfil: str,
    tensao_kpa: float,
    taxa_secagem_kpa_dia: float,
    dias_restantes: float,
    status: str,
    mensagem: str,
    enviado_telegram: int = 1
) -> int:
    iso = datetime.now(timezone.utc).isoformat()
    with obter_conexao() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO alertas_disparados (
                timestamp_iso, no_id, id_perfil, tensao_kpa,
                taxa_secagem_kpa_dia, dias_restantes, status, mensagem, enviado_telegram
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            iso, no_id, id_perfil, tensao_kpa, taxa_secagem_kpa_dia,
            dias_restantes, status, mensagem, enviado_telegram
        ))
        conn.commit()
        return cursor.lastrowid


def obter_solos_van_genuchten() -> List[Dict[str, Any]]:
    """Retorna os parâmetros hidráulicos de Van Genuchten das 11 classes texturais."""
    with obter_conexao() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM solos_van_genuchten ORDER BY cc_kpa ASC")
        return [dict(r) for r in cursor.fetchall()]


def obter_fases_cultura(cultura_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retorna as fases fenológicas, profundidade de raiz, Kc e limites por solo."""
    with obter_conexao() as conn:
        cursor = conn.cursor()
        if cultura_id:
            cursor.execute("SELECT * FROM fases_cultura WHERE cultura_id = ? ORDER BY id ASC", (cultura_id,))
        else:
            cursor.execute("SELECT * FROM fases_cultura ORDER BY cultura_id, id ASC")
        return [dict(r) for r in cursor.fetchall()]
