## 📌 Descrição do Pull Request

**Título:** `feat: Simulador 3D Web Three.js com Biossensor In-Planta, Acessibilidade WCAG 2.2 AA e Deploy gh-pages (PR 1)`  
**Branch:** `feat/simulador-3d-biossensor`  
**Base:** `pr/integracao-total-biossensor-e-identidade-visual`  
**Tipo de Alteração:**
- [x] Nova funcionalidade (Simulador 3D WebGL interativo Three.js na Aba 1)
- [x] Otimização e Ciclo de Vida WebGL (pausa em `document.hidden` e troca de abas, fallback automático 2D)
- [x] Acessibilidade Rural (WCAG 2.2 AA, alvos >= 48px, controles por toque/mouse/setas do teclado, ARIA dinâmico e live region `#sr-anuncios`)
- [x] Modo Claro / Escuro (adaptação cromática dinâmica e iluminação difusa/direcional Three.js para visibilidade solar no campo)
- [x] PWA Offline & Segurança (Three.js ESM vendorado localmente em `web/js/vendor/three.module.min.js`, conformidade CSP `'self'`, cache `teko-v9`)
- [x] Sincronização de Deploy (`web/` sincronizado diretamente na raiz da branch `gh-pages` para o Telegram Mini App)

---

### 🎯 Motivação & Contexto (Desafio 02 UERGS: Água e Drenagem Rural)
Este Pull Request implementa o **Simulador 3D WebGL com Three.js** integrado na Aba 1 do Mini App Tekó Biotech, proporcionando ao produtor rural e à banca avaliadora uma experiência imersiva e fitoeletrônica do funcionamento do biossensor:
1. **Clipe de Caule com Bio-hidrogel KCl (10 mM) e Eletrodos de Grafite:** Representação geométrica tridimensional do clipe plástico laranja (#ff6b00) abraçando o caule, com almofada interna de hidrogel condutivo e eletrodos de grafite biocompatível conectados via cabo espiral ao módulo ESP32-C3 IP68.
2. **Dinâmica Bioelétrica em Dupla Frequência (Dual-Frequency):**
   - **Fluxo Apoplástico a 1 kHz:** Sistema de partículas no xilema com velocidade proporcional à disponibilidade hídrica (viva e azul no estado hidratado; lenta e âmbar na seca; estagnada e avermelhada na hipóxia).
   - **Pulso Simplástico a 50 kHz:** Pulsação senoidal volumétrica de turgor celular na seção transversal do caule ($R_s$), evidenciando a contração do caule sob estresse hídrico.
3. **Rizosfera & Haste Basal P-MFC (ORP Geobacter):** Visualização do solo agrícola, sistema radicular ramificado, haste de titânio coletora e halo bioelétrico pulsante na ponta de feltro de carbono colonizada por *Geobacter sulfurreducens* (+310 mV hidratada; +420 mV sede; -140 mV hipóxia).
4. **Lâmina de Água de Enchente em Hipóxia:** Emersão dinâmica de lâmina de água translúcida sobre o solo no estado de hipóxia, alertando para inundação e asfixia radicular com recomendação imediata de desligar a bomba de irrigação.
5. **Autonomia e Resiliência em Campo (Offline-First & Bateria):** Three.js vendorado localmente como ES Module (`web/js/vendor/three.module.min.js`), estritamente compatível com o CSP `script-src 'self'` do Netlify e cacheado no Service Worker `teko-v9`. Loop de animação pausado imediatamente quando a aba perde foco ou fica oculta (`document.hidden`), economizando bateria de smartphones no campo.

---

## 🔬 Componentes Afetados
- [x] 📱 Frontend / Telegram Mini App PWA (`web/`)
  - `web/js/vendor/three.module.min.js`: Three.js r160 ES Module minificado vendorado localmente (670 KB, offline-first e CSP `'self'`).
  - `web/js/simulador_3d.js`: Módulo Three.js com cena, iluminação dinâmica, malhas fitoeletrônicas, partículas de seiva, halo bioelétrico, ciclo de vida WebGL, controles de rotação e fallback.
  - `web/index.html`: Botões de alternância 2D/3D com alvos >= 48px, elemento `<canvas id="canvas-planta-3d">` com `role="img"`, `tabindex="0"`, `aria-label` dinâmico e suporte a `#sr-anuncios`.
  - `web/css/styles.css`: Estilização dos seletores 2D/3D, canvas 3D, focus-visible acessível e regras de modo claro `[data-theme="light"]`.
  - `web/js/app.js`: Integração com o controlador 3D, pausa/retomada na troca de abas, sincronização de estado com o 2D e hook de tema.
  - `web/sw.js`: Atualização do Service Worker para cache `teko-v9` incluindo o Three.js e o simulador 3D.
- [x] 🌐 Deploy / Sincronização GitHub Pages (`gh-pages`)
  - Conteúdo atualizado da pasta `web/` sincronizado diretamente na raiz da branch `gh-pages` e publicado em `origin/gh-pages`.
- [x] 📖 Documentação / CI / GitHub Workflows (`docs/`, `.github/`)
  - Preenchimento do `.github/pull_request_template.md` com evidências técnicas.
  - Governança estrita: nenhum arquivo em `.github/workflows/` foi criado ou modificado.

---

## 🌾 Checklist de Aceite Técnico & Fitoeletrônico (Tekó Biotech)
- [x] **Acessibilidade Rural WCAG 2.2 AA**:
  - Alvos de toque com tamanho mínimo de 48x48px (`--touch-minimo`).
  - Navegação por teclado: setas direcionais rotacionam o modelo 3D, `R` ou `Home` redefinem a câmera.
  - Anúncios dinâmicos para tecnologias assistivas via `#sr-anuncios` (`aria-live="polite"`).
  - Respeito à preferência de redução de movimento (`prefers-reduced-motion`).
- [x] **Adaptação Dinâmica ao Tema**: Alternância sem reload entre modo escuro oficial Tekó e modo claro rural, com recalibração de luzes e solo no Three.js.
- [x] **Tratamento de Exceções Gráficas**: Detecção antecipada via `isWebGLAvailable()`, fallback gracioso para 2D e recuperação automática em caso de `webglcontextlost`.
- [x] **Gerenciamento Energético**: Loop `requestAnimationFrame` cancelado quando `document.hidden === true` ou quando outra aba (2, 3 ou 4) estiver em exibição.
- [x] **Suíte de Testes Automatizados**: 95 testes do `pytest` 100% aprovados, sem falhas e sem warnings.
- [x] **Validação Sintática**: Todos os módulos JavaScript aprovados via `node --check`.
- [x] **Governança de CI**: Diretório `.github/workflows/` intocado.

---
> 🤖 **Code Review com IA:** Este repositório conta com revisão automatizada via **CodeRabbit AI** e **Qodo Merge**. Interaja nos comentários do PR com `/review`, `/improve` ou `/ask` para esclarecer dúvidas técnicas com a IA.
