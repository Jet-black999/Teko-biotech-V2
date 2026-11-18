"""Tekó / Phytosense: consultas via API v1 e entrega da outbox Telegram."""
import logging
import os
import re
import threading
from pathlib import Path

import telebot
from dotenv import load_dotenv
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup, WebAppInfo

from backend_client import BackendClient, BackendError
from monitoring import Monitoring, NotificationWorker, dashboard_link

load_dotenv(Path(__file__).with_name(".env"))
logger = logging.getLogger(__name__)
TOKEN = os.getenv("TELEGRAM_TOKEN", "").strip()
# Texto simples também para notificações: conteúdo da API não é HTML/Markdown.
bot = telebot.TeleBot(TOKEN or "0:invalido", parse_mode=None)
api = BackendClient(os.getenv("BACKEND_API_URL", "http://127.0.0.1:8000"), os.getenv("BOT_SERVICE_TOKEN", ""))
monitor = Monitoring(api)
BUTTONS = {"🌱 Como estão os pontos?": "status", "📡 Meus pontos": "sensores", "🔔 Alertas": "alertas", "📊 Abrir painel": "painel", "❓ Ajuda": "ajuda"}


def main_menu_keyboard():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(*(KeyboardButton(label) for label in BUTTONS))
    return markup


def panel_keyboard(config, private=True):
    url = dashboard_link(config.get("dashboard_url"))
    if not url:
        return None
    markup = InlineKeyboardMarkup()
    if url.startswith("https://") and private:
        markup.add(InlineKeyboardButton("📊 Abrir painel Tekó", web_app=WebAppInfo(url=url)))
    else:
        markup.add(InlineKeyboardButton("📊 Abrir painel Tekó", url=url))
    return markup


def send_text(chat_id, text, **kwargs):
    # Evita ultrapassar o limite do Telegram mesmo com muitos canais cadastrados.
    for start in range(0, len(text), 3500):
        bot.send_message(chat_id, text[start:start + 3500], parse_mode=None, **kwargs)


def authorized_config(message):
    try:
        config = api.config()
    except BackendError:
        send_text(message.chat.id, "Não consegui consultar a configuração do monitoramento. Tente novamente em instantes.")
        return None
    if not config.get("authorized_chat_id"):
        send_text(message.chat.id, f"Para liberar o acesso, configure este ID de chat no backend: {message.chat.id}.")
        return None
    if str(message.chat.id) != config["authorized_chat_id"]:
        send_text(message.chat.id, f"Este chat ainda não está autorizado para consultar a lavoura. ID deste chat: {message.chat.id}.")
        return None
    return config


@bot.message_handler(content_types=["voice", "audio"])
def handle_voice(message):
    if authorized_config(message):
        send_text(message.chat.id, "🎙️ Nesta versão, use os botões abaixo para consultar leituras e alertas. O conteúdo do áudio não é interpretado.", reply_markup=main_menu_keyboard())


@bot.message_handler(content_types=["text"])
def handle_questions(message):
    config = authorized_config(message)
    if not config:
        return
    text = (message.text or "").strip()
    command = BUTTONS.get(text, text.split("@", 1)[0].split(" ", 1)[0].lstrip("/").lower())
    command = {"planta": "status", "graficos": "painel", "sensores": "sensores"}.get(command, command)
    try:
        if command == "status":
            response = monitor.status()
        elif command == "sensores":
            response = monitor.sensors()
        elif command == "alertas":
            response = monitor.alerts()
        elif command == "painel":
            url = dashboard_link(config.get("dashboard_url"))
            response = "📊 Confira leituras, histórico e alertas no painel Tekó."
            if not url:
                response = "O endereço do painel ainda não foi configurado no backend."
            elif url.startswith("http://"):
                response += f"\nNa demonstração local, conecte o celular à mesma rede do notebook.\n{url}"
            send_text(message.chat.id, response, reply_markup=panel_keyboard(config, message.chat.type == "private"))
            return
        else:
            response = ("🌱 Olá! Eu sou o Tekó. Acompanhe os pontos da sua lavoura pelos botões abaixo.\n\n"
                        "/status — últimas leituras (também /planta)\n/sensores — pontos e comunicação\n"
                        "/alertas — ocorrências ativas\n/painel — gráficos e histórico\n/ajuda — este menu\n\n"
                        "As leituras fictícias são identificadas como simulação. Se a conexão falhar, informarei a indisponibilidade.")
        send_text(message.chat.id, response, reply_markup=main_menu_keyboard())
    except BackendError:
        send_text(message.chat.id, "Não consegui consultar os dados da lavoura agora. Tente novamente em instantes.", reply_markup=main_menu_keyboard())


def main():
    if not TOKEN or TOKEN in {"SEU_TOKEN_AQUI", "coloque_o_token_do_BotFather_aqui"}:
        raise SystemExit("Configure TELEGRAM_TOKEN em bot/.env.")
    if not api.token:
        raise SystemExit("Configure BOT_SERVICE_TOKEN com o token emitido por app.manage issue-bot-token.")
    worker_id = os.getenv("BOT_WORKER_ID", "phytosense-local-1")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,79}", worker_id):
        raise SystemExit("BOT_WORKER_ID inválido; use até 80 letras, números, ponto, hífen, dois-pontos ou sublinhado.")
    stop = threading.Event()
    worker = NotificationWorker(api, lambda chat, text: bot.send_message(chat, text, parse_mode=None, timeout=10), worker_id)
    thread = threading.Thread(target=worker.run, args=(stop,), daemon=True, name="telegram-outbox")
    thread.start()
    try:
        bot.infinity_polling(timeout=20, long_polling_timeout=20)
    finally:
        stop.set()
        thread.join(timeout=15)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
