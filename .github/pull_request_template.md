## 📌 Descrição do Pull Request

**Título:** `feat: Integracao Total do Biossensor In-Planta, Identidade Visual Oficial & Resolucao de Qualidade de Codigo`  
**Branch:** `pr/integracao-total-biossensor-e-identidade-visual`  
**Tipo de Alteração:**
- [x] Correção de bugs / Refatoração de qualidade de código (100% dos 37 achados Qodo/SonarCloud resolvidos)
- [x] Migração de infraestrutura (`@app.on_event("startup")` -> `lifespan` assíncrono no FastAPI)
- [x] Nova funcionalidade (Integração total do biossensor fitoeletrônico, 11 solos Van Genuchten, 4 culturas Embrapa/FAO)
- [x] Acessibilidade e Identidade Visual (WCAG 2.2 AA no Modo Claro, alvos >= 48px, botões e semântica ARIA)

---

### 🎯 Motivação & Contexto (Desafio 02 UERGS: Água e Drenagem Rural)
Este Pull Request consolida a evolução completa do ecossistema **Tekó Biotech** para o **Hackathon das Engenharias UERGS 2026** (Desafio 02: Água e Drenagem Rural), focado na resiliência climática da agricultura familiar do Rio Grande do Sul:
1. **Resiliência a Extremos Climáticos:** Monitoramento eletrofisiológico in-planta em tempo real para combater tanto a estiagem severa (alerta de sede precoce via bioimpedância de caule a 1 kHz e 50 kHz antes do murchamento visual) quanto inundações e enchentes históricas (detecção de hipóxia e asfixia radicular via Potencial Redox ORP < -100 mV com bactérias exoeletrogênicas *Geobacter* na célula P-MFC).
2. **Base Científica Embrapa / FAO-56:** Incorporação das curvas de retenção de água de Van Genuchten para 11 classes texturais de solo e matriz fenológica completa para Milho, Tomate, Feijão e Alface, calculando lâmina de irrigação e economia de recursos hídricos e energéticos (4.200 L de água e R$ 38,00 de luz/diesel poupados por hectare/mês no estado hidratado).
3. **Qualidade de Código e Confiabilidade Máxima:** Resolução integral dos 37 apontamentos de análise estática e revisão de código (Qodo / SonarCloud) distribuídos entre backend, bot e frontend web, além da modernização do ciclo de vida da API FastAPI com `lifespan`, eliminando 100% dos `DeprecationWarning`.

---

## 🔬 Componentes Afetados
- [x] 📱 Frontend / Telegram Mini App PWA (`web/`)
  - Adequação de contraste no Modo Claro para conformidade WCAG 2.2 AA (`web/css/styles.css`).
  - Remoção de seletores CSS duplicados e especificação de transições.
  - Refatoração de funções de alta complexidade cognitiva, eliminação de ternários aninhados, uso de `Number.parseInt/isNaN/parseFloat`, `el.dataset` e remoção de imports não utilizados (`web/js/app.js`, `charts.js`, `content.js`).
  - Correção de semântica ARIA para elementos interativos (`web/index.html`).
- [x] 🤖 Bot do Telegram Tekó (`bot/`)
  - Refatoração modular de `send_welcome` em `bot/phytosense_bot.py` reduzindo a complexidade cognitiva de 20 para <= 15 (funções auxiliares `_obter_avatar_path` e `_enviar_foto_boas_vindas`).
  - Uso estrito de `logger.exception()` em blocos de exceção (python:S8572).
  - Remoção de prefixo f-string sem interpolação em `bot/configurar_teko.py` (python:S3457).
  - Suíte de 16 testes unitários em `bot/tests/test_bot.py` 100% aprovada.
- [x] ⚡ Backend FastAPI & Banco de Dados (`backend/`)
  - Migração de `@app.on_event("startup")` para `@asynccontextmanager async def lifespan(app: FastAPI)` em `backend/server.py`.
  - Extração de constantes de citação Embrapa para eliminar duplicações de literais em `backend/database.py` (python:S1192).
  - Correção de comparação de ponto flutuante via tolerância épsilon em `backend/motor_predicao.py` (python:S1244).
- [ ] 🔌 Firmware Embarcado ESP32 / Gateway (`firmware/`)
- [ ] 🧩 Extensão de Acessibilidade (`extension/`)
- [x] 📖 Documentação / CI / GitHub Workflows (`docs/`, `.github/`)
  - Preenchimento completo do template de Pull Request para auditoria técnica.
  - Garantia de governança estrita de CI: nenhum arquivo sob `.github/workflows/` foi criado ou modificado.

---

## 🌾 Checklist de Aceite Técnico & Fitoeletrônico (Tekó Biotech)
- [x] **Acessibilidade Rural WCAG 2.2 AA**: Alvos de toque >= 48px, alto contraste sob luz solar forte (#252A26 Carbon em fundos claros, contraste >= 4.5:1), suporte à síntese de voz e semântica ARIA estrita.
- [x] **Rigor Eletrofisiológico**:
  - Bioimpedância dual-frequency validada (50 kHz para turgor celular simplástico, 1 kHz para fluxo apoplástico/xilema).
  - Detecção precoce de asfixia radicular na enchente via ORP < -100 mV (P-MFC Geobacter).
- [x] **Consistência de Manejo e Custos**:
  - Limites críticos calibrados segundo literatura Embrapa (Embrapa-RR 1997, Embrapa Hortaliças 2008, Embrapa Arroz e Feijão / FAO-56).
  - Indicadores de economia de diesel e litros de água coerentes em todos os estados da planta (4.200 L de água e R$ 38,00/mês economizados no estado hidratado).
- [x] **Segurança Absoluta**: Nenhum token (`TELEGRAM_TOKEN`), credencial ou segredo foi exposto em commits.
- [x] **Testes Automatizados**: Suíte `pytest` com 95 testes (100% aprovados) com **0 warnings de depreciação** e validação sintática do JS (`node --check`) sem erros.
- [x] **Governança de Repositório**: Preservação integral do diretório `.github/workflows/` (sem adição ou modificação de arquivos de pipeline).

---
> 🤖 **Code Review com IA:** Este repositório conta com revisão automatizada via **CodeRabbit AI** e **Qodo Merge**. Interaja nos comentários do PR com `/review`, `/improve` ou `/ask` para esclarecer dúvidas técnicas com a IA.
