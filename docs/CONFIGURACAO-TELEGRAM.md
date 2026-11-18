# Configurar o Telegram — Phytosense / Tekó

O procedimento atual está no [README do bot](../bot/README.md).
O processo oficial usa `phytosense_bot.py`, a API de `backend/app/` e o painel
`frontend/`. Firmware e aquisição ESP ficam para uma etapa posterior.

1. Crie o bot pelo BotFather e coloque o token somente em `bot/.env` como
   `TELEGRAM_TOKEN`.
2. No banco do backend que será utilizado, execute
   `python -m app.manage issue-bot-token` e configure esse token interno como
   `BOT_SERVICE_TOKEN` no bot. Configure também `BACKEND_API_URL`.
3. Em `backend/.env`, defina `AUTHORIZED_TELEGRAM_CHAT_ID` e `DASHBOARD_URL`.
   O bot informa o ID do chat ao recusar uma consulta não autorizada.
4. Reinicie a API. Inicie o frontend e `python phytosense_bot.py` em `bot/`.
5. Execute explicitamente `python configurar_teko.py` para atualizar o menu
   público no Telegram. O configurador preserva seus arquivos `.env`.
6. Siga o ensaio com leituras simuladas no README do bot antes do aceite.

O endereço do painel deve ser o frontend oficial. Com HTTP local, `/painel`
envia um link comum para uso na mesma rede. Para Mini App, configure o frontend
em HTTPS com API alcançável por esse frontend. A publicação antiga de `web/`
no GitHub Pages não representa a publicação de `frontend/` nem da API atual.

Um único processo deve fazer polling por token. Para a integração no notebook,
pare uma eventual instância remota do mesmo bot antes de iniciar o processo
local. O deploy remoto exige backend acessível a esse serviço; `localhost`
remoto não aponta para o notebook.
