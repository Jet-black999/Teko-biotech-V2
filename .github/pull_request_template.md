## 📌 Descrição do Pull Request

**Título:** `feat(llm): endpoint POST /api/llm/diagnostico com cliente Ollama leve, fallback fitoeletronico <50ms e filtro anti-termos proibidos`  
**Branch:** `feat/llm-local-biossensor`  
**Milestone:** M3 (PR 2: feat/llm-local-biossensor)  
**Tipo de Alteração:**
- [x] Nova funcionalidade (Endpoint REST `POST /api/llm/diagnostico` para WebApp e Telegram Bot)
- [x] Integração com LLM Local (Cliente HTTP assíncrono leve para Ollama / `qwen2.5:0.5b` com timeout de 1.0s, sem poluir `requirements.lock.txt`)
- [x] Motor especialista fitoeletrônico determinístico de fallback (<50ms SLA, benchmark medido <0.2ms)
- [x] Tolerância a falhas em 3 camadas garantindo zero retornos HTTP 500 sob indisponibilidade de rede/Ollama
- [x] Filtro léxico ativo e validação estrita contra termos legados proibidos (`agrosponge`, `casca de arroz`, `saco biodegradável`)
- [x] Ampliação da suíte de testes automatizados (+29 testes novos em `backend/tests/test_llm.py`, totalizando 124 testes aprovados)

---

### 🎯 Motivação & Contexto (Desafio 02 UERGS: Água e Drenagem Rural)
Este Pull Request implementa a infraestrutura de inteligência artificial agronômica local e diagnósticos fitoeletrônicos para a **Tekó Biotech** no **Hackathon das Engenharias UERGS 2026**:
1. **Inteligência Artificial Local e Soberania Tecnológica no Campo:** Conexão assíncrona com o Ollama local (`http://localhost:11434` / `qwen2.5:0.5b`) sem dependências pesadas externas e sem alteração do `requirements.lock.txt`.
2. **Motor Especialista Fitoeletrônico de Fallback (< 50ms SLA):** Caso o Ollama esteja offline, desligado ou leve mais de 1,0s para responder, o motor determinístico em memória assume imediatamente (tempo de resposta medido < 0.2ms, mais de 250x abaixo do SLA contratual), eliminando qualquer risco de erro HTTP 500.
3. **Conhecimento Agronômico e Eletrofisiológico Integrado:**
   - Modelos hidrofísicos Van Genuchten/Embrapa para 11 classes texturais normalizadas em 3 regimes (arenoso, franco, argiloso) com cálculo contínuo de Água Disponível ($AD\%$).
   - Bioimpedância de caule dupla frequência: 1 kHz apoplástico (fluxo xilema) vs 50 kHz simplástico (turgor celular intracelular e ITR = $Z_{1k} / Z_{50k}$), detectando "seca invisível" ($Z_{50k} \ge 4.5\text{ k}\Omega$) 18 a 36h antes do murchamento foliar.
   - Paradoxo da Enchente / Asfixia Radicular (ORP < -100 mV ou solo alagado): a depleção de oxigênio e ATP desativa as aquaporinas radiculares (PIP), gerando seca fisiológica. A bomba NUNCA deve ser ligada (`"NÃO LIGAR A BOMBA!"`), priorizando abertura de valetas de drenagem e laudo pericial PROAGRO.
4. **Política de Segurança Léxica Tekó Biotech:** Sanitização ativa com expressões regulares e verificação defensiva Unicode NFD sem marcas diacríticas, erradicando qualquer termo obsoleto (`agrosponge`, `casca de arroz`, `saco biodegradável`) e carimbando a resposta com `seguranca_termos_antigos: true`.

---

## 🔬 Componentes Afetados
- [x] ⚡ Backend FastAPI (`backend/`)
  - Criação do módulo `backend/llm_engine.py`: cliente Ollama leve, fallback determinístico, tabelas Van Genuchten e sanitizador léxico.
  - Atualização de `backend/server.py`: esquemas Pydantic `DiagnosticoLLMIn` e `DiagnosticoLLMOut`, inicialização não-bloqueante no `lifespan`, exposição do endpoint `POST /api/llm/diagnostico` com proteção em 3 camadas e catálogo de rotas em `GET /`.
- [x] 🧪 Testes Automatizados (`backend/tests/test_llm.py`)
  - 29 novos testes cobrindo hidratada, sede, hipóxia/paradoxo da enchente, benchmark de latência < 50ms, normalização dos 11 solos Van Genuchten, injeções adversariais de termos proibidos, mock de Ollama online e offline, e validações de esquema HTTP 422.
  - Suíte completa do projeto elevada de 95 para 124 testes (100% aprovados).
- [x] 📖 Governança e Repositório
  - `backend/requirements.lock.txt` preservado intacto (0 alterações).
  - `.github/workflows/` preservado intacto (nenhum arquivo criado ou alterado).

---

## 🌾 Checklist de Aceite Técnico & Fitoeletrônico (Tekó Biotech)
- [x] **Cliente HTTP Leve**: Utiliza `httpx` nativo já presente no ambiente sem adicionar novas dependências.
- [x] **SLA de Fallback < 50ms**: Benchmark medido de ~0.15ms a 0.20ms em execução determinística local.
- [x] **Zero Erros HTTP 500**: Tolerância a falhas em 3 camadas (timeout curto no Ollama, fallback determinístico, barreira de exceção na rota FastAPI).
- [x] **Política Anti-Termos Proibidos**: Validação estrita assegurando ausência de `agrosponge`, `casca de arroz` ou `saco biodegradável`.
- [x] **Contrato de API Cumprido**: `POST /api/llm/diagnostico` retorna exatamente os campos definidos no `PROJECT.md` e `SCOPE.md`.
- [x] **Testes Automatizados**: 124 testes passando (`pytest`), sem nenhuma regressão.
- [x] **Governança de CI**: Nenhuma modificação em `.github/workflows/`.

---
> 🤖 **Code Review com IA:** Este repositório conta com revisão automatizada via **CodeRabbit AI** e **Qodo Merge**. Interaja nos comentários do PR com `/review`, `/improve` ou `/ask` para esclarecer dúvidas técnicas com a IA.
