import { useState, useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import { useFetch } from "@/hooks/useFetch";
import { api } from "@/services/api";
import { SignalBadge } from "@/components/SignalBadge";
import { CandlestickChart } from "@/components/CandlestickChart";
import type { SignalType } from "@/types";

interface WatchlistItem {
  id: number; symbol: string; name: string; sector: string;
  price: number | null; change_1d: number | null;
  rsi: number | null; macd_bullish: boolean | null; above_ema200: boolean | null; atr: number | null;
  signal_type: SignalType | null; confidence: number | null;
  notes: string;
}

interface TickerDetail {
  symbol: string;
  name: string;
  ohlcv: { date: string; open: number; high: number; low: number; close: number; volume: number }[];
  rsi: number | null;
  macd: number | null;
  macd_signal: number | null;
  macd_histogram: number | null;
  macd_bullish: boolean | null;
  ema_50: number | null;
  ema_200: number | null;
  above_ema200: boolean | null;
  atr: number | null;
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

function TickerDetailPanel({ symbol, onClose }: { symbol: string; onClose: () => void }) {
  const { data, loading, error } = useFetch<TickerDetail>(
    () => api.tickers.detail(symbol) as Promise<TickerDetail>,
    [symbol]
  );

  if (loading) {
    return (
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-bold">{symbol}</h3>
          <button onClick={onClose} className="text-ink-tertiary hover:text-ink text-sm">Schliessen</button>
        </div>
        <div className="flex items-center justify-center py-12">
          <div className="w-5 h-5 border-2 border-accent/30 border-t-accent rounded-full animate-spin" />
          <span className="ml-3 text-sm text-ink-tertiary">Lade Chart-Daten...</span>
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-bold">{symbol}</h3>
          <button onClick={onClose} className="text-ink-tertiary hover:text-ink text-sm">Schliessen</button>
        </div>
        <p className="text-sm text-loss">Fehler beim Laden: {error || "Keine Daten"}</p>
      </div>
    );
  }

  return (
    <div className="card">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <h3 className="text-lg font-bold">{data.symbol}</h3>
          {data.name && <span className="text-sm text-ink-tertiary">{data.name}</span>}
        </div>
        <button onClick={onClose} className="text-ink-tertiary hover:text-ink text-sm">Schliessen</button>
      </div>

      {data.ohlcv && data.ohlcv.length > 0 ? (
        <CandlestickChart data={data.ohlcv} height={350} />
      ) : (
        <p className="text-sm text-ink-tertiary py-8 text-center">Keine OHLCV-Daten verfuegbar</p>
      )}

      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-4 mt-4 pt-4 border-t border-border">
        <div>
          <div className="text-[10px] text-ink-tertiary uppercase tracking-wider">RSI</div>
          <div className={`font-mono font-semibold ${
            data.rsi && data.rsi < 30 ? "text-gain" : data.rsi && data.rsi > 70 ? "text-loss" : "text-ink"
          }`}>{data.rsi?.toFixed(1) ?? "—"}</div>
        </div>
        <div>
          <div className="text-[10px] text-ink-tertiary uppercase tracking-wider">MACD</div>
          <div className={`font-mono font-semibold ${
            data.macd_bullish ? "text-gain" : data.macd_bullish === false ? "text-loss" : "text-ink"
          }`}>{data.macd?.toFixed(2) ?? "—"}</div>
        </div>
        <div>
          <div className="text-[10px] text-ink-tertiary uppercase tracking-wider">MACD Signal</div>
          <div className="font-mono font-semibold text-ink">{data.macd_signal?.toFixed(2) ?? "—"}</div>
        </div>
        <div>
          <div className="text-[10px] text-ink-tertiary uppercase tracking-wider">Histogram</div>
          <div className={`font-mono font-semibold ${
            data.macd_histogram && data.macd_histogram > 0 ? "text-gain" : data.macd_histogram && data.macd_histogram < 0 ? "text-loss" : "text-ink"
          }`}>{data.macd_histogram?.toFixed(2) ?? "—"}</div>
        </div>
        <div>
          <div className="text-[10px] text-ink-tertiary uppercase tracking-wider">EMA 50</div>
          <div className="font-mono font-semibold text-ink">{data.ema_50?.toFixed(2) ?? "—"}</div>
        </div>
        <div>
          <div className="text-[10px] text-ink-tertiary uppercase tracking-wider">EMA 200</div>
          <div className="font-mono font-semibold text-ink">{data.ema_200?.toFixed(2) ?? "—"}</div>
        </div>
        <div>
          <div className="text-[10px] text-ink-tertiary uppercase tracking-wider">ATR</div>
          <div className="font-mono font-semibold text-ink">{data.atr?.toFixed(2) ?? "—"}</div>
        </div>
      </div>
    </div>
  );
}

export function WatchlistPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const { data: items, loading, refetch } = useFetch<WatchlistItem[]>(
    () => api.watchlist.list() as Promise<WatchlistItem[]>,
    []
  );
  const [newSymbol, setNewSymbol] = useState("");
  const [adding, setAdding] = useState(false);
  const [selectedSymbol, setSelectedSymbol] = useState<string | null>(
    searchParams.get("symbol")
  );

  useEffect(() => {
    const sym = searchParams.get("symbol");
    if (sym) setSelectedSymbol(sym.toUpperCase());
  }, [searchParams]);

  const handleSelectSymbol = (symbol: string) => {
    if (selectedSymbol === symbol) {
      setSelectedSymbol(null);
      setSearchParams({});
    } else {
      setSelectedSymbol(symbol);
      setSearchParams({ symbol });
    }
  };

  const handleAdd = async () => {
    if (!newSymbol.trim()) return;
    setAdding(true);
    try {
      await api.watchlist.add({ symbol: newSymbol.trim().toUpperCase() });
      setNewSymbol("");
      refetch();
    } catch {
      alert("Fehler beim Hinzufuegen");
    }
    setAdding(false);
  };

  const handleRemove = async (symbol: string) => {
    await api.watchlist.remove(symbol);
    if (selectedSymbol === symbol) {
      setSelectedSymbol(null);
      setSearchParams({});
    }
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
            + Hinzufuegen
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
                <th className="py-3 px-2 text-left hidden md:table-cell">Sektor</th>
                <th className="py-3 px-2 text-right">Kurs</th>
                <th className="py-3 px-2 text-right">1d</th>
                <th className="py-3 px-2 text-right">RSI</th>
                <th className="py-3 px-2 text-center hidden md:table-cell">MACD</th>
                <th className="py-3 px-2 text-center hidden md:table-cell">&gt;EMA200</th>
                <th className="py-3 px-2 text-right hidden md:table-cell">ATR</th>
                <th className="py-3 px-2 text-center">Signal</th>
                <th className="py-3 px-2 text-right hidden md:table-cell">Konf.</th>
                <th className="py-3 px-2 text-center"></th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr
                  key={item.id}
                  className={`border-b border-border/50 hover:bg-surface-muted cursor-pointer transition-colors ${
                    selectedSymbol === item.symbol ? "bg-accent/[0.04]" : ""
                  }`}
                  onClick={() => handleSelectSymbol(item.symbol)}
                >
                  <td className="py-2.5 px-4">
                    <span className={`font-bold transition-colors ${selectedSymbol === item.symbol ? "text-accent" : "text-ink hover:text-accent"}`}>{item.symbol}</span>
                    {item.name && <span className="text-ink-tertiary text-xs ml-1.5 hidden lg:inline">{item.name}</span>}
                  </td>
                  <td className="py-2.5 px-2 text-ink-tertiary text-xs hidden md:table-cell">{item.sector || "—"}</td>
                  <td className="py-2.5 px-2 text-right font-mono font-semibold">
                    {item.price ? `€${item.price.toFixed(2)}` : "—"}
                  </td>
                  <td className="py-2.5 px-2 text-right"><Chg value={item.change_1d} /></td>
                  <td className="py-2.5 px-2 text-right"><RsiCell value={item.rsi} /></td>
                  <td className="py-2.5 px-2 text-center hidden md:table-cell">
                    {item.macd_bullish === null ? "—" : item.macd_bullish
                      ? <span className="text-gain text-xs">BULL</span>
                      : <span className="text-loss text-xs">BEAR</span>}
                  </td>
                  <td className="py-2.5 px-2 text-center hidden md:table-cell">
                    {item.above_ema200 === null ? "—" : item.above_ema200
                      ? <span className="text-gain">✓</span>
                      : <span className="text-loss">✗</span>}
                  </td>
                  <td className="py-2.5 px-2 text-right font-mono text-xs text-ink-tertiary hidden md:table-cell">
                    {item.atr ? `€${item.atr}` : "—"}
                  </td>
                  <td className="py-2.5 px-2 text-center">
                    {item.signal_type ? <SignalBadge type={item.signal_type} /> : <span className="text-ink-faint text-xs">—</span>}
                  </td>
                  <td className="py-2.5 px-2 text-right hidden md:table-cell">
                    {item.confidence ? (
                      <span className={`font-bold text-sm ${
                        item.confidence >= 65 ? "text-gain" :
                        item.confidence >= 45 ? "text-ink-secondary" : "text-loss"
                      }`}>{item.confidence.toFixed(0)}%</span>
                    ) : "—"}
                  </td>
                  <td className="py-2.5 px-2 text-center">
                    <button
                      onClick={(e) => { e.stopPropagation(); handleRemove(item.symbol); }}
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
          <p className="text-ink-faint text-sm">Fuege Ticker hinzu um Signale zu generieren</p>
        </div>
      )}

      {selectedSymbol && (
        <TickerDetailPanel
          symbol={selectedSymbol}
          onClose={() => { setSelectedSymbol(null); setSearchParams({}); }}
        />
      )}
    </div>
  );
}
