/* Prévia isolada: fixtures determinísticas, sem API, credenciais ou gravação de configuração. */
(() => {
  'use strict';
  const $ = selector => document.querySelector(selector);
  const icons = {
    home: '<path d="m3 10 9-7 9 7v10H3Z"/><path d="M9 20v-7h6v7"/>',
    points: '<rect x="3" y="3" width="7" height="7" rx="2"/><rect x="14" y="3" width="7" height="7" rx="2"/><rect x="3" y="14" width="7" height="7" rx="2"/><rect x="14" y="14" width="7" height="7" rx="2"/>',
    alert: '<path d="m12 3 10 18H2Z"/><path d="M12 9v5m0 3v1"/>',
    settings: '<circle cx="12" cy="12" r="4"/><path d="M12 2v4m0 12v4M2 12h4m12 0h4M5 5l3 3m8 8 3 3M5 19l3-3M16 8l3-3"/>',
    leaf: '<path d="M5 19C-1 7 10 2 21 3c0 12-5 20-16 16Zm0 0L16 8"/>',
    arrow: '<path d="M4 12h16m-6-6 6 6-6 6"/>',
    offline: '<path d="m3 3 18 18M8 16a7 7 0 0 1 8 0M5 12a12 12 0 0 1 4-2m5 0a12 12 0 0 1 5 2M2 8a18 18 0 0 1 4-2m5-1a18 18 0 0 1 11 3"/><circle cx="12" cy="20" r="1"/>',
  };
  const icon = name => `<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${icons[name] || icons.leaf}</svg>`;
  const badge = (text, kind = '') => `<span class="status ${kind}">${text}</span>`;
  const button = (text, href, primary = false) => `<a class="button${primary ? ' primary' : ''}" href="${href}">${text} ${icon('arrow')}</a>`;
  const heading = (eyebrow, title, subtitle) => `<div class="page-heading"><div><span class="eyebrow">${eyebrow}</span><h1>${title}</h1><p>${subtitle}</p></div><div class="heading-meta">SEGUNDA-FEIRA<strong>16 de novembro, 2026</strong>Referência fictícia · 10:42</div></div>`;
  const points = [
    { id: 'estufa', name: 'Estufa 01', location: 'Hortaliças · setor norte', value: 34.2, time: '10:40', age: 'há 2 min', status: 'Atenção · regra de teste', kind: 'warn', connected: true },
    { id: 'pomar', name: 'Pomar', location: 'Frutíferas · setor leste', value: 26.8, time: '10:38', age: 'há 4 min', status: 'Sem ocorrência ativa', kind: '', connected: true },
    { id: 'horta', name: 'Horta aberta', location: 'Canteiros · setor sul', value: 22.1, time: '04:40', age: 'há 6 h e 2 min', status: 'Sem comunicação', kind: 'neutral', connected: false },
  ];
  const state = { scenario: 'routine', direction: 'campo', channel: 'temperature', period: '6', filter: 'all', alertFilter: 'active' };
  const query = new URLSearchParams(location.search);
  for (const key of ['scenario', 'direction']) {
    if ([...$(`#${key}`).options].some(option => option.value === query.get(key))) state[key] = query.get(key);
    $(`#${key}`).value = state[key];
  }
  document.body.dataset.direction = state.direction;
  const noData = () => ['empty', 'api-empty', 'loading'].includes(state.scenario);
  const noLatest = () => ['pending', 'replaced', 'error'].includes(state.scenario);
  const hasAlert = () => !noData() && !['pending', 'replaced', 'uncalibrated', 'unknown-time', 'error'].includes(state.scenario);
  function pointData(point) {
    const p = { ...point };
    if (state.scenario === 'api-cache') Object.assign(p, { time: '09:40', age: 'há 1 h e 2 min', status: 'Última consulta guardada', kind: 'neutral' });
    if (state.scenario === 'sensor-offline') Object.assign(p, { time: '08:40', age: 'há 2 h e 2 min', status: 'Sem comunicação', kind: 'neutral', connected: false });
    if (state.scenario === 'stale') Object.assign(p, { time: '08:40', age: 'há 2 h e 2 min', status: 'Leitura antiga', kind: 'warn', connected: true });
    if (state.scenario === 'unknown-time') Object.assign(p, { time: null, age: 'idade desconhecida', status: 'Horário desconhecido', kind: 'warn' });
    if (state.scenario === 'uncalibrated') Object.assign(p, { value: 1840, status: 'Sem calibração', kind: 'warn' });
    if (noLatest()) Object.assign(p, { value: null, status: state.scenario === 'error' ? 'Erro de aquisição' : 'Primeira leitura pendente', kind: 'warn', time: null, age: 'sem leitura válida', connected: true });
    return p;
  }
  function readingValue(p) {
    if (p.value === null) return { text: state.scenario === 'error' ? 'Leitura indisponível' : 'Aguardando leitura', unit: '', label: 'Nenhuma condição avaliada' };
    if (state.scenario === 'uncalibrated') return { text: '1.840', unit: 'contagens ADC', label: 'Sinal bruto · sem conversão física' };
    if (state.channel === 'contact') return { text: 'Não detectada', unit: '', label: 'Presença de água · resultado booleano: falso' };
    if (state.channel === 'state') return { text: 'Estável', unit: '', label: 'Estado do sinal · categoria simulada' };
    return { text: p.value.toLocaleString('pt-BR', { minimumFractionDigits: 1 }), unit: '°C', label: 'Temperatura do ar' };
  }
  const acquired = p => p.time ? `Adquirido às ${p.time} · ${p.age}` : p.value === null ? 'Aquisição: nenhuma leitura válida' : 'Aquisição: horário e idade desconhecidos';
  function scenarioNotice() {
    const notices = {
      'api-cache': ['API indisponível · exibindo a última consulta fictícia', 'Consulta guardada às 09:42. Não é possível confirmar a condição atual nem a situação dos alertas. Nenhuma reconexão real está sendo testada.'],
      'api-empty': ['API indisponível · nenhuma consulta guardada', 'Não há informações locais para mostrar. A condição dos pontos é desconhecida.'],
      'sensor-offline': ['Sensor sem comunicação', 'A API do cenário está acessível, mas os sensores não se comunicam desde 08:40. As últimas leituras não descrevem a condição atual.'],
      stale: ['Leitura antiga · comunicação disponível', 'O sensor se comunicou às 10:41, mas não há uma nova leitura válida desde 08:40. Comunicação não confirma a condição medida.'],
      error: ['Não foi possível obter uma leitura válida', 'O sensor respondeu às 10:40 com erro de aquisição. O erro não é um valor zero nem uma condição normal.'],
      uncalibrated: ['Calibração pendente', 'Somente o sinal bruto está disponível. Cadastre método, parâmetros e versão pelo notebook antes de apresentar uma unidade física.'],
      replaced: ['Novo sensor · histórico anterior preservado', 'O sensor S-02 substituiu o S-01 às 10:30. A primeira leitura do novo sensor está pendente. As amostras anteriores continuam identificadas como S-01.'],
      'unknown-time': ['Horário de aquisição desconhecido', 'Recebido às 10:41. O horário de recebimento não indica quando a leitura foi adquirida; ela não entra na curva temporal.'],
      pending: ['Aguardando a primeira leitura', 'O ponto foi cadastrado no notebook. A comunicação foi detectada às 10:41, mas nenhuma leitura foi recebida.'],
    };
    const entry = notices[state.scenario];
    return entry ? `<div class="notice"><strong>${entry[0]}</strong><p>${entry[1]}</p></div>` : '';
  }
  function emptyState(title, description, action = '') {
    return `<section class="empty"><div class="point-icon">${icon(state.scenario.startsWith('api') ? 'offline' : 'leaf')}</div><h2>${title}</h2><p>${description}</p>${action}</section>`;
  }
  function unavailable() {
    if (state.scenario === 'empty') return emptyState('Seu primeiro ponto começa aqui.', 'Esta instalação fictícia ainda não tem pontos cadastrados. A preparação é feita no notebook; depois, as leituras aparecem aqui.', button('Ver primeira conexão', '#instalacao', true));
    if (state.scenario === 'api-empty') return emptyState('Não foi possível consultar os pontos.', 'Confira se o notebook está ligado e conectado à mesma rede. Nenhuma leitura ou situação de alerta está disponível.', '<button class="button primary" id="restore">Simular reconexão</button>');
    if (state.scenario === 'loading') return `<section class="panel" aria-busy="true"><h2>Consultando pontos e leituras…</h2><p class="muted">Estado de carregamento para revisão. Ainda não há resultado disponível.</p><div class="loading-bar wide"></div><div class="loading-bar"></div><button class="button" id="restore">Simular consulta concluída</button></section>`;
    return '';
  }
  function pointCard(original) {
    const p = pointData(original);
    const value = p.value === null ? 'Aguardando leitura' : p.value.toLocaleString('pt-BR', { minimumFractionDigits: state.scenario === 'uncalibrated' ? 0 : 1 });
    return `<article class="point-card"><div class="card-top"><span class="point-icon">${icon('leaf')}</span>${badge(p.status, p.kind)}</div><h3>${p.name}</h3><p class="location">${p.location}</p><div class="value${p.value === null ? ' no-value' : ''}">${state.scenario === 'error' ? 'Leitura indisponível' : value}${p.value === null ? '' : `<span>${state.scenario === 'uncalibrated' ? 'ADC' : '°C'}</span>`}</div><p class="reading-label">${state.scenario === 'uncalibrated' ? 'Sinal bruto · sem unidade física' : 'Temperatura do ar'}</p><p class="reading-time">${acquired(p)}</p><span class="source">ORIGEM: SIMULAÇÃO · SEM SENSOR REAL</span><svg class="spark" viewBox="0 0 240 40" preserveAspectRatio="none" aria-hidden="true"><path d="M0 35H240" stroke="currentColor" opacity=".15"/>${p.value !== null && p.time && p.connected ? '<path d="m0 29 20-3 20 2 20-10 20 4 20-5 20 2 20-10 20 5 20-8 20 2 20-7 20 2" fill="none" stroke="currentColor" stroke-width="1.5"/>' : ''}</svg><a class="card-link" href="#ponto/${p.id}">Ver ponto <span class="sr-only">${p.name}</span><span aria-hidden="true">↗</span></a></article>`;
  }
  function home() {
    const header = heading('SEU CULTIVO, MAIS PERTO', 'Um olhar para o que importa.', 'Acompanhe os pontos, entenda as mudanças e saiba onde olhar primeiro.');
    if (noData()) return header + scenarioNotice() + unavailable();
    const alert = hasAlert();
    const isCurrent = ['routine', 'no-history'].includes(state.scenario);
    const valid = !noLatest() && state.scenario !== 'unknown-time';
    return header + scenarioNotice() + `<section class="hero"><div class="hero-copy"><span class="eyebrow">${isCurrent ? 'SEU RESUMO DE HOJE' : 'ACOMPANHE COM CONTEXTO'}</span><h2>${isCurrent ? 'A Estufa 01 pede<br>um pouco de atenção.' : 'Antes de avaliar,<br>confira a qualidade do dado.'}</h2><p>${isCurrent ? 'A temperatura passou do limite da regra experimental.<br>Veja a leitura e o contexto antes de agir.' : 'Uma informação ausente ou antiga não confirma<br>a condição do cultivo neste momento.'}</p>${button(isCurrent ? 'Entender o alerta' : 'Conferir o ponto', isCurrent ? '#alerta/estufa' : '#ponto/estufa')}</div><svg class="hero-art" viewBox="0 0 200 170" fill="none" aria-hidden="true"><ellipse cx="100" cy="148" rx="85" ry="14" stroke="currentColor" opacity=".25"/><path d="M100 147V60M100 98C66 102 48 80 49 50c35-2 56 13 51 48ZM101 116c-4-40 19-61 55-60 0 36-21 61-55 60Z" stroke="currentColor" stroke-width="1.5"/><path d="m100 98-35-34m38 48 36-37M26 121h28l9-13 12 23 14-21 10 11h74" stroke="currentColor" stroke-width="1.5"/><circle cx="100" cy="40" r="24" stroke="currentColor" opacity=".25"/><circle cx="100" cy="40" r="4" fill="currentColor"/></svg></section><div class="stats"><div class="stat"><span class="stat-value">03</span><div><strong>Pontos cadastrados</strong><small>Nesta área de exemplo</small></div></div><div class="stat"><span class="stat-value">${isCurrent ? '02' : '—'}</span><div><strong>${isCurrent ? 'Com dados recentes' : 'Atualidade não confirmada'}</strong><small>${isCurrent ? '1 sem comunicação' : 'Confira o estado de cada ponto'}</small></div></div><div class="stat"><span class="stat-value">${alert ? '01' : '—'}</span><div><strong>${alert ? (isCurrent ? 'Ocorrência ativa' : 'Ocorrência registrada') : 'Condição não avaliada'}</strong><small>${alert ? 'Regra experimental' : 'Sem leitura avaliável'}</small></div></div></div><section><div class="section-head"><h2>Seus pontos</h2><a class="text-link" href="#pontos">Ver todos <span aria-hidden="true">↗</span></a></div><div class="point-grid">${points.map(pointCard).join('')}</div></section><div class="below-grid"><section class="panel"><h2>O que aconteceu</h2><div class="activity"><span class="activity-dot"></span><div><time>16 NOV · ${alert ? (state.scenario === 'api-cache' ? '09:40' : '08:40') : '10:41'}</time><p>${alert ? 'Temperatura acima do limite de teste na Estufa 01.' : 'Condição atual ainda não avaliada.'}</p>${alert ? '<a class="text-link" href="#alerta/estufa">Consultar ocorrência ↗</a>' : '<a class="text-link" href="#instalacao">Conferir preparação ↗</a>'}</div></div></section><section class="panel"><h2>Conexões do exemplo</h2><div class="connection-row"><span>Painel e API</span>${badge(state.scenario === 'api-cache' ? 'Indisponível' : 'Acessível · simulado', state.scenario === 'api-cache' ? 'warn' : '')}</div><div class="connection-row"><span>Telegram</span>${badge('Não vinculado', 'neutral')}</div><small>${valid ? 'Nenhuma mensagem será enviada nesta prévia.' : 'Comunicação disponível não garante uma leitura válida.'}</small></section></div>`;
  }
  function pointsPage() {
    const header = heading('MONITORAMENTO', 'Cada ponto, seu contexto.', 'Localização, última aquisição e comunicação em uma única consulta.');
    if (noData()) return header + scenarioNotice() + unavailable();
    const filtered = points.filter(p => state.filter === 'all' || (state.filter === 'offline' ? !pointData(p).connected : pointData(p).connected));
    return header + scenarioNotice() + `<div class="filters"><label>Mostrar pontos<select id="point-filter"><option value="all">Todos os pontos</option><option value="connected">Com comunicação</option><option value="offline">Sem comunicação</option></select></label><span class="muted">${filtered.length} de 3 pontos</span></div><div class="point-grid">${filtered.length ? filtered.map(pointCard).join('') : '<p>Nenhum ponto neste filtro.</p>'}</div>`;
  }
  function historyRows(p) {
    if (['no-history', 'pending', 'unknown-time', 'uncalibrated'].includes(state.scenario)) return [];
    const endMinutes = p.time ? Number(p.time.slice(0, 2)) * 60 + Number(p.time.slice(3)) : 620;
    const rows = Array.from({ length: 13 }, (_, i) => {
      const minutes = endMinutes - (12 - i) * 30;
      const time = `${String(Math.floor(minutes / 60)).padStart(2, '0')}:${String(minutes % 60).padStart(2, '0')}`;
      const values = [27.1, 27.5, 27.3, 28.2, 28.8, 29.4, 30.2, 31.4, 32.5, 33.1, 33.6, 34, 34.2];
      return { time, value: state.channel === 'temperature' ? Number((values[i] + (p.id === 'pomar' ? -7.4 : p.id === 'horta' ? -12.1 : 0)).toFixed(1)) : state.channel === 'contact' ? false : (i < 8 ? 'Oscilando' : 'Estável'), sensor: state.scenario === 'replaced' ? 'S-01' : `S-${p.id}`, minutes };
    });
    // Horta's earliest samples fall on the previous date; fixtures use the same explicit reference date below.
    return rows.filter(row => row.minutes >= 0 && row.minutes >= endMinutes - Number(state.period) * 60 && !(state.scenario === 'replaced' && row.minutes >= 630));
  }
  function history(p) {
    const rows = historyRows(p);
    const controls = `<div class="filters"><label>Parâmetro<select id="channel" ${state.scenario === 'uncalibrated' ? 'disabled' : ''}><option value="temperature">Temperatura do ar</option><option value="contact">Presença de água</option><option value="state">Estado do sinal</option></select></label><label>Período<select id="period"><option value="1">Última hora</option><option value="6">Últimas 6 horas</option></select></label><button class="button" id="export" ${rows.length ? '' : 'disabled'}>Exportar CSV fictício ↓</button></div>`;
    let graph = '';
    if (!rows.length) graph = `<div class="empty"><h3>${state.scenario === 'unknown-time' ? 'Sem aquisição datada para este gráfico' : 'Nenhuma leitura neste período'}</h3><p>${state.scenario === 'uncalibrated' ? 'Sinal bruto disponível no cartão. O histórico físico depende de uma calibração registrada.' : 'Nenhuma curva é desenhada sem amostras válidas e com horário conhecido.'}</p></div>`;
    else if (state.channel !== 'temperature') graph = `<p class="chart-caption">Eventos discretos · ${state.channel === 'contact' ? '“Não detectada” é um resultado válido, equivalente a falso.' : 'Categorias do sinal, sem escala numérica.'}</p>${rows.slice(-3).map(row => `<div class="event-state"><time>${row.time}</time><strong>${row.value === false ? 'Água não detectada' : row.value}</strong><span class="source">SIMULAÇÃO</span></div>`).join('')}<p class="chart-caption">Exibindo os últimos ${Math.min(3, rows.length)} eventos de ${rows.length}. A tabela e o CSV contêm todo o período.</p>`;
    else {
      const lo = Math.floor(Math.min(...rows.map(r => r.value), 26) - 2), hi = Math.ceil(Math.max(...rows.map(r => r.value), 34) + 2);
      const y = v => 175 - (v - lo) / (hi - lo) * 145;
      const coords = rows.map((r, i) => `${42 + i * 538 / Math.max(rows.length - 1, 1)},${y(r.value)}`).join(' ');
      graph = `<svg class="chart" viewBox="0 0 620 225" role="img" aria-labelledby="chart-title chart-description"><title id="chart-title">Temperatura do ar · ${p.name}</title><desc id="chart-description">${rows.length} amostras fictícias entre ${rows[0].time} e ${rows.at(-1).time}, de ${rows[0].value} a ${rows.at(-1).value} graus Celsius. Valores completos na tabela abaixo.</desc>${[lo, (lo + hi) / 2, hi].map(v => `<path class="gridline" d="M42 ${y(v)}H580"/><text x="5" y="${y(v) + 4}">${v}°</text>`).join('')}${p.id === 'estufa' ? `<path class="limit" d="M42 ${y(32)}H580"/><text x="350" y="${y(32) - 8}">32 °C · limite experimental</text>` : ''}<polyline class="trace" points="${coords}"/>${rows.map((r, i) => `<circle cx="${42 + i * 538 / Math.max(rows.length - 1, 1)}" cy="${y(r.value)}" r="3" fill="var(--green)"/>`).join('')}<text x="42" y="207">${rows[0].time}</text><text x="540" y="207">${rows.at(-1).time}</text></svg><p class="chart-caption">${rows.length} amostras fictícias · sem agregação · ${rows[0].time}–${rows.at(-1).time}. ${p.id === 'estufa' ? 'O limite é experimental; não representa uma recomendação agronômica.' : 'Nenhuma regra de avaliação aplicada neste ponto.'}</p>`;
    }
    return `<section class="panel"><h2>Uma leitura ao longo do tempo</h2>${controls}${graph}${rows.length ? `<details><summary>Ver leituras em tabela · alternativa ao gráfico</summary><div class="table-wrap"><table><caption class="sr-only">Amostras fictícias de ${p.name} · 16 de novembro de 2026 · UTC−3</caption><thead><tr><th scope="col">Aquisição</th><th scope="col">Resultado</th><th scope="col">Sensor</th><th scope="col">Origem</th></tr></thead><tbody>${rows.map(r => `<tr><td>${r.time}</td><td>${typeof r.value === 'number' ? r.value.toLocaleString('pt-BR') + ' °C' : r.value === false ? 'Não detectada (falso)' : r.value}</td><td>${r.sensor}</td><td>Simulação</td></tr>`).join('')}</tbody></table></div></details>` : ''}</section>`;
  }
  function pointPage(id) {
    const original = points.find(p => p.id === id);
    if (!original) return notFound();
    const p = pointData(original), v = readingValue(p);
    const header = `<a class="back" href="#pontos">← Todos os pontos</a>` + heading('DETALHE DO PONTO', p.name, p.location + ' · dados inteiramente fictícios');
    if (noData()) return header + scenarioNotice() + unavailable();
    const evaluation = p.id === 'estufa' && hasAlert();
    const uncertainty = ['api-cache', 'sensor-offline', 'stale', 'unknown-time'].includes(state.scenario) || !p.connected;
    return header + scenarioNotice() + `<div class="detail-grid"><div><section class="panel metric-panel"><div>${badge(p.status, p.kind)}<p class="reading-label" style="margin-top:18px">${v.label}</p><div class="value${!v.unit ? ' no-value' : ''}">${v.text}<span>${v.unit}</span></div><p class="reading-time">${acquired(p)}<br>${state.scenario === 'unknown-time' ? 'Recebido às 10:41 · idade da aquisição desconhecida' : '16 nov 2026 · UTC−3'}</p><span class="source">ORIGEM: SIMULAÇÃO · ${p.value === null ? 'SEM RESULTADO VÁLIDO' : state.scenario === 'uncalibrated' ? 'BRUTO, SEM CALIBRAÇÃO' : 'AMOSTRA FICTÍCIA'}</span></div><div class="metric-summary"><strong>${uncertainty ? 'Condição atual desconhecida' : evaluation ? 'Regra experimental ultrapassada' : 'Confira o contexto'}</strong><p>${uncertainty ? 'Esta leitura não confirma o estado atual do ponto.' : evaluation ? 'Há uma ocorrência de temperatura neste ponto. A regra é apenas demonstrativa.' : 'Não há recomendação de manejo. A disponibilidade da leitura depende do cenário selecionado.'}</p>${evaluation ? '<a class="text-link" href="#alerta/estufa">Entender ocorrência ↗</a>' : ''}</div></section>${history(p)}</div><aside class="panel aside-panel"><h3>Sobre este ponto</h3><dl><div><dt>Comunicação</dt><dd>${state.scenario === 'api-cache' ? 'Não confirmada · API offline' : p.connected ? 'Disponível · simulado' : 'Sem comunicação'}</dd></div><div><dt>Sensor</dt><dd>${state.scenario === 'replaced' ? 'S-02 · novo sensor' : `S-${p.id}`}<br>Exemplo sem hardware</dd></div><div><dt>Calibração</dt><dd>${['uncalibrated', 'replaced'].includes(state.scenario) ? 'Pendente no notebook' : 'Exemplo de fábrica · v1'}</dd></div><div><dt>Origem dos dados</dt><dd>Simulação explícita<br>Nenhuma medição física</dd></div></dl>${button('Ver preparação', '#instalacao')}<details><summary>Diagnóstico técnico</summary><p>Identidade e versão são ilustrativas. Nenhuma sequência, credencial ou dispositivo real é consultado.</p></details><p class="source">Cadastro, calibração e substituição são feitos no notebook. Este painel é de consulta.</p></aside></div>`;
  }
  function alertsPage() {
    const header = heading('OCORRÊNCIAS', 'Atenção com contexto.', 'Condição medida, comunicação e entrega de mensagens são informações diferentes.');
    if (noData()) return header + scenarioNotice() + unavailable();
    return header + scenarioNotice() + `<div class="filters"><label>Ocorrências<select id="alert-filter"><option value="active">Ativas</option><option value="resolved">Encerradas</option></select></label></div>` + (state.alertFilter === 'resolved' ? `<section class="panel"><div class="alert-row"><div>${badge('Encerrada · exemplo')}<h3 style="margin-top:12px">Temperatura · Estufa 01</h3><p>15 nov · 14:10–15:00 · recuperação registrada</p></div>${button('Ver ocorrência', '#alerta/encerrada')}</div></section>` : hasAlert() ? `<section class="panel"><div class="alert-row"><div>${badge(state.scenario === 'api-cache' ? 'Ativa na última consulta' : 'Ativa · experimental', 'warn')}<h3 style="margin-top:12px">Temperatura acima do limite de teste</h3><p>Estufa 01 · desde 08:40 · origem: simulação</p></div>${button('Entender alerta', '#alerta/estufa')}</div></section>` : emptyState('Nenhuma ocorrência avaliável.', 'Neste cenário não há leitura válida para avaliar a regra experimental. Isso não confirma uma condição normal.', button('Conferir o ponto', '#ponto/estufa')));
  }
  function alertPage(id) {
    if (!['estufa', 'encerrada'].includes(id)) return notFound();
    const resolved = id === 'encerrada';
    const header = `<a class="back" href="#alertas">← Todas as ocorrências</a>` + heading('ESTUFA 01 / TEMPERATURA DO AR', resolved ? 'A condição se recuperou.' : 'Uma mudança para acompanhar.', 'Ocorrência fictícia · regra experimental · sem recomendação automática de manejo');
    if (noData()) return header + scenarioNotice() + unavailable();
    if (!resolved && !hasAlert()) return header + scenarioNotice() + emptyState('Ocorrência indisponível neste cenário.', 'Não há condição avaliada para abrir um alerta. Consulte a preparação ou a qualidade da leitura.', button('Conferir o ponto', '#ponto/estufa'));
    return header + scenarioNotice() + `<div class="detail-grid"><section class="panel">${badge(resolved ? 'Encerrada em 15 nov · 15:00' : state.scenario === 'api-cache' ? 'Ativa na última consulta · situação atual desconhecida' : 'Ativa desde 16 nov · 08:40', resolved ? '' : 'warn')}<h2 style="margin:22px 0 14px">Temperatura acima de 32 °C</h2><p class="muted">A regra de exemplo abre uma ocorrência após 10 minutos acima de 32 °C. A recuperação exige 10 minutos abaixo de 30 °C.</p><div class="notice info"><strong>Primeiro, confira a leitura.</strong><p>O limiar é fictício e não considera cultura, fase de crescimento ou condições locais. Confirme o contexto antes de tomar uma decisão.</p></div><h3>Linha do tempo</h3><ol class="event-list"><li><time>${resolved ? '14:00' : '08:30'}</time><div><strong>Limite ultrapassado</strong><p>32,5 °C · aquisição simulada · ${resolved ? '15' : '16'} nov.</p></div></li><li><time>${resolved ? '14:10' : '08:40'}</time><div><strong>Ocorrência aberta</strong><p>Condição mantida por 10 minutos na regra experimental.</p></div></li>${resolved ? '<li><time>15:00</time><div><strong>Recuperação confirmada no exemplo</strong><p>Temperatura abaixo de 30 °C durante 10 minutos.</p></div></li>' : `<li><time>${pointData(points[0]).time || '—'}</time><div><strong>Última amostra disponível</strong><p>${acquired(pointData(points[0]))}. Consulte a atualidade do dado no ponto.</p></div></li>`}</ol>${button('Consultar medições do ponto', '#ponto/estufa', true)}</section><aside class="panel aside-panel"><h3>Sobre a ocorrência</h3><dl><div><dt>Origem</dt><dd>Demonstração · dados fictícios</dd></div><div><dt>Regra</dt><dd>Temperatura · experimental v1</dd></div><div><dt>Telegram</dt><dd>Não vinculado<br>Nenhuma mensagem enviada</dd></div><div><dt>Recuperação</dt><dd>${resolved ? '15 nov 2026 · 15:00 · UTC−3' : 'Não registrada'}</dd></div></dl><p class="source">Falha de comunicação não encerra nem confirma a condição desta ocorrência.</p></aside></div>`;
  }
  function setupPage() {
    return heading('PRIMEIRA CONEXÃO', 'Do notebook ao seu cultivo.', 'Roteiro da experiência futura. Esta prévia não cadastra nem configura equipamentos.') + `<div class="detail-grid"><section class="panel"><h2>Prepare uma vez. Acompanhe sempre.</h2><ol class="steps"><li><div><strong>Iniciar a instalação no notebook</strong><p>O iniciador deverá mostrar o endereço local do painel e a situação da API. O Telegram pode ser conectado depois.</p></div></li><li><div><strong>Cadastrar o ponto e o sensor</strong><p>Informar nome, localização, identidade física e canais pela administração local no notebook. Nenhum cadastro é enviado por esta prévia.</p></div></li><li><div><strong>Conferir a calibração</strong><p>Registrar método, parâmetros e versão. Sem calibração, consultar somente o sinal bruto; não inferir uma unidade física.</p></div></li><li><div><strong>Receber a primeira leitura</strong><p>Confirmar valor, unidade, origem, horário de aquisição e qualidade antes de avaliar qualquer condição.</p></div></li><li><div><strong>Abrir no celular</strong><p>Usar o endereço de rede informado pelo notebook, com ambos na mesma rede. Telegram e internet externa não são requisitos para a consulta local.</p></div></li></ol><div class="notice info"><strong>Substituiu um sensor?</strong><p>Registre uma nova identidade física no mesmo ponto pelo notebook. O histórico anterior mantém sensor e calibração originais. Aguarde a primeira leitura do novo sensor.</p></div><div class="filters"><button class="button" data-scenario="pending">Prévia da primeira leitura</button><button class="button" data-scenario="uncalibrated">Prévia sem calibração</button><button class="button" data-scenario="replaced">Prévia de substituição</button></div></section><aside class="panel aside-panel"><h3>Consulta nesta versão</h3><p class="muted">O painel mostra leituras, histórico e ocorrências. Operações administrativas ficam no notebook.</p><dl><div><dt>Conexão</dt><dd>Somente cenário fictício</dd></div><div><dt>Telegram</dt><dd>Não vinculado</dd></div><div><dt>Banco de dados</dt><dd>Nenhum banco acessado</dd></div></dl></aside></div>`;
  }
  const notFound = () => emptyState('Esta página não está na prévia.', 'Volte ao início para consultar os pontos e ocorrências do exemplo.', button('Voltar ao início', '#inicio', true));
  function exportCsv(p) {
    const rows = historyRows(p);
    const fields = ['ponto', 'canal', 'periodo_horas', 'sensor', 'valor', 'unidade', 'origem', 'qualidade', 'aquisicao', 'recebimento', 'qualidade_horario'];
    const records = rows.map(row => [p.name, state.channel, state.period, row.sensor, row.value, state.channel === 'temperature' ? '°C' : '', 'simulation', 'valid', `2026-11-16T${row.time}:00-03:00`, `2026-11-16T${row.time}:05-03:00`, 'synchronized']);
    const csv = '\uFEFF' + [fields, ...records].map(row => row.map(value => `"${String(value).replaceAll('"', '""')}"`).join(';')).join('\r\n');
    const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }));
    const link = document.createElement('a');
    link.href = url; link.download = `teko-FICTICIO-${p.id}-${state.channel}-${state.period}h.csv`; link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    $('#announcement').textContent = `${rows.length} leituras fictícias exportadas. Nenhum dado real foi consultado.`;
  }
  function setScenario(value) {
    state.scenario = value;
    $('#scenario').value = value;
    syncQuery();
  }
  function syncQuery() {
    const params = new URLSearchParams({ direction: state.direction, scenario: state.scenario });
    try { window.history.replaceState(null, '', `${location.pathname}?${params}${location.hash}`); } catch { /* file:// may disallow replaceState; the preview still works. */ }
  }
  function bindSelect(id, key) {
    const el = $(`#${id}`);
    if (!el) return;
    el.value = state[key];
    el.addEventListener('change', () => { state[key] = el.value; render(); $(`#${id}`)?.focus(); });
  }
  function render(focus = false) {
    const [page = 'inicio', id] = location.hash.slice(1).split('/');
    const active = page === 'ponto' ? 'pontos' : page === 'alerta' ? 'alertas' : page || 'inicio';
    const destinations = [['inicio', 'Início', 'home'], ['pontos', 'Pontos', 'points'], ['alertas', 'Alertas', 'alert'], ['instalacao', 'Preparação', 'settings']];
    $('#navigation').innerHTML = destinations.map(([route, label, symbol]) => `<a href="#${route}"${active === route ? ' aria-current="page"' : ''}>${icon(symbol)}<span>${label}</span>${route === 'alertas' && hasAlert() ? '<span class="nav-count" aria-label="1 ocorrência registrada">1</span>' : ''}</a>`).join('');
    $('#breadcrumb').textContent = `Tekó / ${destinations.find(d => d[0] === active)?.[1] || 'Prévia'}`;
    const renderers = { inicio: home, pontos: pointsPage, ponto: () => pointPage(id), alertas: alertsPage, alerta: () => alertPage(id), instalacao: setupPage };
    $('#conteudo').innerHTML = (renderers[page || 'inicio'] || notFound)();
    document.title = `${$('#conteudo h1, #conteudo h2')?.textContent || 'Prévia'} · Tekó V2`;
    bindSelect('channel', 'channel'); bindSelect('period', 'period'); bindSelect('point-filter', 'filter'); bindSelect('alert-filter', 'alertFilter');
    $('#export')?.addEventListener('click', () => exportCsv(pointData(points.find(p => p.id === id))));
    $('#restore')?.addEventListener('click', () => { setScenario('routine'); render(true); });
    document.querySelectorAll('[data-scenario]').forEach(el => el.addEventListener('click', () => { setScenario(el.dataset.scenario); if (location.hash === '#ponto/estufa') render(true); else location.hash = '#ponto/estufa'; }));
    if (focus) { $('#conteudo').focus(); window.scrollTo(0, 0); }
  }
  $('#direction').addEventListener('change', event => {
    state.direction = event.target.value; document.body.dataset.direction = state.direction; syncQuery();
    $('#announcement').textContent = `Direção ${state.direction === 'campo' ? 'Campo' : 'Observatório'} aplicada. A navegação e os dados foram mantidos.`;
  });
  $('#scenario').addEventListener('change', event => { setScenario(event.target.value); render(); $('#announcement').textContent = `Cenário alterado: ${event.target.selectedOptions[0].textContent}.`; });
  window.addEventListener('hashchange', () => render(true));
  render();
})();
