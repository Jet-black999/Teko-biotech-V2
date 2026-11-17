# Entrega 0 — preparação da V2

Data: 16/11/2026. Resultado: preservação e preparação concluídas; instalação limpa e suíte completa permanecem bloqueadas conforme diagnóstico abaixo. Não houve migração funcional nem envio de mensagens.

## Base e branch

- Fork: `Jet-black999/Teko-biotech-V2`.
- Base local: `73dc025c854fe303fe08719b228994b08e19a775`.
- Branch criada: `chore/preparacao-v2`.
- `origin` permanece no fork; `upstream` foi cadastrado como `brunoluiztv/PROJETO-HACKATON-2026`.
- As duas consultas `git ls-remote` falharam com `Could not resolve host: github.com`. Nenhuma atualização remota foi integrada. Conferir os remotos novamente quando a conexão permitir, antes de decidir mudar a base.
- Não foram criados commits nem realizados pushes nesta entrega. Documentação e `.gitignore` estão disponíveis como alterações revisáveis na branch.

## Preservação e recuperação

Snapshot válido no notebook:

```text
/home/emporio/UERGS/hackathon/backups-privados/teko-v2-20261116-154156/
```

O diretório de backup é privado e não fica dentro do fork. Não deve ser publicado: contém histórico, configurações e bancos locais.

| Fonte | Estado preservado | Verificação |
| --- | --- | --- |
| Projeto antigo | HEAD `7e49814`, todas as refs incluídas no bundle, 26 arquivos modificados e 17 novos | Bundle verificado; restauração em diretório temporário; hashes e modos conferidos |
| Branch de recursos antiga | `feat/frontend-integracao-gh-pages` em `48752ef` | Histórico incluído no mesmo bundle |
| Fork antes da preparação | HEAD `73dc025`, 2 documentos modificados e 2 novos | Bundle verificado; restauração e hashes conferidos |
| Configurações/dados privados | 6 arquivos encontrados na origem antiga; nenhum no fork | Cópias separadas; bancos SQLite via backup e `integrity_check` |

Cada fonte possui `state.json`, `manifest.json`, `history.bundle`, `index.patch`, `worktree.patch` e cópias dos arquivos relevantes. O manifesto registra caminho, tamanho, SHA-256, permissões, arquivos novos e exclusões. Configurações e bancos ficam em `private/`, com manifesto próprio.

`verification.json` registra as verificações; `RECUPERACAO.md` e `restaurar.py` explicam e executam a reconstrução em destino novo. O script foi executado com sucesso para ambas as fontes. Ele restaura o código em checkout destacado e não aplica configurações privadas automaticamente.

Exemplo, a partir da pasta do snapshot e usando um destino ainda inexistente:

```bash
python3 restaurar.py PROJETO-HACKATON-2026 /tmp/teko-origem-recuperada
```

Na recuperação operacional, interromper escritores antes de restaurar bancos, preservar dados posteriores ao snapshot e usar código compatível com o esquema. O ensaio desta entrega verificou estrutura/integridade das cópias SQLite, não a equivalência funcional de uma instalação completa restaurada.

## Mapa de transferência

| Origem | Recurso/destino pretendido | Dependências e conflitos |
| --- | --- | --- |
| Fork atual | Base da V2, recursos de áudio, análise e 3D | Preservar funcionalidades selecionadas ao portar versões anteriores |
| Alterações locais em `backend/integration.py` e `integration_store.py` | Ingestão/persistência consolidadas | Adaptar ao banco canônico e à fila única; combinar lifespan com LLM |
| `backend/app/provision.py` e alterações de cadastro | Administração local de sensores | Catálogo, perfis, unidades e credencial de gateway |
| `backend/esp_bridge.py` e firmware de umidade local | Ensaio HTTP/serial | pyserial opcional; fila em RAM; identidade limitada entre sessões |
| Alterações de `database.py` e `motor_predicao.py` | Proteção do histórico e cálculo temporal | Conflitos com mudanças posteriores do fork; preservar zero e distinguir estimativas |
| Branch `48752ef`, pacote `monitoring_bot` | Bot oficial, autorização, cliente e worker | Contrato v1, transporte, comandos e exclusão de polling concorrente |
| Branch `48752ef`, iniciador e preparação local | Inicialização simplificada | Adaptar banco isolado e portas ao fluxo oficial; API deve iniciar sem Telegram |
| Alterações em `web/js/api.js` e chamadas dos clientes | URL central e operação na mesma origem | Preservar recursos novos do painel ao resolver conflitos |
| Frontends anteriores | Lógica de dados e recursos úteis | Telas redesenhadas; tecnologia escolhida na entrega visual |
| Gateway/nó existentes | Firmware oficial e continuidade | Coleta periódica ainda necessária no nó v1; fila atual limitada a 128 registros |
| Testes e guias de cada fonte | Evidências e critérios da V2 | Portar junto da funcionalidade; não assumir validação por relatório antigo |

Há 13 arquivos alterados dos dois lados; o exame anterior de aplicação direta detectou incompatibilidade em 9. A transferência será seletiva. Esta entrega não aplicou esses patches ao fork.

## Ambiente e verificações

Ambiente do notebook: Python **3.12.3**, Node **18.19.1**, npm **9.2.0**.

| Verificação | Resultado e limite |
| --- | --- |
| Bundles e reconstrução | As duas fontes recuperadas; hashes/permissões conferidos |
| Sintaxe Python | 68 arquivos versionados analisados com AST; nenhum erro sintático |
| Backend v1 | 53 testes aprovados: alertas, heartbeat, ingestão, notificações e consultas |
| Frontend herdado | `npm test` aprovado: 2 arquivos de teste reconhecidos pelo runner |
| Build do frontend herdado | TypeScript e Vite concluídos; Vite disponível 6.4.6 |
| Instalação Python limpa | Ambiente virtual criado; pip não encontrou distribuição para `annotated-doc==0.0.6`; instalação não concluída |
| Suíte completa Python | Não executada: ambientes disponíveis não contêm pytest nem httpx |
| Proteção Git e documentos | Exclusões de dados/credenciais verificadas; links locais e diff conferidos |

Os testes executados usaram cópias temporárias do código do fork e dependências já presentes na pasta antiga. O frontend temporário apontou para o `node_modules` antigo; o backend usou o Python da `.venv` antiga. Isso confirma uma base parcial funcional, **não** comprova instalação reproduzível a partir dos manifests.

O executor ASGI precisou de uma tarefa auxiliar de despertar do loop durante os testes, apenas no harness temporário. Nenhum teste ou código de aplicação foi alterado. O procedimento e os resultados estão em `baseline-checks.py` e `baseline-results.json` dentro do snapshot privado.

Comandos de referência após resolver o ambiente:

```bash
# Na raiz, com o ambiente Python completo e isolado:
python -m pytest

# Dentro de frontend/:
npm ci
npm test
npm run build
```

Pontos de execução herdados a consolidar: `app.main:app` a partir de `backend/` para o contrato v1 e `backend.server:app` a partir da raiz para a API fitoeletrônica. São aplicações distintas; não executar ambas na mesma porta presumindo que sejam equivalentes.

## Bloqueios e próximos passos

1. Verificar resolução DNS e acesso aos remotos. A base local permanece registrada enquanto isso.
2. Revisar os requisitos fixados contra os pacotes disponíveis; o erro do pip não identifica sozinho se a causa é acesso ao índice ou disponibilidade da versão. Não atualizar versões por tentativa.
3. Declarar as dependências reais antes da consolidação: `httpx` é importado por `backend/server.py` e `backend/llm_engine.py`, mas não aparece no lock examinado. pytest é necessário à suíte completa. Não foram instalados pacotes ad hoc nem alteradas versões nesta entrega.
4. Iniciar a entrega visual e o desenho do núcleo de dados; resolver os bloqueios de ambiente antes de aceitar a integração funcional.

O plano foi corrigido para incluir autorização antecipada, coleta periódica, painel do gateway, calibração versionada, CSV, comportamento sem internet, alertas atrasados, limites da fila e operação/backup. As etapas de implementação desses recursos continuam pendentes.
