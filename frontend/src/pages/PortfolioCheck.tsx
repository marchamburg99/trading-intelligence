import { useState, useRef } from "react";
import { api } from "@/services/api";
import { SignalBadge } from "@/components/SignalBadge";
import type { SignalType } from "@/types";

interface Position {
  symbol: string;
  name?: string;
  sector?: string;
  shares: number;
  entry_price: number;
  current_price?: number;
  current_value?: number;
  position_value: number;
  unrealized_pnl: number;
  unrealized_pct: number;
  concentration?: number;
  currency_symbol?: string;
  signal_type?: string;
  confidence?: number;
  data_quality?: number;
  risk_rating?: number;
  stop_loss?: number;
  take_profit?: number;
  rsi?: number;
  action: string;
  reason: string;
  reasoning?: string;
  status?: string;
}

interface CheckResult {
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
  NICHT_ANALYSIERBAR: { bg: "bg-surface-muted border-border", text: "text-ink-faint", label: "Nicht analysierbar" },
};

function ActionBadge({ action }: { action: string }) {
  const style = ACTION_STYLES[action] || ACTION_STYLES.BEOBACHTEN;
  return (
    <span className={`text-[11px] font-bold px-2.5 py-1 rounded-lg border ${style.bg} ${style.text}`}>
      {style.label}
    </span>
  );
}

function PositionRow({ p, expanded, onToggle }: { p: Position; expanded: boolean; onToggle: () => void }) {
  const ccy = p.currency_symbol || "$";
  return (
    <>
      <tr
        className="border-b border-border/50 hover:bg-surface-muted cursor-pointer transition-colors"
        onClick={onToggle}
      >
        <td className="py-3 px-4">
          <a href={`https://finance.yahoo.com/quote/${p.symbol}`} target="_blank" rel="noopener noreferrer"
            onClick={(e) => e.stopPropagation()} className="font-bold text-ink hover:text-accent transition-colors">{p.symbol}</a>
          {p.name && <span className="text-ink-tertiary text-xs ml-1.5 hidden lg:inline">{p.name}</span>}
        </td>
        <td className="py-3 px-2 text-right font-mono">{p.shares}</td>
        <td className="py-3 px-2 text-right font-mono">{ccy}{p.entry_price.toFixed(2)}</td>
        <td className="py-3 px-2 text-right font-mono">{p.current_price ? `${ccy}${p.current_price.toFixed(2)}` : "—"}</td>
        <td className="py-3 px-2 text-right">
          <span className={`font-mono font-semibold ${p.unrealized_pnl >= 0 ? "text-gain" : "text-loss"}`}>
            {p.unrealized_pnl >= 0 ? "+" : ""}{ccy}{p.unrealized_pnl.toFixed(0)} ({p.unrealized_pct >= 0 ? "+" : ""}{p.unrealized_pct.toFixed(1)}%)
          </span>
        </td>
        <td className="py-3 px-2 text-center hidden md:table-cell">
          {p.signal_type ? <SignalBadge type={p.signal_type as SignalType} /> : <span className="text-ink-faint text-xs">—</span>}
        </td>
        <td className="py-3 px-2 text-center">
          <ActionBadge action={p.action} />
        </td>
      </tr>
      {expanded && (
        <tr className="border-b border-border/50 bg-surface-muted/50">
          <td colSpan={7} className="px-4 py-4">
            <div className="space-y-3">
              <p className="text-sm text-ink-secondary leading-relaxed">{p.reason}</p>
              {p.stop_loss && p.take_profit && (
                <div className="flex gap-6 text-sm">
                  <span>SL: <b className="text-loss font-mono">{ccy}{p.stop_loss.toFixed(2)}</b></span>
                  <span>TP: <b className="text-gain font-mono">{ccy}{p.take_profit.toFixed(2)}</b></span>
                  {p.confidence && <span>Konfidenz: <b>{p.confidence.toFixed(0)}%</b></span>}
                  {p.rsi && <span>RSI: <b className={p.rsi < 30 ? "text-gain" : p.rsi > 70 ? "text-loss" : ""}>{p.rsi.toFixed(0)}</b></span>}
                  {p.concentration != null && <span>Anteil: <b>{p.concentration.toFixed(1)}%</b> vom Kapital</span>}
                </div>
              )}
              {p.reasoning && p.reasoning !== p.reason && (
                <p className="text-xs text-ink-tertiary">{p.reasoning}</p>
              )}
            </div>
          </td>
        </tr>
      )}
    </>
  );
}

export function PortfolioCheck() {
  const [mode, setMode] = useState<"manual" | "text" | "csv">("text");
  const [textInput, setTextInput] = useState("AAPL 10 150\nMSFT 5 380\nNVDA 3 800");
  const [manualRows, setManualRows] = useState([{ symbol: "", shares: "", price: "" }]);
  const [result, setResult] = useState<CheckResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedIdx, setExpandedIdx] = useState<number | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const handleCheck = async () => {
    setLoading(true);
    setError(null);
    try {
      let positions: { symbol: string; shares: number; entry_price: number }[] = [];

      if (mode === "text") {
        positions = textInput
          .split("\n")
          .map((line) => line.trim())
          .filter((l) => l && !l.startsWith("#"))
          .map((line) => {
            const parts = line.replace(/,/g, " ").replace(/\t/g, " ").split(/\s+/);
            return { symbol: parts[0].toUpperCase(), shares: parseFloat(parts[1]) || 0, entry_price: parseFloat(parts[2]) || 0 };
          })
          .filter((p) => p.shares > 0);
      } else if (mode === "manual") {
        positions = manualRows
          .filter((r) => r.symbol && parseFloat(r.shares) > 0)
          .map((r) => ({ symbol: r.symbol.toUpperCase(), shares: parseFloat(r.shares), entry_price: parseFloat(r.price) || 0 }));
      }

      if (positions.length === 0) {
        setError("Keine gueltige Positionen eingegeben");
        setLoading(false);
        return;
      }

      const data = await api.portfolioCheck.check(positions) as CheckResult;
      setResult(data);
    } catch (e) {
      setError(`Fehler: ${e}`);
    }
    setLoading(false);
  };

  const handleCsvUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setLoading(true);
    setError(null);
    try {
      const data = await api.portfolioCheck.uploadCsv(file) as CheckResult;
      if ("error" in data) {
        setError((data as { error: string }).error);
      } else {
        setResult(data);
      }
    } catch (err) {
      setError(`CSV-Fehler: ${err}`);
    }
    setLoading(false);
    if (fileRef.current) fileRef.current.value = "";
  };

  const addManualRow = () => setManualRows([...manualRows, { symbol: "", shares: "", price: "" }]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-ink">Portfolio-Check</h1>
        <p className="text-ink-tertiary text-sm mt-1">
          Bestehendes Portfolio eintragen und von der Signal-Engine analysieren lassen
        </p>
      </div>

      {/* Eingabe-Modi */}
      <div className="card">
        <div className="flex gap-2 mb-4">
          {([["text", "Schnell-Eingabe"], ["manual", "Einzeln"], ["csv", "CSV-Import"]] as const).map(([key, label]) => (
            <button key={key} onClick={() => setMode(key)}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                mode === key ? "bg-accent text-white" : "bg-surface-muted text-ink-secondary hover:text-ink border border-border"
              }`}>
              {label}
            </button>
          ))}
        </div>

        {mode === "text" && (
          <div>
            <p className="text-xs text-ink-tertiary mb-2">Eine Position pro Zeile: <code className="bg-surface-muted px-1 rounded">SYMBOL STUECKZAHL KAUFKURS</code></p>
            <textarea
              value={textInput}
              onChange={(e) => setTextInput(e.target.value)}
              rows={8}
              className="input font-mono text-sm w-full"
              placeholder={"AAPL 10 150.00\nMSFT 5 380.50\nTTE.PA 20 65.00"}
            />
          </div>
        )}

        {mode === "manual" && (
          <div className="space-y-2">
            {manualRows.map((row, i) => (
              <div key={i} className="flex gap-2">
                <input placeholder="Symbol" value={row.symbol}
                  onChange={(e) => { const r = [...manualRows]; r[i].symbol = e.target.value; setManualRows(r); }}
                  className="input w-28 font-mono" />
                <input placeholder="Stueck" type="number" value={row.shares}
                  onChange={(e) => { const r = [...manualRows]; r[i].shares = e.target.value; setManualRows(r); }}
                  className="input w-24 font-mono" />
                <input placeholder="Kaufkurs" type="number" step="0.01" value={row.price}
                  onChange={(e) => { const r = [...manualRows]; r[i].price = e.target.value; setManualRows(r); }}
                  className="input w-28 font-mono" />
                {manualRows.length > 1 && (
                  <button onClick={() => setManualRows(manualRows.filter((_, j) => j !== i))}
                    className="text-ink-faint hover:text-loss text-sm px-2">x</button>
                )}
              </div>
            ))}
            <button onClick={addManualRow} className="text-sm text-accent hover:text-accent-hover">+ Position</button>
          </div>
        )}

        {mode === "csv" && (
          <div className="text-center py-6 border-2 border-dashed border-border rounded-xl">
            <p className="text-sm text-ink-secondary mb-3">CSV-Datei hochladen (comdirect-Format oder einfach)</p>
            <input type="file" accept=".csv,.txt" onChange={handleCsvUpload} ref={fileRef}
              className="text-sm text-ink-tertiary" />
          </div>
        )}

        {mode !== "csv" && (
          <button onClick={handleCheck} disabled={loading}
            className="btn-primary mt-4 w-full disabled:opacity-50">
            {loading ? "Analysiere..." : "Portfolio analysieren"}
          </button>
        )}

        {error && <p className="text-sm text-loss mt-3">{error}</p>}
      </div>

      {/* Ergebnisse */}
      {result && (
        <>
          {/* Summary */}
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            <div className="card text-center">
              <div className="text-[10px] text-ink-tertiary uppercase tracking-wider">Positionen</div>
              <div className="text-2xl font-bold text-ink">{result.total_positions}</div>
            </div>
            <div className="card text-center">
              <div className="text-[10px] text-ink-tertiary uppercase tracking-wider">Gesamtwert</div>
              <div className="text-2xl font-bold text-ink">${result.total_value.toLocaleString(undefined, { maximumFractionDigits: 0 })}</div>
            </div>
            <div className="card text-center">
              <div className="text-[10px] text-ink-tertiary uppercase tracking-wider">P&L</div>
              <div className={`text-2xl font-bold ${result.total_pnl >= 0 ? "text-gain" : "text-loss"}`}>
                {result.total_pnl >= 0 ? "+" : ""}${result.total_pnl.toLocaleString(undefined, { maximumFractionDigits: 0 })}
              </div>
            </div>
            <div className="card text-center">
              <div className="text-[10px] text-ink-tertiary uppercase tracking-wider">P&L %</div>
              <div className={`text-2xl font-bold ${result.total_pnl_pct >= 0 ? "text-gain" : "text-loss"}`}>
                {result.total_pnl_pct >= 0 ? "+" : ""}{result.total_pnl_pct.toFixed(1)}%
              </div>
            </div>
            <div className="card text-center">
              <div className="text-[10px] text-ink-tertiary uppercase tracking-wider">Kapital</div>
              <div className="text-2xl font-bold text-ink">€{result.portfolio_capital.toLocaleString(undefined, { maximumFractionDigits: 0 })}</div>
            </div>
          </div>

          {/* Action Summary */}
          <div className="flex gap-3 flex-wrap">
            {Object.entries(result.action_summary).map(([action, count]) => {
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
                </tr>
              </thead>
              <tbody>
                {result.positions.map((p, i) => (
                  <PositionRow key={p.symbol} p={p} expanded={expandedIdx === i}
                    onToggle={() => setExpandedIdx(expandedIdx === i ? null : i)} />
                ))}
              </tbody>
            </table>
          </div>

          {/* Sektor-Allokation */}
          {Object.keys(result.sector_allocation).length > 0 && (
            <div className="card">
              <h3 className="section-label mb-3">Sektor-Allokation</h3>
              <div className="space-y-2">
                {Object.entries(result.sector_allocation)
                  .sort(([, a], [, b]) => b - a)
                  .map(([sector, pct]) => (
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
    </div>
  );
}
