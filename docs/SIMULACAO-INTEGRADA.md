# Simulação integrada — frontend, backend e Telegram

Esta entrega acrescenta uma ferramenta nas configurações do frontend para
salvar valores fictícios na mesma API consultada pelo painel e pelo bot.
O usuário confirmou o teste da integração inicial do Telegram. Os avisos
produzidos por esta ferramenta ainda precisam do ensaio no chat real.

## Preparar uma vez

Na pasta `backend/`, com seu ambiente virtual ativo:

```bash
python -m app.manage init-db
python -m app.manage prepare-simulator
python -m app.manage issue-token gateway-simulator
```

O esquema passa para **5**, preservando os dados existentes. `prepare-simulator`
é repetível: cria um gateway, um ponto e um canal exclusivos do simulador,
um perfil numérico fictício e uma regra experimental. Não cria leituras,
não apaga histórico e não rotaciona tokens. O último comando emite/rotaciona
somente a credencial do simulador: copie o token localmente para usar na tela.
Os tokens do Telegram e do serviço do bot permanecem os mesmos.

No `backend/.env`, acrescente:

```dotenv
SIMULATOR_ENABLED=true
```

Reinicie a API atual (`app.main:app`). O simulador fica desabilitado por padrão.
Mantenha o bot em execução com o backend, banco e chat já configurados.

## Usar pelo celular ou computador

1. No frontend oficial, abra a engrenagem e salve o endereço da API atual.
2. Clique em **Abrir simulação integrada**.
3. Cole a credencial de `gateway-simulator`. Ela fica apenas em memória e é
   descartada ao fechar a ferramenta; não use tokens do bot ou do BotFather.
4. Salve um valor de 0 a 100 ou clique em **Enviar valores de alerta**.
   Esse botão salva as amostras fictícias 20, 21 e 22 com horário atual.
5. Clique em **Ver leituras e alertas no painel**. O painel abre no modo API,
   selecionando `node-simulator` / `signal-01`. Confira gráfico, histórico e
   ocorrência. `/status`, `/sensores` e `/alertas` consultam esse mesmo ponto.
6. Aguarde o worker entregar o aviso de teste no Telegram. O link do aviso
   abre o ponto/canal no frontend.
7. Reabra a ferramenta e envie **recuperação** (36, 37, 38). Confira a ocorrência
   resolvida e a mensagem de recuperação.

As três amostras de um botão pertencem ao mesmo lote e usam o mesmo horário.
São valores de roteiro, sem equivalência a um sensor físico ou recomendação
agronômica. Envios manuais sucessivos acrescentam pontos no histórico temporal.

A regra abre após 3 amostras consecutivas abaixo de 30 e recupera após 3 em
35 ou mais, respeitando o intervalo máximo de 300 segundos. Se houver pausa
maior, use novamente o botão de 3 amostras para completar a transição. Uma
regra desativada é informada na ferramenta e não é reativada pela preparação.

O ponto do simulador não tem rádio: contato desconhecido é esperado. Recência
da amostra e contato por rádio continuam sendo informações diferentes.

## Falhas e reenvio

Cada envio recebe um UUID. Leituras, avaliações, ocorrências, notificações e
recibo desse UUID são gravados na mesma transação. Repetir a tentativa com os
mesmos valores retorna o recibo original; usar outros valores no mesmo UUID
retorna conflito. A sequência é alocada no servidor sob transação SQLite.

Se faltar confirmação de rede, use **Tentar novamente o mesmo envio**, mantendo
a tela aberta. Isso não cria outra amostra nem outra ocorrência. Após fechar
ou recarregar a ferramenta, a tentativa em memória é descartada; confira o
histórico antes de iniciar um novo envio se o resultado anterior ficou incerto.

Salvar na API não significa que a mensagem já chegou ao Telegram. O bot usa a
outbox e suas retentativas existentes. Se ele estiver parado, o aviso permanece
pendente. Para bloquear novos envios do simulador, defina
`SIMULATOR_ENABLED=false` e reinicie a API; o histórico permanece disponível.

## Contrato adicional

- `GET /api/v1/simulator/config`: disponibilidade, cadastro e regra do simulador.
- `POST /api/v1/simulator/readings`: exige o token exclusivo de `gateway-simulator`.
  Corpo: `request_id` UUID e `values`, com 1 a 6 números finitos entre 0 e 100.
  Campos de identidade, origem e horário são determinados pelo servidor.
- Essa credencial é restrita ao POST do simulador. Credenciais de outros
  gateways e do serviço do bot não permitem escrever por essa ferramenta.

A aplicação continua usando `/api/v1/readings`, `/devices` e `/alerts` para
consulta e ingestão normal. O simulador chama os mesmos serviços de ingestão
e avaliação dentro da transação; não há motor paralelo de alertas.
