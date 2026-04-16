import { useState, useRef, Component, type ReactNode, useEffect } from "react";
import { api } from "@/services/api";
import { useFetch } from "@/hooks/useFetch";
import { SignalBadge } from "@/components/SignalBadge";
import type { SignalType } from "@/types";

interface Position {
  id: number;
  symbol: string;
  name?: string;
  sector?: string;
  shares: number;
  entry_price: number;
  current_price?: number | null;
  current_value?: number;
  position_value: number;
  unrealized_pnl?: number | null;
  unrealized_pct?: number | null;
  concentration?: number;
  currency_symbol?: string;
  signal_type?: string | null;
  confidence?: number | null;
  data_quality?: number | null;
  risk_rating?: number | null;
  stop_loss?: number | null;
  take_profit?: number | null;
  rsi?: number | null;
  action: string;
  reason: string;
  reasoning?: string;
}

interface PortfolioData {
  portfolio_capital: number;
  total_positions: number;
  total_value: number;
  total_pnl: number;
  total_pnl_pct: number;
  action_summary: Record<string, number>;
  sector_allocation: Record<string, number>;
  positions: Position[];
}

const ACTION_STYLES: Record<string, { bg: string; text: string; label: string }> = {
  AUFSTOCKEN: { bg: "bg-gain-bg border-gain-light", text: "text-gain", label: "Aufstocken" },
  HALTEN: { bg: "bg-surface-muted border-border", text: "text-ink", label: "Halten" },
  REDUZIEREN: { bg: "bg-warn-bg border-warn-light", text: "text-warn", label: "Reduzieren" },
  VERKAUFEN: { bg: "bg-loss-bg border-loss-light", text: "text-loss", label: "Verkaufen" },
  SOFORT_VERKAUFEN: { bg: "bg-loss-bg border-loss", text: "text-loss", label: "Sofort verkaufen!" },
  STOP_LOSS: { bg: "bg-loss-bg border-loss", text: "text-loss", label: "Stop-Loss!" },
  BEOBACHTEN: { bg: "bg-surface-muted border-border", text: "text-ink-secondary", label: "Beobachten" },
};

function ActionBadge({ action }: { action: string }) {
  const style = ACTION_STYLES[action] || ACTION_STYLES.BEOBACHTEN;
  return (
    <span className={`text-[11px] font-bold px-2.5 py-1 rounded-lg border ${style.bg} ${style.text}`}>
      {style.label}
    </span>
  );
}

function PositionRow({ p, expanded, onToggle, onDelete, onEdit }: {
  p: Position; expanded: boolean; onToggle: () => void;
  onDelete: (id: number) => void; onEdit: (p: Position) => void;
}) {
  const ccy = p.currency_symbol || "$";
  const hasPnl = p.unrealized_pnl != null && p.unrealized_pct != null;
  const pnlVal = p.unrealized_pnl ?? 0;
  const pctVal = p.unrealized_pct ?? 0;
  return (
    <>
      <tr className="border-b border-border/50 hover:bg-surface-muted cursor-pointer transition-colors" onClick={onToggle}>
        <td className="py-3 px-4">
          <a href={`https://finance.yahoo.com/quote/${p.symbol}`} target="_blank" rel="noopener noreferrer"
            onClick={(e) => e.stopPropagation()} className="font-bold text-ink hover:text-accent transition-colors">{p.symbol}</a>
          {p.name && <span className="text-ink-tertiary text-xs ml-1.5 hidden lg:inline">{p.name}</span>}
        </td>
        <td className="py-3 px-2 text-right font-mono">{p.shares}</td>
        <td className="py-3 px-2 text-right font-mono">{ccy}{(p.entry_price ?? 0).toFixed(2)}</td>
        <td className="py-3 px-2 text-right font-mono">{p.current_price != null ? `${ccy}${p.current_price.toFixed(2)}` : "—"}</td>
        <td className="py-3 px-2 text-right">
          {hasPnl ? (
            <span className={`font-mono font-semibold ${pnlVal >= 0 ? "text-gain" : "text-loss"}`}>
              {pnlVal >= 0 ? "+" : ""}{ccy}{pnlVal.toFixed(0)} ({pctVal >= 0 ? "+" : ""}{pctVal.toFixed(1)}%)
            </span>
          ) : <span className="text-ink-faint text-xs">—</span>}
        </td>
        <td className="py-3 px-2 text-center hidden md:table-cell">
          {p.signal_type ? <SignalBadge type={p.signal_type as SignalType} /> : <span className="text-ink-faint text-xs">—</span>}
        </td>
        <td className="py-3 px-2 text-center"><ActionBadge action={p.action} /></td>
        <td className="py-3 px-2 text-center">
          <button onClick={(e) => { e.stopPropagation(); onEdit(p); }} className="text-ink-faint hover:text-accent text-xs px-1">bearbeiten</button>
          <button onClick={(e) => { e.stopPropagation(); if (confirm(`${p.symbol} entfernen?`)) onDelete(p.id); }}
            className="text-ink-faint hover:text-loss text-xs px-1">x</button>
        </td>
      </tr>
      {expanded && (
        <tr className="border-b border-border/50 bg-surface-muted/50">
          <td colSpan={8} className="px-4 py-4">
            <div className="space-y-3">
              <p className="text-sm text-ink-secondary leading-relaxed">{p.reason}</p>
              {(p.stop_loss != null || p.take_profit != null || p.confidence != null || p.rsi != null) && (
                <div className="flex gap-6 text-sm flex-wrap">
                  {p.stop_loss != null && <span>SL: <b className="text-loss font-mono">{ccy}{p.stop_loss.toFixed(2)}</b></span>}
                  {p.take_profit != null && <span>TP: <b className="text-gain font-mono">{ccy}{p.take_profit.toFixed(2)}</b></span>}
                  {p.confidence != null && <span>Konfidenz: <b>{p.confidence.toFixed(0)}%</b></span>}
                  {p.rsi != null && <span>RSI: <b className={p.rsi < 30 ? "text-gain" : p.rsi > 70 ? "text-loss" : ""}>{p.rsi.toFixed(0)}</b></span>}
                  {p.concentration != null && <span>Anteil: <b>{p.concentration.toFixed(1)}%</b></span>}
                </div>
              )}
              {p.reasoning && p.reasoning !== p.reason && <p className="text-xs text-ink-tertiary">{p.reasoning}</p>}
            </div>
          </td>
        </tr>
      )}
    </>
  );
}

function AddPositionModal({ onClose, onAdd, initial }: {
  onClose: () => void;
  onAdd: (data: { symbol: string; shares: number; entry_price: number }) => Promise<void>;
  initial?: Position;
}) {
  const [symbol, setSymbol] = useState(initial?.symbol ?? "");
  const [shares, setShares] = useState(String(initial?.shares ?? ""));
  const [price, setPrice] = useState(String(initial?.entry_price ?? ""));
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    const p = parseFloat(price.replace(",", "."));
    const s = parseFloat(shares.replace(",", "."));
    if (!symbol || !s || s <= 0) return;
    setSaving(true);
    await onAdd({ symbol: symbol.toUpperCase(), shares: s, entry_price: p || 0 });
    setSaving(false);
    onClose();
  };

  return (
    <div className="fixed inset-0 bg-black/30 flex items-center justify-center z-50" onClick={onClose}>
      <div className="bg-surface rounded-2xl p-6 shadow-float max-w-md w-full" onClick={(e) => e.stopPropagation()}>
        <h3 className="text-lg font-bold mb-4">{initial ? "Position bearbeiten" : "Position hinzufuegen"}</h3>
        <div className="space-y-3">
          <div>
            <label className="text-[10px] text-ink-tertiary uppercase">Symbol</label>
            <input value={symbol} onChange={(e) => setSymbol(e.target.value)} className="input font-mono" disabled={!!initial} placeholder="AAPL, DTE.DE..." />
          </div>
          <div>
            <label className="text-[10px] text-ink-tertiary uppercase">Stueckzahl</label>
            <input value={shares} onChange={(e) => setShares(e.target.value)} className="input font-mono" placeholder="100" />
          </div>
          <div>
            <label className="text-[10px] text-ink-tertiary uppercase">Kaufkurs</label>
            <input value={price} onChange={(e) => setPrice(e.target.value)} className="input font-mono" placeholder="150,00" />
          </div>
        </div>
        <div className="flex gap-2 mt-4">
          <button onClick={onClose} className="btn-secondary flex-1">Abbrechen</button>
          <button onClick={handleSave} disabled={saving} className="btn-primary flex-1">{saving ? "..." : "Speichern"}</button>
        </div>
      </div>
    </div>
  );
}

class ErrorBoundary extends Component<{ children: ReactNode }, { error: Error | null }> {
  state = { error: null as Error | null };
  static getDerivedStateFromError(error: Error) { return { error }; }
  render() {
    if (this.state.error) {
      return (
        <div className="card border-loss/20 bg-loss-bg/30">
          <h3 className="text-loss font-bold mb-2">Fehler</h3>
          <p className="text-sm">{String(this.state.error.message || this.state.error)}</p>
          <button onClick={() => this.setState({ error: null })} className="btn-primary mt-3">Zuruecksetzen</button>
        </div>
      );
    }
    return this.props.children;
  }
}

export function Portfolio() {
  return <ErrorBoundary><PortfolioInner /></ErrorBoundary>;
}

function PortfolioInner() {
  const { data, loading, refetch } = useFetch<PortfolioData>(() => api.portfolio.overview() as Promise<PortfolioData>, [], 60000);
  const [expandedIdx, setExpandedIdx] = useState<number | null>(null);
  const [showAdd, setShowAdd] = useState(false);
  const [editPos, setEditPos] = useState<Position | null>(null);
  const [showImport, setShowImport] = useState(false);
  const [textInput, setTextInput] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);
  const [alerts, setAlerts] = useState<Array<{ symbol: string; from: string; to: string; timestamp: string; reason: string }>>([]);

  useEffect(() => {
    (api.portfolio.alerts() as Promise<typeof alerts>).then(setAlerts).catch(() => {});
  }, []);

  const handleAdd = async (d: { symbol: string; shares: number; entry_price: number }) => {
    await api.portfolio.addHolding(d);
    refetch();
  };

  const handleEdit = async (d: { symbol: string; shares: number; entry_price: number }) => {
    if (!editPos) return;
    await api.portfolio.updateHolding(editPos.id, { shares: d.shares, entry_price: d.entry_price });
    setEditPos(null);
    refetch();
  };

  const handleDelete = async (id: number) => {
    await api.portfolio.deleteHolding(id);
    refetch();
  };

  const handleBulkImport = async () => {
    const positions = textInput
      .split("\n")
      .map((l) => l.trim())
      .filter((l) => l && !l.startsWith("#"))
      .map((line) => {
        const parts = line.replace(/\t/g, " ").split(/\s+/);
        const parseNum = (s: string) => parseFloat((s || "").replace(/\./g, "").replace(",", "."));
        return { symbol: parts[0].toUpperCase(), shares: parseNum(parts[1]) || 0, entry_price: parseNum(parts[2]) || 0 };
      })
      .filter((p) => p.shares > 0);
    if (positions.length === 0) return;
    if (!confirm(`${positions.length} Positionen importieren? Ersetzt alle bestehenden.`)) return;
    await api.portfolio.bulkReplace(positions);
    setTextInput("");
    setShowImport(false);
    refetch();
  };

  const handleCsv = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (!confirm("CSV importieren? Ersetzt alle bestehenden Positionen.")) return;
    await api.portfolio.uploadCsv(file);
    setShowImport(false);
    refetch();
    if (fileRef.current) fileRef.current.value = "";
  };

  const handleClearAlerts = async () => {
    await api.portfolio.clearAlerts();
    setAlerts([]);
  };

  if (loading && !data) {
    return <div className="flex items-center justify-center py-20"><div className="w-6 h-6 border-2 border-accent/30 border-t-accent rounded-full animate-spin" /></div>;
  }

  const isEmpty = !data || data.total_positions === 0;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-ink">Mein Portfolio</h1>
          <p className="text-ink-tertiary text-sm mt-1">
            Persistente Positionen, automatisch alle 15 Min gecheckt
          </p>
        </div>
        <div className="flex gap-2">
          <button onClick={() => setShowImport(true)} className="btn-secondary text-sm">Import</button>
          <button onClick={() => setShowAdd(true)} className="btn-primary text-sm">+ Position</button>
        </div>
      </div>

      {/* Alerts */}
      {alerts.length > 0 && (
        <div className="card border-warn/20 bg-warn-bg/30">
          <div className="flex items-center justify-between mb-2">
            <h3 className="section-label text-warn">{alerts.length} Portfolio-Alert(s)</h3>
            <button onClick={handleClearAlerts} className="text-xs text-ink-tertiary hover:text-ink">Alle loeschen</button>
          </div>
          <div className="space-y-1">
            {alerts.slice(-5).reverse().map((a, i) => (
              <p key={i} className="text-sm text-ink-secondary">
                <b>{a.symbol}</b>: {a.from || "—"} → <span className="text-warn font-semibold">{a.to}</span> · {a.reason}
              </p>
            ))}
          </div>
        </div>
      )}

      {isEmpty ? (
        <div className="card text-center py-12">
          <p className="text-ink-tertiary text-lg mb-2">Portfolio ist leer</p>
          <p className="text-ink-faint text-sm mb-4">Fuege Positionen manuell hinzu oder importiere sie</p>
          <div className="flex gap-2 justify-center">
            <button onClick={() => setShowAdd(true)} className="btn-primary">+ Position</button>
            <button onClick={() => setShowImport(true)} className="btn-secondary">Import</button>
          </div>
        </div>
      ) : (
        <>
          {/* Summary */}
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            <div className="card text-center">
              <div className="text-[10px] text-ink-tertiary uppercase tracking-wider">Positionen</div>
              <div className="text-2xl font-bold text-ink">{data!.total_positions}</div>
            </div>
            <div className="card text-center">
              <div className="text-[10px] text-ink-tertiary uppercase tracking-wider">Gesamtwert</div>
              <div className="text-2xl font-bold text-ink">${(data!.total_value ?? 0).toLocaleString(undefined, { maximumFractionDigits: 0 })}</div>
            </div>
            <div className="card text-center">
              <div className="text-[10px] text-ink-tertiary uppercase tracking-wider">P&L</div>
              <div className={`text-2xl font-bold ${(data!.total_pnl ?? 0) >= 0 ? "text-gain" : "text-loss"}`}>
                {(data!.total_pnl ?? 0) >= 0 ? "+" : ""}${(data!.total_pnl ?? 0).toLocaleString(undefined, { maximumFractionDigits: 0 })}
              </div>
            </div>
            <div className="card text-center">
              <div className="text-[10px] text-ink-tertiary uppercase tracking-wider">P&L %</div>
              <div className={`text-2xl font-bold ${(data!.total_pnl_pct ?? 0) >= 0 ? "text-gain" : "text-loss"}`}>
                {(data!.total_pnl_pct ?? 0) >= 0 ? "+" : ""}{(data!.total_pnl_pct ?? 0).toFixed(1)}%
              </div>
            </div>
            <div className="card text-center">
              <div className="text-[10px] text-ink-tertiary uppercase tracking-wider">Kapital</div>
              <div className="text-2xl font-bold text-ink">€{(data!.portfolio_capital ?? 0).toLocaleString(undefined, { maximumFractionDigits: 0 })}</div>
            </div>
          </div>

          {/* Action Summary */}
          <div className="flex gap-3 flex-wrap">
            {Object.entries(data!.action_summary).map(([action, count]) => {
              const style = ACTION_STYLES[action] || ACTION_STYLES.BEOBACHTEN;
              return (
                <div key={action} className={`px-3 py-2 rounded-xl border ${style.bg}`}>
                  <span className={`font-bold ${style.text}`}>{count}x {style.label}</span>
                </div>
              );
            })}
          </div>

          {/* Positions Table */}
          <div className="card p-0 overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-[10px] uppercase tracking-wider text-ink-tertiary border-b border-border bg-surface-muted/50">
                  <th className="py-3 px-4 text-left">Symbol</th>
                  <th className="py-3 px-2 text-right">Stueck</th>
                  <th className="py-3 px-2 text-right">Kaufkurs</th>
                  <th className="py-3 px-2 text-right">Aktuell</th>
                  <th className="py-3 px-2 text-right">P&L</th>
                  <th className="py-3 px-2 text-center hidden md:table-cell">Signal</th>
                  <th className="py-3 px-2 text-center">Empfehlung</th>
                  <th className="py-3 px-2"></th>
                </tr>
              </thead>
              <tbody>
                {data!.positions.map((p, i) => (
                  <PositionRow key={p.id} p={p} expanded={expandedIdx === i}
                    onToggle={() => setExpandedIdx(expandedIdx === i ? null : i)}
                    onDelete={handleDelete}
                    onEdit={(pos) => setEditPos(pos)} />
                ))}
              </tbody>
            </table>
          </div>

          {/* Sektor-Allokation */}
          {Object.keys(data!.sector_allocation).length > 0 && (
            <div className="card">
              <h3 className="section-label mb-3">Sektor-Allokation</h3>
              <div className="space-y-2">
                {Object.entries(data!.sector_allocation).sort(([, a], [, b]) => b - a).map(([sector, pct]) => (
                  <div key={sector} className="flex items-center gap-3">
                    <span className="text-sm text-ink-secondary w-32 shrink-0">{sector}</span>
                    <div className="flex-1 h-2 bg-surface-muted rounded-full overflow-hidden">
                      <div className="h-full bg-accent rounded-full" style={{ width: `${Math.min(100, pct)}%` }} />
                    </div>
                    <span className="text-sm font-mono text-ink-secondary w-12 text-right">{pct.toFixed(0)}%</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}

      {showAdd && <AddPositionModal onClose={() => setShowAdd(false)} onAdd={handleAdd} />}
      {editPos && <AddPositionModal onClose={() => setEditPos(null)} onAdd={handleEdit} initial={editPos} />}

      {showImport && (
        <div className="fixed inset-0 bg-black/30 flex items-center justify-center z-50" onClick={() => setShowImport(false)}>
          <div className="bg-surface rounded-2xl p-6 shadow-float max-w-lg w-full" onClick={(e) => e.stopPropagation()}>
            <h3 className="text-lg font-bold mb-3">Portfolio importieren</h3>
            <p className="text-xs text-ink-tertiary mb-3">Ersetzt alle bestehenden Positionen!</p>
            <div className="space-y-3">
              <div>
                <label className="text-[10px] text-ink-tertiary uppercase mb-1 block">Als Text (SYMBOL STUECK KURS pro Zeile)</label>
                <textarea value={textInput} onChange={(e) => setTextInput(e.target.value)} rows={6}
                  className="input font-mono text-sm" placeholder={"AAPL 10 150,00\nDTE.DE 100 16,79"} />
                <button onClick={handleBulkImport} disabled={!textInput.trim()} className="btn-primary mt-2 w-full">Text importieren</button>
              </div>
              <div className="border-t border-border pt-3">
                <label className="text-[10px] text-ink-tertiary uppercase mb-1 block">Oder CSV-Datei</label>
                <input type="file" accept=".csv,.txt" onChange={handleCsv} ref={fileRef} className="text-sm w-full" />
              </div>
            </div>
            <button onClick={() => setShowImport(false)} className="btn-secondary w-full mt-4">Abbrechen</button>
          </div>
        </div>
      )}
    </div>
  );
}
