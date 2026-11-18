# Bot Phytosense / Tekó — integração com o backend v1

O processo oficial é `phytosense_bot.py`. Ele consulta a API FastAPI em
`backend/app/`, atende somente o chat autorizado e entrega notificações da
outbox persistida pelo backend. Não acessa o SQLite nem consulta `backend/server.py`.

## Preparar

No diretório `bot/`:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
```

Se `.env` já existir, edite-o preservando os valores locais.
Configure `TELEGRAM_TOKEN`, `BACKEND_API_URL` e `BOT_SERVICE_TOKEN`.
O token interno é emitido no ambiente do backend:

```bash
cd backend
python -m app.manage issue-bot-token
```

Esse comando rotaciona a credencial interna anterior. Copie o valor exibido
somente para `BOT_SERVICE_TOKEN` no bot. O token do BotFather permanece no bot.

Em `backend/.env`, configure:

```dotenv
AUTHORIZED_TELEGRAM_CHAT_ID=ID_REAL_DO_CHAT
DASHBOARD_URL=http://IP_DO_NOTEBOOK:5173
```

Reinicie a API depois de alterar sua configuração. Envie `/start` ao bot para
conhecer o ID do chat caso ele ainda não esteja autorizado. Antes da
configuração inicial, o bot informa somente o ID e não consulta dados nem
reserva notificações. Depois de salvar o ID, reinicie a API.

Inicie a API com `python -m uvicorn app.main:app --host 0.0.0.0 --port 8000`
a partir de `backend/`. Inicie o frontend conforme seu README. Em `bot/`:

```bash
python phytosense_bot.py
```

Mantenha um único processo de polling por token Telegram. Para este ensaio,
execute no notebook: um bot hospedado remotamente não alcança `127.0.0.1`
ou o IP privado do notebook. `BOT_WORKER_ID` identifica o worker local.

## Atendimento

| Comando | Resposta |
| --- | --- |
| `/start`, `/ajuda` | Menu de botões grandes e instruções. |
| `/status`, `/planta` | Últimas leituras por ponto e canal. |
| `/sensores` | Pontos cadastrados e contato por rádio. |
| `/alertas` | Até 10 ocorrências ativas; demais detalhes no painel. |
| `/painel`, `/graficos` | Abre o frontend oficial no modo API. |

As respostas preservam unidade, zero, falso, erro de aquisição, origem simulada
ou física e recência. Nenhuma falha da API é substituída por dados fictícios.
Áudio recebe orientação para usar os botões; o bot não interpreta a gravação.
Os antigos diagnósticos fixos, comandos de irrigação e laudos não fazem parte
deste atendimento. `telemetria.py`, `conteudo.py` e `agrosponge_telegram_bot.py`
permanecem como código anterior e não são importados pelo processo oficial.

`DASHBOARD_URL` deve apontar para `frontend/`, não para o antigo `web/`.
O link recebe `mode=live`, preservando os demais parâmetros. HTTP local usa
link comum e exige celular na mesma LAN. HTTPS em chat privado usa botão
Mini App. Configure a origem exata em `CORS_ORIGINS` no backend e o endereço
acessível da API no frontend (`VITE_API_BASE_URL` ou campo de conexão).
Publicar só o frontend não publica a API.

## Configurar o menu público

Após preparar a configuração, o operador pode executar explicitamente:

```bash
python configurar_teko.py
```

Isso atualiza nome, descrição e comandos no Telegram. HTTPS habilita o botão
Mini App; HTTP usa menu de comandos e `/painel` envia o link comum. O script
não modifica arquivos `.env`. `setup_telegram_bot.py` chama o mesmo configurador.

## Entrega e retentativas

A cada 5 segundos o worker consulta a configuração e reserva uma notificação.
Envia o texto como texto simples, confirma o ID real retornado pelo Telegram
ou informa falha resumida. O backend controla prazo da reserva e retentativas.
Se apenas a confirmação HTTP falhar, o processo tenta confirmá-la novamente
sem reenviar enquanto a reserva estiver válida. Reinício ou expiração da
reserva após aceite externo ainda podem causar repetição: a entrega não é
exatamente uma vez. Desligar o bot não impede a API de armazenar leituras.

## Ensaio sem ESP

1. Use uma API e banco de ensaio conforme `backend/ENTREGA-FINAL-BACKEND.md`,
   substituindo o chat fictício pelo seu chat e o painel pelo IP do notebook.
2. Configure `BACKEND_API_URL` do bot para a porta do ensaio (8001 no roteiro),
   e emita o token interno nesse mesmo banco. Inicie apenas um bot.
3. Consulte `/status`, `/sensores` e `/painel` no celular.
4. Execute `backend/examples/send-demo-readings.py` com os três valores de
   abertura (20, 21, 22), uma sessão nova e o token do gateway desse banco.
5. Confira `/alertas`, recebimento de aviso de simulação e estado `sent` na
   fila interna. Envie os valores de recuperação (36, 37, 38) continuando a
   sequência da mesma sessão e confira o aviso de recuperação.
6. Pare a API: o bot deve informar indisponibilidade. Reinicie-a e repita a consulta.
7. Pare o bot, gere outra ocorrência e reinicie o bot: a fila deve entregar
   o aviso pendente. Um chat diferente deve ser recusado.

Testes locais, a partir da raiz do repositório (dependências do bot e backend):

```bash
python -m pytest bot/tests/test_bot.py backend/tests/test_bot_integration.py
```

Esses testes usam transporte Telegram simulado. O recebimento real exige o
ensaio com suas credenciais; testes não iniciam polling nem enviam mensagens.
