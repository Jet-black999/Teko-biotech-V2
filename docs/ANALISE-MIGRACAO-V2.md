# Análise para migração ao fork Tekó V2

> Registro da análise anterior ao plano. A recomendação de React e de reaproveitamento visual foi posteriormente revisada: as telas serão redesenhadas e a tecnologia será escolhida na entrega visual. Consulte o [Plano de implementação V2](../PLANO-IMPLEMENTACAO-V2.md) para a direção atual.

Data: 16/11/2026. Análise do código e do histórico Git disponíveis no notebook. Não foi realizada transferência de código, merge, commit ou push. Não foram executados serviços, testes funcionais ou envios ao Telegram. A consulta ao GitHub falhou por resolução DNS; a igualdade com o remoto se refere às referências já disponíveis localmente.

## 1. Situação dos repositórios

| Local | Situação observada | Uso proposto |
| --- | --- | --- |
| `Teko-biotech-V2/` | Fork `Jet-black999/Teko-biotech-V2`; branch `main`, commit `73dc025`; árvore limpa; apenas remoto `origin` | Base do desenvolvimento pessoal |
| `PROJETO-HACKATON-2026/` | Origin `brunoluiztv/PROJETO-HACKATON-2026`; branch aberta `pr/integracao-total-biossensor-e-identidade-visual`, commit `7e49814`; 26 arquivos rastreados modificados e 17 arquivos novos | Fonte das melhorias locais de integração |
| Branch `feat/frontend-integracao-gh-pages` do repositório antigo | Commit `48752ef`; contém melhorias React e o pacote `monitoring_bot` | Fonte de recursos anteriores que não chegaram à main do fork |
| `gp3/` | Sem commits e sem remotos | Não é fonte de histórico Git para esta migração |

O commit atual da pasta antiga é ancestral da main do fork: há **32 commits posteriores** no fork. Portanto, a pasta antiga combina uma base desatualizada com alterações locais importantes.

A branch de recursos `48752ef` diverge da main do fork: há **11 commits exclusivos nessa branch e 37 exclusivos na main do fork**. Seus arquivos não devem substituir a árvore inteira da main.

O fork e `origin/main` da pasta antiga apontam localmente para `73dc025`. Isso confirma a mesma base nos históricos consultados, mas não confirma novas alterações que possam ter ocorrido no GitHub após o último fetch.

## 2. O que já existe no fork

- `backend/app/`: API modular v1, catálogo de perfis/canais, ingestão autenticada, deduplicação, heartbeat, histórico, regras de alerta e fila persistente de notificações. É a base genérica para diferentes sensores.
- `backend/server.py`, `backend/database.py` e `backend/motor_predicao.py`: outra aplicação FastAPI, dedicada à telemetria fitoeletrônica, solos, culturas e predição. Não é automaticamente a mesma aplicação de `backend/app/main.py`.
- `backend/llm_engine.py`: processamento de diagnóstico com integração a LLM e fallback, acompanhado de testes no repositório.
- `frontend/`: React/TypeScript/Vite com perfis de análise e modo conectado ao contrato v1. Ainda não contém todas as melhorias da branch local de frontend.
- `web/`: painel PWA com identidade visual mais recente, conteúdo agronômico e simulador 3D em Three.js.
- `bot/phytosense_bot.py`, `bot/audio_processor.py` e `bot/telemetria.py`: experiência de conversa, telemetria e tratamento de áudio. Não correspondem ao cliente `monitoring_bot` desenvolvido anteriormente.
- `firmware/`: variantes de nó e gateway, incluindo gateway com fila LittleFS. Existem também sketches em `ESPs32 - Hard/` e na raiz, exigindo definição dos modelos oficiais.

Existência de código e testes não equivale a validação física. Nenhuma capacidade foi revalidada em hardware ou Telegram nesta análise.

## 3. O que aproveitar das alterações locais não commitadas

| Recurso | Caminhos de origem | Recomendação |
| --- | --- | --- |
| API e painel na mesma origem | `backend/integration.py`, `backend/server.py`, `web/js/api.js`, `iniciar_integracao.sh` | Integrar mantendo as rotas e o ciclo de vida novos do fork |
| Persistência de telemetria e projeção v1 | `backend/integration_store.py`, `backend/integration.py` | Aproveitar a lógica; decidir qual armazenamento será a fonte principal |
| Cadastro de sensor físico | `backend/app/provision.py`, `backend/app/manage.py`, `backend/examples/esp32-device.json` | Migrar o cadastro explícito de nó, canal e unidade |
| Ponte HTTP/serial para ESP32 | `backend/esp_bridge.py`, `backend/requirements-hardware.txt`, `firmware/umidade_painel/` | Preservar como opção de bancada e validar com a placa escolhida |
| Falha de conexão exibida como indisponibilidade | `bot/telemetria.py`, alterações no painel e bot | Integrar sem perder o áudio e os recursos novos do fork |
| Preservação de medições físicas ao resetar demo | `backend/database.py` | Prioridade alta: portar para a versão atualizada |
| Cálculo de taxa pelo tempo decorrido | `backend/motor_predicao.py` | Portar com os testes relevantes e revisar as condições de histórico insuficiente |
| Separação de ADC, estimativas, simulação e medições físicas | Backend, bot, painel e configurações do firmware | Manter essa distinção em todo o fluxo |
| Evidências de integração | `backend/tests/test_integration.py`, alterações em testes existentes, `INTEGRACAO.md` | Portar os cenários junto das funcionalidades correspondentes |

A ponte de bancada mantém pendências em RAM e não garante retenção após reinício. Isso é diferente da fila LittleFS do gateway. Um percentual calibrado ou ADC convertido por fórmula demonstrativa também não deve ser apresentado como tensão em kPa efetivamente medida.

## 4. O que recuperar da branch de recursos

Fonte: `PROJETO-HACKATON-2026`, branch `feat/frontend-integracao-gh-pages`, commit `48752ef`.

- `bot/monitoring_bot/`: cliente da API, validação de contratos, comandos autorizados, worker de notificações com reserva e confirmação, transporte HTTP do Telegram e configuração automática.
- `iniciar_telegram.py` e `backend/app/local_setup.py`: preparação local e inicialização. A versão dessa branch também contém opções de modo local, demonstração, verificação e IP de rede. O iniciador usa banco isolado e precisa ser adaptado ao ponto de entrada definitivo.
- Testes `bot/tests/test_backend_*.py`, testes de contrato e configuração no backend e documentação das entregas do bot.
- Componentes React `FarmerOverview`, `LocalWeather`, `PropertySimulator`, `ThemeToggle`, melhorias em `LiveApp`, animação da planta, identidade visual e regras de apresentação em `frontend/src/domain/status.ts`.

Recuperar esses módulos com suas dependências e testes. O commit agregador altera outros componentes; aplicar a branch inteira poderia reintroduzir versões antigas de arquivos que evoluíram no fork.

## 5. Conflitos e problemas concretos

**Há mudanças dos dois lados em 13 arquivos:**

`ESPs32 - Hard/esp1_sensor/esp1_sensor.ino`, `backend/database.py`, `backend/motor_predicao.py`, `backend/server.py`, `backend/tests/test_api.py`, `bot/phytosense_bot.py`, `bot/telemetria.py`, `bot/tests/test_bot.py`, `web/css/styles.css`, `web/index.html`, `web/js/app.js`, `web/js/charts.js`, `web/sw.js`.

Uma verificação com `git apply --check` do diff local contra o fork encontrou falhas de aplicação em 9 arquivos. Essa operação apenas verificou o patch; não o aplicou. Os 17 arquivos novos não colidem em nome com arquivos atuais do fork, mas vários dependem de alterações nos arquivos compartilhados.

Pontos que exigem integração manual:

1. **Ciclo de vida da API:** o fork inicializa/encerra o motor LLM no lifespan de `server.py`. A integração local atribui outro lifespan para banco, projeção e worker. A versão final deve executar ambos os conjuntos de tarefas e encerrá-los corretamente.
2. **Duas filas de mensagens:** já existe a fila v1; a integração local adiciona `telegram_outbox` no banco de telemetria. Usar os dois fluxos para a mesma ocorrência pode gerar mensagens duplicadas. A recomendação é consolidar na fila v1 e em um worker de envio.
3. **Dois bots:** o bot do fork tem experiência visual/áudio; `monitoring_bot` tem controle de acesso e envio persistente. Devem alimentar um único processo de recebimento de comandos por token.
4. **Dois bancos:** a integração local projeta dados v1 no banco fitoeletrônico. É uma solução de transição, com necessidade de rastreabilidade e recuperação. A varredura de todo o histórico a cada sincronização merece substituição por processamento incremental se esse caminho for mantido.
5. **Reset destrutivo no fork:** `resetar_dados_demonstracao()` apaga todo o histórico e os alertas nas tabelas da aplicação fitoeletrônica. A melhoria local preserva leituras físicas e deve ser adaptada antes de usar dados reais nessa aplicação.
6. **Confirmação de envio:** rotas ADC/gateway do fork registram `enviado_telegram=1` antes de executar o envio em background. Migrar para confirmação após resposta válida do Telegram e tentativas persistentes.
7. **Endereços fixos:** partes do painel e bot ainda usam `127.0.0.1:8000`. No celular isso aponta para o próprio celular. A configuração do bot também contém URL padrão do GitHub Pages do repositório original. Centralizar URLs e ajustar para o fork/deploy escolhido.
8. **Demonstração e operação real:** `bot/telemetria.py` no fork possui fallback para dados simulados quando a API falha. A alteração local retorna indisponibilidade. Preservar demonstração explícita e impedir interpretações de valores inventados como leituras atuais.
9. **Documentação desatualizada:** o README do fork ainda descreve bot inicial e concentra o produto em React, embora haja implementação fitoeletrônica, áudio e painel PWA. Reescrever o estado do produto após escolher a composição final.

## 6. Arquitetura recomendada para o fork pessoal

Usar a main atual do fork como base e evoluir por módulos:

- **Dados:** contrato v1 e perfis de análise como núcleo genérico; recursos de solo e bioimpedância como módulos opcionais de análise. Registrar unidade, origem e qualidade da medição.
- **API:** um ponto de entrada com configuração consistente; serviços especializados por trás dele. Preservar as rotas atuais durante a transição, com adaptadores quando necessário.
- **Interface:** recomendar React como aplicação principal, aproveitando o visual e os recursos úteis do `web/`. Manter o painel existente funcional durante a migração. Isso é uma proposta; a escolha visual pode seguir a preferência pessoal do proprietário do fork.
- **Telegram:** um bot, com a experiência de conversa/áudio desejada e os mecanismos de autorização, consulta e notificações persistentes recuperados do trabalho anterior.
- **Hardware:** gateway/nó v1 como caminho distribuído; ponte serial/HTTP como caminho de bancada. Documentar cada variante e evitar manter cópias divergentes do mesmo firmware.
- **Demonstração:** modo separado de dados reais. LLM, 3D e predição devem ser recursos opcionais e não pré-requisitos da coleta.

## 7. Transferência proposta em entregas

1. **Preservação:** registrar a branch e o commit de origem, salvar alterações rastreadas e os 17 novos arquivos, incluindo versões de firmware. Separar backups privados de bancos/configurações da transferência de código. Não incluir `.env`, tokens, `.runtime`, bancos de execução, `.venv` ou `node_modules` em commits. Não descartar a pasta antiga.
2. **Preparação do fork:** criar uma branch de integração a partir da main atual e cadastrar o original como `upstream`; manter `origin` apontando para o fork. Buscar novidades quando a conexão permitir e registrar a base usada.
3. **Núcleo confiável:** integrar cadastro físico, persistência, distinção de origem, proteção de dados no reset e correções de confirmação de envio. Adaptar a inicialização sem perder o LLM existente.
4. **Bot:** recuperar os módulos da branch `48752ef`, decidir os comandos oficiais e integrar a experiência de áudio. Consolidar fila/worker e configuração.
5. **Interface:** recuperar os componentes React selecionados, integrar recursos desejados do painel atual e unificar configuração da API para notebook e celular.
6. **Hardware e encerramento:** selecionar firmware oficial, integrar a ponte de bancada se útil, revisar documentação e executar validação ponta a ponta.

Cada entrega deve ter commits próprios e comparação revisável. A escolha é por funcionalidades; copiar arquivos completos ou fazer merge indiscriminado não resolve as divergências observadas.

## 8. Validação após a migração

Executar os testes afetados por cada entrega e, ao final, verificar:

- ingestão, duplicata e conflito; histórico preservado após reinício;
- reset de demonstração sem perda de medições físicas;
- ADC bruto, valores estimados e unidades apresentados corretamente;
- API indisponível sem fabricar leituras;
- mesma leitura no dashboard e Telegram;
- abertura/recuperação de alerta, retentativa e ausência de dois emissores concorrentes;
- acesso pelo celular usando o IP do notebook;
- LLM/áudio/3D preservados quando selecionados;
- perda de conexão, reconexão e retenção de dados de acordo com o firmware utilizado.

O próximo passo recomendado é a entrega 1 e a criação da branch de integração. A seleção final de interface e recursos agronômicos pode ser feita durante as entregas seguintes, sem bloquear a preservação do trabalho.
