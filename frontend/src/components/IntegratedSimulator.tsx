import { useEffect, useRef, useState } from 'react';
import { FlaskConical, Send } from 'lucide-react';
import { apiBase } from '../data/api';

type Config = { enabled: boolean; prepared: boolean; rule_enabled: boolean; node_id: string; channel_id: string };
type Receipt = { duplicate: boolean; values: number[]; node_id: string; channel_id: string; measured_at: string };
type Submission = { request_id: string; values: number[] };
function requestId() {
  const bytes = crypto.getRandomValues(new Uint8Array(16));
  bytes[6] = (bytes[6] & 15) | 64; bytes[8] = (bytes[8] & 63) | 128;
  const hex = Array.from(bytes, b => b.toString(16).padStart(2, '0')).join('');
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
}
export function IntegratedSimulator({ apiUrl, onView }: { apiUrl: string; onView(node: string, channel: string): void }) {
  const [config, setConfig] = useState<Config | null>(null);
  const [configError, setConfigError] = useState('');
  const [token, setToken] = useState('');
  const [value, setValue] = useState('50');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [receipt, setReceipt] = useState<Receipt | null>(null);
  const [pending, setPending] = useState<Submission | null>(null);
  const locked = useRef(false);
  useEffect(() => {
    const controller = new AbortController();
    setConfig(null); setConfigError('');
    async function load() {
      try {
        const response = await fetch(`${apiBase(apiUrl)}/api/v1/simulator/config`, { signal: controller.signal });
        if (!response.ok) throw new Error();
        setConfig(await response.json());
      } catch { if (!controller.signal.aborted) setConfigError('Não foi possível consultar o simulador. Confira a conexão da API nas configurações.'); }
    }
    void load(); return () => controller.abort();
  }, [apiUrl]);
  async function submit(values?: number[]) {
    if (locked.current) return;
    const submission = pending || { request_id: requestId(), values: values || [] };
    if (!token.trim() || !submission.values.length) { setError('Informe a credencial do simulador e um valor.'); return; }
    locked.current = true; setBusy(true); setError(''); setReceipt(null); setPending(submission);
    const controller = new AbortController(); const timer = setTimeout(() => controller.abort(), 15000);
    try {
      const response = await fetch(`${apiBase(apiUrl)}/api/v1/simulator/readings`, {
        method: 'POST', signal: controller.signal, redirect: 'error',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token.trim()}` }, body: JSON.stringify(submission),
      });
      if (!response.ok) {
        if (response.status < 500) setPending(null);
        throw new Error(response.status === 401 || response.status === 403 ? 'Credencial inválida ou simulador desabilitado. Confira a preparação no backend.' : response.status === 409 ? 'O backend não aceitou o envio. Confira a preparação do simulador.' : `Não foi possível salvar (HTTP ${response.status}).`);
      }
      setReceipt(await response.json()); setPending(null);
    } catch (failure) { setError(failure instanceof Error && failure.name !== 'AbortError' && failure.message !== 'Failed to fetch' ? failure.message : 'Não houve confirmação do envio. Tente novamente: a mesma tentativa não será gravada duas vezes.'); }
    finally { clearTimeout(timer); locked.current = false; setBusy(false); }
  }
  const disabled = busy || !!pending || !config?.enabled || !config?.prepared;
  return <div className="integrated-simulator">
    <div className="simulation"><FlaskConical size={22} /><p><strong>Simulação integrada.</strong> Os valores fictícios serão salvos no backend e poderão gerar avisos de teste no Telegram.</p></div>
    {configError && <p className="error" role="alert">{configError}</p>}
    {!config && !configError && <p role="status">Consultando disponibilidade…</p>}
    {config && (!config.enabled || !config.prepared) && <p className="notice">Prepare o simulador no backend com <code>prepare-simulator</code> e habilite <code>SIMULATOR_ENABLED=true</code>. Reinicie a API.</p>}
    {config?.prepared && !config.rule_enabled && <p className="notice">A regra experimental está desativada. Os valores serão salvos, mas ela não gerará alertas.</p>}
    <p className="muted">Ponto: Simulação integrada · Canal: sinal fictício (%) · Origem: simulação. Esta ferramenta não fornece recomendação de irrigação.</p>
    <label className="field">Credencial do simulador<input type="password" autoComplete="off" value={token} onChange={event => setToken(event.target.value)} placeholder="Token de gateway-simulator" disabled={busy} /></label>
    <p className="muted">Use o token emitido para <code>gateway-simulator</code>. Ele fica somente em memória nesta tela. Os tokens do Telegram e do bot não são usados aqui.</p>
    <form onSubmit={event => { event.preventDefault(); void submit([Number(value)]); }}><label className="field">Valor fictício (%)<input type="number" min="0" max="100" step="0.1" required value={value} onChange={event => setValue(event.target.value)} disabled={disabled} /></label><button className="button secondary" disabled={disabled || !token.trim()}><Send size={17} /> Salvar leitura</button></form>
    <section><h2>Demonstrar um alerta</h2><p className="muted">A regra abre uma ocorrência após 3 valores abaixo de 30 e registra recuperação após 3 valores a partir de 35. Cada botão envia um lote de 3 amostras fictícias no horário atual.</p><div className="mode-options"><button className="button secondary" disabled={disabled || !token.trim()} onClick={() => void submit([20, 21, 22])}>Enviar valores de alerta</button><button className="button secondary" disabled={disabled || !token.trim()} onClick={() => void submit([36, 37, 38])}>Enviar recuperação</button></div></section>
    {busy && <p role="status">Salvando no backend…</p>}
    {error && <p className="error" role="alert">{error}</p>}
    {pending && !busy && <button className="button secondary" onClick={() => void submit()}>Tentar novamente o mesmo envio</button>}
    {receipt && <div className="simulator-success" role="status"><strong>{receipt.duplicate ? 'Envio já registrado; nenhuma duplicação.' : 'Leituras salvas no backend.'}</strong><p>Valores: {receipt.values.join(', ')}% · {new Date(receipt.measured_at).toLocaleString('pt-BR')}</p><p>Os avisos seguem a fila do bot. A confirmação de gravação não confirma recebimento no Telegram.</p><button className="button secondary" onClick={() => onView(receipt.node_id, receipt.channel_id)}>Ver leituras e alertas no painel</button></div>}
  </div>;
}
