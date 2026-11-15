## 📌 Descrição do Pull Request

**Título:** `feat(bot): processamento de audio ogg/opus puro python, integracao llm/fallback e protecao anti-409`  
**Branch:** `feat/bot-audio-stt-llm`  
**Milestone:** M4 (PR 3: feat/bot-audio-stt-llm)  
**Tipo de Alteração:**
- [x] Processamento de áudio Ogg/Opus (RFC 3533 & RFC 7845) 100% puro Python, dispensando binários externos (`ffmpeg`/`ffprobe`) no PATH do Windows
- [x] Validação pré-download de notas de voz no Telegram (duração <= 120s e tamanho <= 5 MB) protegendo largura de banda e prevenindo exaustão de rede no meio rural
- [x] Gerenciador de contexto temporário resiliente a locks de arquivos Win32 (`[WinError 32]`), com fechamento atômico de descritores antes do yield e limpeza determinística em `try/finally`
- [x] Integração fitoeletrônica cliente-servidor em `bot/telemetria.py` (`obter_diagnostico_llm`) conectando com `/api/llm/diagnostico` e fallback instantâneo em memória (<5ms)
- [x] Manipulador de voz `handle_voice` em `bot/phytosense_bot.py` com feedback imediato via ação `"typing"`, inspeção acústica, telemetria em tempo real e resposta estruturada com o teclado do produtor
- [x] Blindagem anti-conflito Telegram HTTP 409 Conflict nos testes automatizados através de isolamento de rede e mocks de polling
- [x] Ampliação da suíte de testes com +33 novos testes unitários e de integração em `bot/tests/test_audio.py`, elevando o projeto para 160 testes (100% aprovados)
- [x] Conformidade rigorosa com política anti-termos proibidos (`agrosponge`, `casca de arroz`, `saco biodegradável`) e governança de CI (`.github/workflows/` 100% intocado)

---

### 🎯 Motivação & Contexto (Desafio 02 UERGS: Água e Drenagem Rural)
Este Pull Request conclui o **Marco 4** da **Tekó Biotech** no **Hackathon das Engenharias UERGS 2026**, viabilizando a interação por notas de voz para produtores rurais com foco em acessibilidade e zero digitação:
1. **Inspeção de Contêiner Ogg/Opus sem ffmpeg:** Decodificação e inspeção binária com o módulo `struct` nativo do Python (RFC 3533 e RFC 7845), extraindo magic signature `b"OggS"`, cabeçalho `b"OpusHead"`, canais, taxa de amostragem de referência (48000 Hz), versão Opus, pré-skip e cálculo da duração exata a partir da posição de grânulo da última página Ogg.
2. **Guarda de Recursos & Conexões Rurais Instáveis:** O produtor rural em áreas remotas frequentemente opera sob redes 3G/4G limitadas. A validação prévia de metadados (`duration` <= 120s e `file_size` <= 5 MB) antes de chamar `bot.get_file` ou `bot.download_file` impede downloads desnecessários de áudios gigantes ou inválidos.
3. **Resiliência a Locks do Windows (WinError 32):** `gerenciador_audio_temporario` garante que handles abertos por `tempfile.NamedTemporaryFile` sejam liberados no Windows antes de ceder o controle, evitando falhas de permissão ao reler ou deletar arquivos temporários em blocos `finally`.
4. **Inteligência Fitoeletrônica Híbrida (LLM + Fallback):** Conecta o bot à inteligência agronômica do backend FastAPI (`POST /api/llm/diagnostico`). Caso o backend ou o Ollama estejam indisponíveis, ativa o motor especialista de fallback em memória em < 0.2ms, garantindo parecer técnico imediato sobre irrigação, bioimpedância e status da bomba.
5. **Zero Conflito Telegram 409 Polling:** Todos os testes de bot são isolados com `unittest.mock.MagicMock` e `patch`, impedindo emissão de `getUpdates` reais contra a API do Telegram e eliminando colisões de webhook/polling durante a execução do `pytest`.

---

## 🔬 Componentes Afetados
- [x] 🎙️ Processador de Áudio (`bot/audio_processor.py`)
  - `validar_metadados_audio`: validação de duração (1 a 120s) e tamanho (1 a 5 MB).
  - `inspecionar_container_ogg`: parsing RFC 3533 e RFC 7845 em Python puro com suporte a `OpusHead`, `OpusTags` e cálculo de duração por grânulos.
  - `gerenciador_audio_temporario`: context manager seguro contra `[WinError 32]` no Windows.
- [x] 🌾 Bot Telegram (`bot/phytosense_bot.py` e `bot/telemetria.py`)
  - `obter_diagnostico_llm`: cliente HTTP com clamping de segurança e fallback em memória.
  - `handle_voice`: pipeline completo de recebimento de áudio, validação pré-download, download temporário, inspeção acústica, coleta de telemetria e resposta textual.
- [x] 🧪 Testes Automatizados (`bot/tests/test_audio.py`)
  - 33 novos testes cobrindo gerador sintético Ogg/Opus, validação de bordas, buffers corrompidos, arquivos de outros codecs (MP3/WAV/Vorbis), ciclo de vida do temporário no Windows, clamping da telemetria, fluxos de sucesso e erro do bot e blindagem anti-409.
  - Suíte completa do projeto elevada de 127 para 160 testes (100% aprovados).
- [x] 📖 Governança e Repositório
  - `.github/workflows/` preservado 100% intacto (0 alterações).
  - Zero ocorrências de termos legados proibidos.

---

## 🌾 Checklist de Aceite Técnico & Fitoeletrônico (Tekó Biotech)
- [x] **Zero Dependência Externa**: Inspeção Ogg/Opus opera sem `ffmpeg` ou bibliotecas C no Windows.
- [x] **Segurança Win32**: Arquivos temporários não disparam `[WinError 32]` e são deletados no `finally`.
- [x] **Proteção de Rede**: Rejeição de áudios > 120s ou > 5 MB ocorre antes de qualquer download.
- [x] **Alta Disponibilidade**: Fallback fitoeletrônico instantâneo em memória garante resposta mesmo com backend offline.
- [x] **Política Anti-Termos Proibidos**: Validação estrita assegurando ausência de `agrosponge`, `casca de arroz` ou `saco biodegradável`.
- [x] **Blindagem Anti-409**: Nenhuma chamada de polling ativa nos testes pytest.
- [x] **Testes Automatizados**: 160 testes passando (`pytest`), sem nenhuma falha ou regressão.
- [x] **Governança de CI**: Nenhuma modificação em `.github/workflows/`.

---
> 🤖 **Code Review com IA:** Este repositório conta com revisão automatizada via **CodeRabbit AI** e **Qodo Merge**. Interaja nos comentários do PR com `/review`, `/improve` ou `/ask` para esclarecer dúvidas técnicas com a IA.
