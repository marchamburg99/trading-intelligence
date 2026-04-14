import { useState } from "react";
import { useFetch } from "@/hooks/useFetch";
import { api } from "@/services/api";
import { SignalBadge } from "@/components/SignalBadge";
import type { SignalType } from "@/types";

interface WatchlistItem {
  id: number; symbol: string; name: string; sector: string;
  price: number | null; change_1d: number | null;
  rsi: number | null; macd_bullish: boolean | null; above_ema200: boolean | null; atr: number | null;
  signal_type: SignalType | null; confidence: number | null;
  notes: string;
}

function Chg({ value }: { value: number | null }) {
  if (value === null) return <span className="text-ink-faint">—</span>;
  const c = value > 0 ? "text-gain" : value < 0 ? "text-loss" : "text-ink-tertiary";
  return <span className={`font-mono text-sm font-semibold ${c}`}>{value > 0 ? "+" : ""}{value.toFixed(2)}%</span>;
}

function RsiCell({ value }: { value: number | null }) {
  if (!value) return <span className="text-ink-faint">—</span>;
  const c = value < 30 ? "text-gain" : value > 70 ? "text-loss" : "text-ink-secondary";
  return <span className={`font-mono text-sm ${c}`}>{value.toFixed(1)}</span>;
}

export function WatchlistPage() {
  const { data: items, loading, refetch } = useFetch<WatchlistItem[]>(
    () => api.watchlist.list() as Promise<WatchlistItem[]>,
    []
  );
  const [newSymbol, setNewSymbol] = useState("");
  const [adding, setAdding] = useState(false);

  const handleAdd = async () => {
    if (!newSymbol.trim()) return;
    setAdding(true);
    try {
      await api.watchlist.add({ symbol: newSymbol.trim().toUpperCase() });
      setNewSymbol("");
      refetch();
    } catch {
      alert("Fehler beim Hinzufügen");
    }
    setAdding(false);
  };

  const handleRemove = async (symbol: string) => {
    await api.watchlist.remove(symbol);
    refetch();
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold">Watchlist</h1>
          <p className="text-ink-tertiary text-sm">{items?.length || 0} Titel · Sortiert nach Signal-Konfidenz</p>
        </div>
        <div className="flex gap-2">
          <input
            type="text"
            value={newSymbol}
            onChange={(e) => setNewSymbol(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleAdd()}
            placeholder="AAPL, MSFT..."
            className="input w-40"
          />
          <button onClick={handleAdd} disabled={adding} className="btn-primary text-sm">
            + Hinzufügen
          </button>
        </div>
      </div>

      {loading ? (
        <p className="text-ink-tertiary">Lade...</p>
      ) : items && items.length > 0 ? (
        <div className="card p-0 overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-[10px] uppercase tracking-wider text-ink-tertiary border-b border-border bg-surface-muted/50">
                <th className="py-3 px-4 text-left">Symbol</th>
                <th className="py-3 px-2 text-left">Sektor</th>
                <th className="py-3 px-2 text-right">Kurs</th>
                <th className="py-3 px-2 text-right">1d</th>
                <th className="py-3 px-2 text-right">RSI</th>
                <th className="py-3 px-2 text-center">MACD</th>
                <th className="py-3 px-2 text-center">&gt;EMA200</th>
                <th className="py-3 px-2 text-right">ATR</th>
                <th className="py-3 px-2 text-center">Signal</th>
                <th className="py-3 px-2 text-right">Konf.</th>
                <th className="py-3 px-2 text-center"></th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.id} className="border-b border-border/50 hover:bg-surface-muted">
                  <td className="py-2.5 px-4">
                    <a href={`https://finance.yahoo.com/quote/${item.symbol}`} target="_blank" rel="noopener noreferrer" className="font-bold hover:text-accent transition-colors">{item.symbol}</a>
                    {item.name && <span className="text-ink-tertiary text-xs ml-1.5 hidden lg:inline">{item.name}</span>}
                  </td>
                  <td className="py-2.5 px-2 text-ink-tertiary text-xs">{item.sector || "—"}</td>
                  <td className="py-2.5 px-2 text-right font-mono font-semibold">
                    {item.price ? `€${item.price.toFixed(2)}` : "—"}
                  </td>
                  <td className="py-2.5 px-2 text-right"><Chg value={item.change_1d} /></td>
                  <td className="py-2.5 px-2 text-right"><RsiCell value={item.rsi} /></td>
                  <td className="py-2.5 px-2 text-center">
                    {item.macd_bullish === null ? "—" : item.macd_bullish
                      ? <span className="text-gain text-xs">BULL</span>
                      : <span className="text-loss text-xs">BEAR</span>}
                  </td>
                  <td className="py-2.5 px-2 text-center">
                    {item.above_ema200 === null ? "—" : item.above_ema200
                      ? <span className="text-gain">✓</span>
                      : <span className="text-loss">✗</span>}
                  </td>
                  <td className="py-2.5 px-2 text-right font-mono text-xs text-ink-tertiary">
                    {item.atr ? `€${item.atr}` : "—"}
                  </td>
                  <td className="py-2.5 px-2 text-center">
                    {item.signal_type ? <SignalBadge type={item.signal_type} /> : <span className="text-ink-faint text-xs">—</span>}
                  </td>
                  <td className="py-2.5 px-2 text-right">
                    {item.confidence ? (
                      <span className={`font-bold text-sm ${
                        item.confidence >= 65 ? "text-gain" :
                        item.confidence >= 45 ? "text-ink-secondary" : "text-loss"
                      }`}>{item.confidence.toFixed(0)}%</span>
                    ) : "—"}
                  </td>
                  <td className="py-2.5 px-2 text-center">
                    <button
                      onClick={() => handleRemove(item.symbol)}
                      className="text-ink-faint hover:text-loss text-xs"
                    >✕</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="card text-center py-12">
          <p className="text-ink-tertiary text-lg mb-2">Watchlist ist leer</p>
          <p className="text-ink-faint text-sm">Füge Ticker hinzu um Signale zu generieren</p>
        </div>
      )}
    </div>
  );
}
