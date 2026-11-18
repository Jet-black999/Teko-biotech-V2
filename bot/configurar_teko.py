"""Configura o menu público do Phytosense; executar explicitamente pelo operador."""
import os
from pathlib import Path

import telebot
from dotenv import load_dotenv
from telebot.types import BotCommand, MenuButtonCommands, MenuButtonWebApp, WebAppInfo

from backend_client import BackendClient
from monitoring import dashboard_link

NOME_BOT = "Tekó — Monitoramento da lavoura"
SHORT_DESC = "Consulte os pontos da lavoura, leituras e alertas e abra o painel Tekó."
LONG_DESC = "Acompanhe leituras, atualização dos pontos e ocorrências. Abra o painel para gráficos e histórico. Dados demonstrativos são identificados como simulação."
COMANDOS_TEKO = [BotCommand(cmd, desc) for cmd, desc in [
    ("start", "Começar"), ("status", "Últimas leituras da lavoura"), ("planta", "Consultar leituras"),
    ("sensores", "Pontos e comunicação"), ("alertas", "Ocorrências ativas"),
    ("painel", "Abrir gráficos e histórico"), ("ajuda", "Como usar o Tekó"),
]]


def main():
    load_dotenv(Path(__file__).with_name(".env"))
    token = os.getenv("TELEGRAM_TOKEN", "").strip()
    service_token = os.getenv("BOT_SERVICE_TOKEN", "").strip()
    if not token or not service_token:
        raise SystemExit("Configure TELEGRAM_TOKEN e BOT_SERVICE_TOKEN em bot/.env.")
    api = BackendClient(os.getenv("BACKEND_API_URL", "http://127.0.0.1:8000"), service_token)
    config = api.config()
    url = dashboard_link(config.get("dashboard_url"))
    bot = telebot.TeleBot(token)
    bot.set_my_name(NOME_BOT)
    bot.set_my_short_description(SHORT_DESC)
    bot.set_my_description(LONG_DESC)
    bot.set_my_commands(COMANDOS_TEKO)
    # Limpa também o Mini App antigo quando só há endereço HTTP local.
    menu = MenuButtonWebApp(text="Painel Tekó", web_app=WebAppInfo(url=url)) if url and url.startswith("https://") else MenuButtonCommands()
    bot.set_chat_menu_button(menu_button=menu)
    print("Menu Tekó atualizado. Os arquivos .env foram preservados.")


if __name__ == "__main__":
    main()
