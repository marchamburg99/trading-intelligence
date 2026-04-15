import { useState } from "react";
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

interface TickerDetailRaw {
  ticker: { symbol: string; name: string; sector: string };
  ohlcv: { date: string; open: number; high: number; low: number; close: number; volume: number }[];
  indicators: {
    rsi_14: number | null; macd: number | null; macd_signal: number | null;
    ema_21: number | null; ema_50: number | null; ema_200: number | null;
    bb_upper: number | null; bb_lower: number | null; atr_14: number | null;
    stoch_k: number | null; stoch_d: number | null;
  } | null;
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

interface SignalData {
  symbol: string; signal_type: string; confidence: number;
  entry_price: number; stop_loss: number; take_profit: number;
  risk_reward_ratio: number; position_size: number; reasoning: string;
  risk_rating: number; expected_hold_days: number;
}

function TickerDetailPanel({ symbol, onClose }: { symbol: string; onClose: () => void }) {
  const { data: raw, loading, error } = useFetch<TickerDetailRaw>(
    () => api.tickers.detail(symbol) as Promise<TickerDetailRaw>,
    [symbol]
  );
  const { data: signal } = useFetch<SignalData>(
    () => api.signals.forSymbol(symbol) as Promise<SignalData>,
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

  if (error || !raw) {
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

  const ind = raw.indicators;
  const macdBullish = ind?.macd != null && ind?.macd_signal != null ? ind.macd > ind.macd_signal : null;

  return (
    <div className="card">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <a href={`https://finance.yahoo.com/quote/${raw.ticker.symbol}`} target="_blank" rel="noopener noreferrer" className="text-lg font-bold hover:text-accent transition-colors">{raw.ticker.symbol}</a>
          {raw.ticker.name && <span className="text-sm text-ink-tertiary">{raw.ticker.name}</span>}
          {raw.ticker.sector && <span className="text-xs bg-surface-muted text-ink-tertiary px-2 py-0.5 rounded-lg">{raw.ticker.sector}</span>}
        </div>
        <button onClick={onClose} className="text-ink-tertiary hover:text-ink text-sm">Schliessen</button>
      </div>

      {raw.ohlcv && raw.ohlcv.length > 0 ? (
        <CandlestickChart data={raw.ohlcv} height={350} />
      ) : (
        <p className="text-sm text-ink-tertiary py-8 text-center">Keine OHLCV-Daten verfuegbar</p>
      )}

      {ind && (
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-4 mt-4 pt-4 border-t border-border">
          <div>
            <div className="text-[10px] text-ink-tertiary uppercase tracking-wider">RSI</div>
            <div className={`font-mono font-semibold ${
              ind.rsi_14 != null && ind.rsi_14 < 30 ? "text-gain" : ind.rsi_14 != null && ind.rsi_14 > 70 ? "text-loss" : "text-ink"
            }`}>{ind.rsi_14?.toFixed(1) ?? "—"}</div>
          </div>
          <div>
            <div className="text-[10px] text-ink-tertiary uppercase tracking-wider">MACD</div>
            <div className={`font-mono font-semibold ${
              macdBullish === true ? "text-gain" : macdBullish === false ? "text-loss" : "text-ink"
            }`}>{ind.macd?.toFixed(2) ?? "—"}</div>
          </div>
          <div>
            <div className="text-[10px] text-ink-tertiary uppercase tracking-wider">MACD Signal</div>
            <div className="font-mono font-semibold text-ink">{ind.macd_signal?.toFixed(2) ?? "—"}</div>
          </div>
          <div>
            <div className="text-[10px] text-ink-tertiary uppercase tracking-wider">EMA 50</div>
            <div className="font-mono font-semibold text-ink">{ind.ema_50?.toFixed(2) ?? "—"}</div>
          </div>
          <div>
            <div className="text-[10px] text-ink-tertiary uppercase tracking-wider">EMA 200</div>
            <div className="font-mono font-semibold text-ink">{ind.ema_200?.toFixed(2) ?? "—"}</div>
          </div>
          <div>
            <div className="text-[10px] text-ink-tertiary uppercase tracking-wider">ATR</div>
            <div className="font-mono font-semibold text-ink">{ind.atr_14?.toFixed(2) ?? "—"}</div>
          </div>
          <div>
            <div className="text-[10px] text-ink-tertiary uppercase tracking-wider">Stochastic</div>
            <div className={`font-mono font-semibold ${
              ind.stoch_k != null && ind.stoch_k < 20 ? "text-gain" : ind.stoch_k != null && ind.stoch_k > 80 ? "text-loss" : "text-ink"
            }`}>{ind.stoch_k?.toFixed(1) ?? "—"}</div>
          </div>
        </div>
      )}

      {signal && (() => {
        const suffixMap: Record<string, string> = { ".DE": "€", ".PA": "€", ".AS": "€", ".MI": "€", ".SW": "CHF ", ".L": "£" };
        const ccy = Object.entries(suffixMap).find(([s]) => symbol.endsWith(s))?.[1] ?? "$";
        return (
        <div className={`mt-4 pt-4 border-t border-border`}>
          <div className="flex items-center gap-3 mb-3">
            <h4 className="text-sm font-semibold text-ink">Trading-Signal</h4>
            <SignalBadge type={signal.signal_type as SignalType} />
            <span className={`text-sm font-bold ${
              signal.confidence >= 68 ? "text-gain" : signal.confidence >= 50 ? "text-accent" : "text-ink-secondary"
            }`}>{signal.confidence.toFixed(0)}% Konfidenz</span>
          </div>
          <div className="bg-surface-muted rounded-xl p-4 mb-3 border border-border/50">
            <div className="grid grid-cols-3 gap-4 text-center">
              <div>
                <div className="text-[10px] uppercase tracking-wider text-ink-tertiary">Einstieg</div>
                <div className="text-lg font-bold font-mono">{ccy}{signal.entry_price.toFixed(2)}</div>
              </div>
              <div>
                <div className="text-[10px] uppercase tracking-wider text-loss">Stop-Loss</div>
                <div className="text-lg font-bold font-mono text-loss">{ccy}{signal.stop_loss.toFixed(2)}</div>
              </div>
              <div>
                <div className="text-[10px] uppercase tracking-wider text-gain">Take-Profit</div>
                <div className="text-lg font-bold font-mono text-gain">{ccy}{signal.take_profit.toFixed(2)}</div>
              </div>
            </div>
            <div className="border-t border-border/50 mt-3 pt-3 grid grid-cols-3 gap-4 text-center text-sm">
              <div>
                <div className="text-[10px] text-ink-tertiary">R:R</div>
                <div className="font-semibold text-ink">{signal.risk_reward_ratio?.toFixed(1) ?? "—"}:1</div>
              </div>
              <div>
                <div className="text-[10px] text-ink-tertiary">Stueck</div>
                <div className="font-semibold text-ink">{signal.position_size?.toFixed(0) ?? "—"}</div>
              </div>
              <div>
                <div className="text-[10px] text-ink-tertiary">Haltedauer</div>
                <div className="font-semibold text-ink">{signal.expected_hold_days ?? "—"}d</div>
              </div>
            </div>
          </div>
          <p className="text-sm text-ink-secondary leading-relaxed">{signal.reasoning}</p>
        </div>
        );
      })()}
    </div>
  );
}

export function WatchlistPage() {
  const [searchParams] = useSearchParams();
  const { data: items, loading, refetch } = useFetch<WatchlistItem[]>(
    () => api.watchlist.list() as Promise<WatchlistItem[]>,
    []
  );
  const [newSymbol, setNewSymbol] = useState("");
  const [adding, setAdding] = useState(false);
  const [selectedSymbol, setSelectedSymbol] = useState<string | null>(
    searchParams.get("symbol")?.toUpperCase() || null
  );

  const handleSelectSymbol = (symbol: string) => {
    setSelectedSymbol(prev => prev === symbol ? null : symbol);
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
                    <a href={`https://finance.yahoo.com/quote/${item.symbol}`} target="_blank" rel="noopener noreferrer" onClick={(e) => e.stopPropagation()} className={`font-bold transition-colors ${selectedSymbol === item.symbol ? "text-accent" : "text-ink hover:text-accent"}`}>{item.symbol}</a>
                    {item.name && <a href={`https://finance.yahoo.com/quote/${item.symbol}`} target="_blank" rel="noopener noreferrer" onClick={(e) => e.stopPropagation()} className="text-ink-tertiary hover:text-accent text-xs ml-1.5 hidden lg:inline transition-colors">{item.name}</a>}
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
          onClose={() => setSelectedSymbol(null)}
        />
      )}
    </div>
  );
}
