import { createContext, useContext, useEffect, useRef, useState, type ReactNode } from 'react';
import { ArrowLeft, ClipboardList, Settings, X } from 'lucide-react';
import { apiBase } from '../data/api';
import { IntegratedSimulator } from './IntegratedSimulator';
import { ProjectGuide } from './ProjectGuide';

export type FarmProfile = { area: string; soil: string; crop: string; irrigation: string };
const empty: FarmProfile = { area: '', soil: '', crop: '', irrigation: '' };
function stored(key: string) { try { return localStorage.getItem(key) || ''; } catch { return ''; } }
function savedFarm(): FarmProfile {
  try {
    const value = JSON.parse(stored('teko-triagem-v1') || 'null');
    return value && typeof value === 'object' ? Object.fromEntries(Object.keys(empty).map(key => [key, typeof value[key] === 'string' ? value[key] : ''])) as FarmProfile : empty;
  } catch { return empty; }
}
const initialApi = () => stored('agrosponge-api-url') || import.meta.env.VITE_API_BASE_URL || (location.protocol === 'http:' ? `${location.protocol}//${location.hostname}:8000` : '');
type Screen = 'triage' | 'settings' | 'simulation' | 'information' | 'integrated';
type Tools = { farm: FarmProfile; apiUrl: string; open(screen: Screen): void };
const Context = createContext<Tools | null>(null);
export function usePanelTools() { const value = useContext(Context); if (!value) throw new Error('Painel sem contexto.'); return value; }

export function PanelActions() {
  const { open } = usePanelTools();
  return <div className="panel-actions"><button className="utility-button" onClick={() => open('triage')}><ClipboardList size={19} /><span>Minha lavoura</span></button><button className="utility-button" aria-label="Configurações" onClick={() => open('settings')}><Settings size={20} /></button></div>;
}

export function PanelToolsProvider({ mode, onMode, children }: { mode: 'demo' | 'live'; onMode(mode: 'demo' | 'live'): void; children: ReactNode }) {
  const [farm, setFarm] = useState(savedFarm);
  const [draft, setDraft] = useState(farm);
  const [apiUrl, setApiUrl] = useState(initialApi);
  const [apiDraft, setApiDraft] = useState(apiUrl);
  const [screen, setScreen] = useState<Screen | null>(null);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const dialog = useRef<HTMLDialogElement>(null);
  const previousFocus = useRef<HTMLElement | null>(null);
  const legacyHash = useRef(false);
  function open(next: Screen) {
    if (!dialog.current?.open) previousFocus.current = document.activeElement as HTMLElement;
    setDraft(farm); setApiDraft(apiUrl); setError(''); setScreen(next);
  }
  function close() {
    setScreen(null);
    if (legacyHash.current) { history.replaceState(null, '', `${location.pathname}${location.search}#overview`); legacyHash.current = false; }
  }
  useEffect(() => {
    const handleHash = () => {
      const hash = location.hash.slice(1);
      if (['triagem', 'configuracoes', 'simulacao', 'graficos', 'receita', 'usar', 'selo', 'guide'].includes(hash)) {
        legacyHash.current = true;
        open(hash === 'triagem' ? 'triage' : hash === 'configuracoes' ? 'settings' : ['simulacao', 'graficos', 'guide'].includes(hash) ? 'simulation' : 'information');
      } else if (legacyHash.current) { legacyHash.current = false; setScreen(null); }
    };
    handleHash(); window.addEventListener('hashchange', handleHash);
    return () => window.removeEventListener('hashchange', handleHash);
  }, []);
  useEffect(() => {
    const element = dialog.current;
    if (screen && element && !element.open) element.showModal();
    if (!screen && element?.open) { element.close(); const target = previousFocus.current?.isConnected ? previousFocus.current : document.querySelector<HTMLElement>('[aria-label="Configurações"]'); target?.focus(); }
  }, [screen]);
  useEffect(() => { if (notice) { const timer = setTimeout(() => setNotice(''), 5000); return () => clearTimeout(timer); } }, [notice]);
  function saveFarm() {
    const value = Object.fromEntries(Object.entries(draft).map(([key, value]) => [key, value.trim()])) as FarmProfile;
    if (Object.values(value).some(field => !field)) { setError('Preencha os campos da lavoura ou escolha Não sei quando necessário.'); return; }
    try { localStorage.setItem('teko-triagem-v1', JSON.stringify(value)); }
    catch { setError('Não foi possível salvar neste navegador. Verifique as permissões de armazenamento.'); return; }
    setFarm(value); setNotice('Perfil da lavoura salvo neste navegador.'); close();
  }
  function saveConnection() {
    try {
      const value = apiBase(apiDraft);
      localStorage.setItem('agrosponge-api-url', value);
      setApiUrl(value); setError(''); setNotice('Endereço da API salvo.');
    } catch (error) { setError(error instanceof Error ? error.message : 'Não foi possível salvar a conexão.'); }
  }
  return <Context.Provider value={{ farm, apiUrl, open }}>
    {children}
    <dialog className={`utility-dialog ${screen === 'triage' ? 'triage-dialog' : ''}`} ref={dialog} aria-labelledby="utility-title" onCancel={event => { event.preventDefault(); close(); }}>
      <div className="utility-heading"><button className="utility-back" onClick={close}><ArrowLeft size={18} /> Voltar ao painel</button><button className="icon-button" onClick={close} aria-label="Fechar"><X size={19} /></button></div>
      <p className="eyebrow">TEKÓ · SUA LAVOURA</p>
      <h1 id="utility-title">{screen === 'triage' ? 'Vamos conhecer sua lavoura.' : screen === 'settings' ? 'Configurações' : screen === 'simulation' ? 'Explorar uma simulação' : screen === 'integrated' ? 'Simulação com backend e Telegram' : 'Sobre a solução'}</h1>
      {screen === 'triage' && <><p className="muted">Cadastre o perfil da área para personalizar seu painel. As informações ficam somente neste navegador e ainda não são compartilhadas com o bot.</p><form className="triage-form" onSubmit={event => { event.preventDefault(); saveFarm(); }}>
        <label className="field">Nome da área ou lavoura<input autoFocus required value={draft.area} onChange={e => setDraft({ ...draft, area: e.target.value })} placeholder="Ex.: Horta do sítio" maxLength={80} /></label>
        <label className="field">O que você cultiva?<input required value={draft.crop} onChange={e => setDraft({ ...draft, crop: e.target.value })} placeholder="Ex.: milho, feijão, hortaliças" maxLength={80} /></label>
        <label className="field">Tipo de solo<select required value={draft.soil} onChange={e => setDraft({ ...draft, soil: e.target.value })}><option value="">Selecione</option>{['Argiloso', 'Arenoso', 'Misto', 'Não sei informar'].map(v => <option key={v}>{v}</option>)}</select></label>
        <label className="field">Possui irrigação?<select required value={draft.irrigation} onChange={e => setDraft({ ...draft, irrigation: e.target.value })}><option value="">Selecione</option>{['Sim', 'Não', 'Não sei'].map(v => <option key={v}>{v}</option>)}</select></label>
        {error && <p className="error" role="alert">{error}</p>}<button className="button primary-button" type="submit">Salvar e voltar ao painel</button>
      </form></>}
      {screen === 'settings' && <div className="settings-content"><section><h2>Dados apresentados</h2><p className="muted">Escolha entre consultar o backend ou explorar exemplos fictícios.</p><div className="mode-options">{(['live', 'demo'] as const).map(value => <button className="button secondary" key={value} aria-pressed={mode === value} onClick={() => onMode(value)}>{value === 'live' ? 'Dados da API' : 'Demonstração'}</button>)}</div></section>
        <form className="settings-connection" onSubmit={event => { event.preventDefault(); saveConnection(); }}><h2>Conexão com o monitoramento</h2><label className="field">Endereço da API<input type="url" value={apiDraft} onChange={e => setApiDraft(e.target.value)} placeholder="http://192.168.1.10:8000" required /></label><p className="muted">No celular, use o IP do notebook na mesma rede. A API precisa permitir a origem deste painel.</p>{error && <p className="error" role="alert">{error}</p>}<button className="button secondary" type="submit">Salvar conexão</button></form>
        <section><h2>Perfil da lavoura</h2><p className="muted">{farm.area || 'Sua área ainda não foi cadastrada.'}</p><button className="button secondary" onClick={() => open('triage')}>Editar cadastro e triagem</button></section>
        <section><h2>Demonstração com Telegram</h2><p className="muted">Envie valores fictícios para o backend e acompanhe os mesmos dados no painel e no bot.</p><button className="button secondary" onClick={() => setScreen('integrated')}>Abrir simulação integrada</button></section>
        <section><h2>Conheça o Tekó</h2><div className="mode-options"><button className="button secondary" onClick={() => { setError(''); setScreen('simulation'); }}>Explorar simulação</button><button className="button secondary" onClick={() => { setError(''); setScreen('information'); }}>Sobre a solução</button></div></section>
      </div>}
      {screen === 'integrated' && <IntegratedSimulator apiUrl={apiUrl} onView={(node, channel) => {
        const url = new URL(location.href); url.searchParams.set('mode', 'live'); url.searchParams.set('node', node); url.searchParams.set('channel', channel); url.hash = 'overview';
        location.assign(url.toString());
      }} />}
      {(screen === 'simulation'  || screen === 'information') && <ProjectGuide initialColor={new URLSearchParams(location.search).get('lote')} page={screen === 'simulation' ? 'simulation' : 'recipe'} triage={farm} onTriage={() => setScreen('triage')} />}
      {notice && screen && <p className="notice" role="status">{notice}</p>}
    </dialog>
    {notice && !screen && <div className="toast" role="status">{notice}<button aria-label="Fechar aviso" onClick={() => setNotice('')}>×</button></div>}
  </Context.Provider>;
}

export function FarmSummary() {
  const { farm, open } = usePanelTools();
  return farm.area ? <div className="farm-summary"><div><strong>{farm.area}</strong><p>{farm.crop || 'Cultura não informada'} · Solo: {farm.soil || 'não informado'} · Irrigação: {farm.irrigation || 'não informada'}</p></div><button className="inline-link" onClick={() => open('triage')}>Editar perfil</button></div> : <div className="farm-summary"><div><strong>Conheça melhor sua lavoura.</strong><p>Cadastre a área, a cultura e o tipo de solo.</p></div><button className="button secondary" onClick={() => open('triage')}>Fazer cadastro e triagem</button></div>;
}
