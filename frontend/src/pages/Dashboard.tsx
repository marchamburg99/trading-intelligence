import { useState, useEffect } from "react";
import { useFetch } from "@/hooks/useFetch";
import { api } from "@/services/api";
import { SignalBadge } from "@/components/SignalBadge";
import { ConfidenceBar } from "@/components/ConfidenceBar";
import { OpenPositions } from "@/components/OpenPositions";
import { MarketOverview } from "@/components/MarketOverview";
import { Price } from "@/components/Price";
import type { SignalType } from "@/types";

interface SignalItem {
  symbol: string; name: string; sector: string; signal_type: SignalType;
  confidence: number; entry_price: number; stop_loss: number; take_profit: number;
  risk_per_share: number; reward_per_share: number; risk_reward_ratio: number;
  position_size: number; position_value: number; max_loss: number; max_gain: number;
  risk_rating: number; expected_hold_days: number; reasoning: string;
  ta_score: number; fundamental_score: number; sentiment_score: number; macro_score: number;
  currency?: string; currency_symbol?: string;
  entry_eur?: number | null; sl_eur?: number | null; tp_eur?: number | null;
}

interface Position {
  id: number; symbol: string; direction: string; entry_price: number;
  current_price: number | null; stop_loss: number | null; take_profit: number | null;
  position_size: number; unrealized_pnl: number; unrealized_pct: number;
  trade_date: string; days_held: number; setup_type: string; alert: string | null;
}

interface ProductInfo {
  leverage: number; direction: string; name: string; type: string; underlying?: string;
}

interface DashboardData {
  briefing: string[];
  regime: { status: string; message: string; vix: number };
  macro: { ampel: "GREEN" | "YELLOW" | "RED"; indicators: Record<string, { value: number; status: string; date: string }> };
  signals: { total: number; buy: number; sell: number; hold: number; avoid: number; buys: SignalItem[]; watch: SignalItem[]; sells: SignalItem[] };
  products: { leveraged: (SignalItem & { product?: ProductInfo; effective_exposure?: number })[]; crypto: (SignalItem & { product?: ProductInfo })[]; commodities: (SignalItem & { product?: ProductInfo })[] };
  positions: { open: Position[]; unrealized_total: number; realized_total: number; total_trades: number; win_rate: number };
  indices: { symbol: string; name: string; price: number; change_1d: number; change_20d: number }[];
  sectors: { symbol: string; name: string; change_1d: number; change_20d: number }[];
  movers: { gainers: { symbol: string; name: string; price: number; change: number }[]; losers: { symbol: string; name: string; price: number; change: number }[] };
}

const AMPEL = {
  GREEN: { dot: "bg-gain", text: "text-gain", label: "BULLISH", bg: "bg-gain-bg border-gain-light" },
  YELLOW: { dot: "bg-warn", text: "text-warn", label: "NEUTRAL", bg: "bg-warn-bg border-warn-light" },
  RED: { dot: "bg-loss", text: "text-loss", label: "BEARISH", bg: "bg-loss-bg border-loss-light" },
};

function TradeCard({ s, type }: { s: SignalItem; type: "buy" | "sell" | "watch" }) {
  const [showExec, setShowExec] = useState(false);
  const [execShares, setExecShares] = useState(s.position_size);
  const [execPrice, setExecPrice] = useState(s.entry_price);
  const [execSL, setExecSL] = useState(s.stop_loss);
  const [execTP, setExecTP] = useState(s.take_profit);
  const [submitting, setSubmitting] = useState(false);

  const borderStyle = type === "buy" ? "border-gain/20 bg-gain-bg/30" : type === "sell" ? "border-loss/20 bg-loss-bg/30" : "border-border bg-surface";
  const accentColor = type === "buy" ? "text-gain" : type === "sell" ? "text-loss" : "text-accent";

  const execVolume = execShares * execPrice;
  const execMaxLoss = execShares * Math.abs(execPrice - execSL);
  const execMaxGain = execShares * Math.abs(execTP - execPrice);

  const handleOpenExec = () => {
    fetch(`/api/quotes/${s.symbol}`).then(r => r.json()).then(q => {
      if (q.price) setExecPrice(q.price);
    }).catch(() => {});
    setShowExec(true);
  };

  const handleSubmit = () => {
    setSubmitting(true);
    const now = new Date();
    api.journal.create({
      symbol: s.symbol, trade_date: now.toISOString().split("T")[0],
      direction: type === "sell" ? "SHORT" : "LONG",
      entry_price: execPrice, position_size: execShares, stop_loss: execSL, take_profit: execTP,
      setup_type: `Signal ${s.confidence.toFixed(0)}%`,
      notes: `${s.reasoning}\n\nGeloggt: ${now.toLocaleString("de-DE")} @ ${s.currency_symbol || "€"}${execPrice}`,
    }).then(() => {
      setShowExec(false);
      setSubmitting(false);
      if (confirm(`✅ Trade im Journal geloggt!\n\n${execShares}x ${s.symbol} @ ${s.currency_symbol || "€"}${execPrice}\nSL: ${s.currency_symbol || "€"}${execSL} | TP: ${s.currency_symbol || "€"}${execTP}\n\nJetzt bei deinem Broker ausführen?\n→ OK öffnet Yahoo Finance für ${s.symbol}`)) {
        window.open(`https://finance.yahoo.com/quote/${s.symbol}`, "_blank");
      }
      window.location.reload();
    });
  };

  return (
    <div className={`border rounded-2xl p-5 shadow-card ${borderStyle}`}>
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-3">
          <a href={`https://finance.yahoo.com/quote/${s.symbol}`} target="_blank" rel="noopener noreferrer" className="text-xl font-bold text-ink hover:text-accent transition-colors">{s.symbol}</a>
          <SignalBadge type={s.signal_type} />
          <span className="text-sm text-ink-tertiary">{s.name}</span>
        </div>
        <div className="text-right">
          <div className="text-[10px] text-ink-tertiary uppercase tracking-wider">Konfidenz</div>
          <div className={`text-xl font-bold ${accentColor}`}>{s.confidence.toFixed(0)}%</div>
        </div>
      </div>

      <div className="bg-surface-muted rounded-xl p-4 mb-3 border border-border/50">
        <div className="grid grid-cols-3 gap-4 text-center">
          <div>
            <div className="text-[10px] uppercase tracking-wider text-ink-tertiary">Einstieg</div>
            <div className="text-lg font-bold"><Price value={s.entry_price} currency={s.currency} currencySymbol={s.currency_symbol} eurValue={s.entry_eur} /></div>
          </div>
          <div>
            <div className="text-[10px] uppercase tracking-wider text-loss">Stop-Loss</div>
            <div className="text-lg font-bold text-loss"><Price value={s.stop_loss} currency={s.currency} currencySymbol={s.currency_symbol} eurValue={s.sl_eur} className="text-loss" /></div>
          </div>
          <div>
            <div className="text-[10px] uppercase tracking-wider text-gain">Take-Profit</div>
            <div className="text-lg font-bold text-gain"><Price value={s.take_profit} currency={s.currency} currencySymbol={s.currency_symbol} eurValue={s.tp_eur} className="text-gain" /></div>
          </div>
        </div>
        <div className="border-t border-border/50 mt-3 pt-3 grid grid-cols-4 gap-3 text-center text-sm">
          <div><div className="text-[10px] text-ink-tertiary">Stück</div><div className="font-semibold text-ink">{s.position_size}</div></div>
          <div><div className="text-[10px] text-ink-tertiary">Volumen</div><div className="font-semibold text-ink"><Price value={s.position_value} currency={s.currency} currencySymbol={s.currency_symbol} /></div></div>
          <div><div className="text-[10px] text-ink-tertiary">Max. Verlust</div><div className="font-semibold text-loss">-<Price value={s.max_loss} currency={s.currency} currencySymbol={s.currency_symbol} className="text-loss" /></div></div>
          <div><div className="text-[10px] text-ink-tertiary">Max. Gewinn</div><div className="font-semibold text-gain">+<Price value={s.max_gain} currency={s.currency} currencySymbol={s.currency_symbol} className="text-gain" /></div></div>
        </div>
      </div>

      <p className="text-sm text-ink-secondary mb-3 leading-relaxed">{s.reasoning}</p>

      {showExec ? (
        <div className="bg-surface-muted border border-border rounded-xl p-4 space-y-3">
          <div className="flex items-center justify-between">
            <h4 className="text-sm font-semibold text-ink">{type === "sell" ? "SHORT" : "LONG"} {s.symbol} ausführen</h4>
            <button onClick={() => setShowExec(false)} className="text-ink-tertiary hover:text-ink text-xs">Abbrechen</button>
          </div>
          <div className="grid grid-cols-4 gap-3">
            <label className="block"><span className="text-[10px] text-ink-tertiary block mb-1">Stückzahl</span>
              <input type="number" value={execShares} onChange={e => setExecShares(Number(e.target.value))} min={1} className="input font-mono" /></label>
            <label className="block"><span className="text-[10px] text-ink-tertiary block mb-1">Kurs (€)</span>
              <input type="number" value={execPrice} onChange={e => setExecPrice(Number(e.target.value))} step={0.01} className="input font-mono" /></label>
            <label className="block"><span className="text-[10px] text-loss block mb-1">Stop-Loss (€)</span>
              <input type="number" value={execSL} onChange={e => setExecSL(Number(e.target.value))} step={0.01} className="input font-mono" /></label>
            <label className="block"><span className="text-[10px] text-gain block mb-1">Take-Profit (€)</span>
              <input type="number" value={execTP} onChange={e => setExecTP(Number(e.target.value))} step={0.01} className="input font-mono" /></label>
          </div>
          <div className="flex items-center justify-between text-xs text-ink-tertiary border-t border-border pt-2">
            <span>Volumen: <b className="text-ink">€{execVolume.toLocaleString(undefined, {maximumFractionDigits: 0})}</b></span>
            <span>Max. Verlust: <b className="text-loss">€{execMaxLoss.toLocaleString(undefined, {maximumFractionDigits: 0})}</b></span>
            <span>Max. Gewinn: <b className="text-gain">€{execMaxGain.toLocaleString(undefined, {maximumFractionDigits: 0})}</b></span>
            <button onClick={handleSubmit} disabled={submitting || execShares <= 0}
              className={`px-5 py-2 rounded-xl font-semibold text-sm transition-all active:scale-[0.98] disabled:opacity-50 ${
                type === "buy" ? "bg-gain text-white hover:bg-gain/90" :
                type === "sell" ? "bg-loss text-white hover:bg-loss/90" :
                "bg-accent text-white hover:bg-accent-hover"
              }`}>{submitting ? "..." : `${execShares}x ${s.symbol} @ €${execPrice} bestätigen`}</button>
          </div>
        </div>
      ) : (
        <div className="flex items-center justify-between">
          <div className="flex gap-3 text-[10px] text-ink-faint font-mono">
            <span>TA:{s.ta_score.toFixed(0)}</span><span>MF:{s.fundamental_score.toFixed(0)}</span>
            <span>Sent:{s.sentiment_score.toFixed(0)}</span><span>Makro:{s.macro_score.toFixed(0)}</span>
            <span>R:R 1:{s.risk_reward_ratio.toFixed(1)}</span><span>{s.expected_hold_days}d</span>
          </div>
          <div className="flex gap-3">
            <a href={`/watchlist?symbol=${s.symbol}`} className="text-[10px] text-ink-tertiary hover:text-accent">Chart</a>
            <a href={`/risk?entry_price=${s.entry_price}&stop_loss=${s.stop_loss}&take_profit=${s.take_profit}`} className="text-[10px] text-ink-tertiary hover:text-accent">Risiko berechnen</a>
          </div>
          <button onClick={handleOpenExec}
            className={`px-4 py-2 rounded-xl font-semibold text-sm transition-all active:scale-[0.98] ${
              type === "buy" ? "bg-gain text-white hover:bg-gain/90" :
              type === "sell" ? "bg-loss text-white hover:bg-loss/90" :
              "bg-accent text-white hover:bg-accent-hover"
            }`}>{type === "sell" ? "SHORT ins Journal" : "Trade ins Journal"}</button>
        </div>
      )}
    </div>
  );
}

export function Dashboard() {
  const { data, loading, error, refetch } = useFetch<DashboardData>(
    () => api.dashboard.overview() as Promise<DashboardData>, [], 60000,
  );
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());
  const [refreshing, setRefreshing] = useState(false);
  const [, setTick] = useState(0);

  // Browser-Notifications für SL/TP Alerts
  useEffect(() => {
    if (!data?.positions?.open) return;
    const alerts = data.positions.open.filter(p => p.alert);
    if (alerts.length === 0) return;

    if (Notification.permission === "default") {
      Notification.requestPermission();
    }

    if (Notification.permission === "granted") {
      alerts.forEach(p => {
        const tag = `alert-${p.symbol}-${p.alert}`;
        if (p.alert === "STOP_LOSS_NEAR") {
          new Notification(`⚠️ ${p.symbol} nahe Stop-Loss!`, {
            body: `Aktuell: €${p.current_price?.toFixed(2)} | SL: €${p.stop_loss?.toFixed(2)}`,
            tag,
            requireInteraction: true,
          });
        } else if (p.alert === "TAKE_PROFIT_NEAR") {
          new Notification(`✅ ${p.symbol} nahe Take-Profit!`, {
            body: `Aktuell: €${p.current_price?.toFixed(2)} | TP: €${p.take_profit?.toFixed(2)}`,
            tag,
          });
        }
      });
    }
  }, [data?.positions?.open]);

  // Timer tickt jede 10s damit "vor Xs" live zählt
  useEffect(() => {
    const timer = setInterval(() => setTick(t => t + 1), 10000);
    return () => clearInterval(timer);
  }, []);

  // Update timestamp wenn neue Daten kommen
  useEffect(() => { if (data) setLastUpdate(new Date()); }, [data]);

  const handleRefresh = async () => {
    setRefreshing(true);
    await refetch();
    setLastUpdate(new Date());
    setRefreshing(false);
  };

  if (loading || !data) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <div className="w-8 h-8 border-2 border-accent/30 border-t-accent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-ink-tertiary">Lade Trading Desk...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="card border-loss/20 bg-loss-bg/30 text-center max-w-md">
          <p className="text-loss font-semibold mb-2">Verbindung fehlgeschlagen</p>
          <p className="text-sm text-ink-secondary mb-4">Backend nicht erreichbar. Läuft Docker?</p>
          <button onClick={() => window.location.reload()} className="btn-primary">Erneut versuchen</button>
        </div>
      </div>
    );
  }

  const a = AMPEL[data.macro.ampel];
  const hasBuys = data.signals.buys.length > 0;
  const hasSells = data.signals.sells.length > 0;

  const secondsAgo = Math.floor((Date.now() - lastUpdate.getTime()) / 1000);
  const timeLabel = secondsAgo < 5 ? "gerade eben" : secondsAgo < 60 ? `vor ${secondsAgo}s` : `vor ${Math.floor(secondsAgo / 60)}min`;

  return (
    <div className="space-y-6">
      {/* === STATUS BAR === */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5">
            <div className="w-1.5 h-1.5 rounded-full bg-gain animate-pulse" />
            <span className="text-[11px] font-medium text-gain">LIVE</span>
          </div>
          <span className="text-[11px] text-ink-faint">
            Aktualisiert {timeLabel} · Auto-Refresh 60s · Kurse via yfinance/Alpha Vantage
          </span>
          {typeof Notification !== "undefined" && Notification.permission !== "granted" && (
            <button onClick={() => Notification.requestPermission()} className="text-[10px] text-warn hover:text-warn/80">
              Benachrichtigungen aktivieren
            </button>
          )}
        </div>
        <button
          onClick={handleRefresh}
          disabled={refreshing}
          className="flex items-center gap-1.5 text-[11px] font-medium text-ink-secondary hover:text-accent bg-surface-muted hover:bg-accent-light border border-border rounded-lg px-3 py-1.5 transition-all active:scale-[0.97] disabled:opacity-50"
        >
          <svg className={`w-3.5 h-3.5 ${refreshing ? "animate-spin" : ""}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          {refreshing ? "Lade..." : "Aktualisieren"}
        </button>
      </div>

      {/* === MORNING BRIEFING === */}
      <div className={`card border ${a.bg}`}>
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-3">
            <div className={`w-2.5 h-2.5 rounded-full ${a.dot} animate-pulse`} />
            <h1 className="text-base font-bold text-ink">Morning Briefing</h1>
            <span className={`text-xs font-bold ${a.text}`}>{a.label}</span>
          </div>
          <span className="text-xs text-ink-tertiary">
            {new Date().toLocaleDateString("de-DE", { weekday: "short", day: "numeric", month: "short" })}
            {" · "}{data.regime.message}
          </span>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-1">
          {data.briefing.map((point) => (
            <p key={point} className="text-sm text-ink-secondary py-0.5">{point}</p>
          ))}
        </div>
      </div>

      {/* === OFFENE POSITIONEN === */}
      <OpenPositions positions={data.positions.open} unrealized_total={data.positions.unrealized_total} realized_total={data.positions.realized_total} win_rate={data.positions.win_rate} />

      {/* === KAUF-SIGNALE === */}
      {hasBuys && (
        <div>
          <h2 className="section-label text-gain mb-3">Kaufen — Aktive BUY-Signale</h2>
          <div className="space-y-4">{data.signals.buys.map((s) => <TradeCard key={s.symbol} s={s} type="buy" />)}</div>
        </div>
      )}

      {/* === BEOBACHTEN === */}
      {data.signals.watch.length > 0 && (
        <div>
          <h2 className="section-label text-accent mb-3">Beobachten — Nahe am Kaufsignal ({data.signals.watch.length} Titel)</h2>
          <div className="space-y-4">{data.signals.watch.map((s) => <TradeCard key={s.symbol} s={s} type="watch" />)}</div>
        </div>
      )}

      {/* === SELL === */}
      {hasSells && (
        <div>
          <h2 className="section-label text-loss mb-3">Verkaufen / Meiden ({data.signals.sells.length})</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {data.signals.sells.map((s) => (
              <div key={s.symbol} className="border border-loss/10 bg-loss-bg/30 rounded-2xl p-4 shadow-card">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <a href={`https://finance.yahoo.com/quote/${s.symbol}`} target="_blank" rel="noopener noreferrer" className="font-bold text-ink hover:text-accent transition-colors">{s.symbol}</a>
                    <SignalBadge type="SELL" />
                  </div>
                  <span className="text-loss font-bold">{s.confidence.toFixed(0)}%</span>
                </div>
                <p className="text-xs text-ink-secondary mb-2">{s.reasoning}</p>
                <div className="flex gap-4 text-xs text-ink-tertiary font-mono">
                  <span>€{s.entry_price}</span><span>SL €{s.stop_loss}</span><span>TP €{s.take_profit}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* === KEIN SIGNAL === */}
      {!hasBuys && data.signals.watch.length === 0 && (
        <div className="card border-warn/20 bg-warn-bg/30 text-center py-8">
          <p className="text-lg font-bold text-warn mb-2">Keine aktiven BUY-Signale</p>
          <p className="text-sm text-ink-secondary">{data.signals.hold} Titel auf HOLD, {data.signals.sell} auf SELL. Cash-Quote halten.</p>
        </div>
      )}

      {/* === HEBELPRODUKTE === */}
      {data.products.leveraged.length > 0 && (
        <div className="card border-leverage/20 bg-leverage-bg/50">
          <div className="flex items-center justify-between mb-1">
            <div className="flex items-center gap-2">
              <h2 className="section-label text-leverage">Hebelprodukte</h2>
            </div>
            <span className="text-[10px] bg-leverage-light text-leverage px-2 py-0.5 rounded-lg font-semibold">MAX. 1% RISIKO</span>
          </div>
          <div className="bg-leverage-light/50 border border-leverage/10 rounded-xl p-3 mb-4 text-xs text-leverage/80">
            <p className="font-semibold mb-1">HOHES VERLUSTRISIKO — Leveraged ETFs nur für kurzfristige Trades (&lt;5 Tage).</p>
            <p className="text-leverage/60">Volatility Decay: Langfristig verlieren Hebelprodukte an Wert. Totalverlust möglich.</p>
          </div>
          <div className="space-y-3">
            {data.products.leveraged.map((s) => {
              const p = s.product;
              return (
                <div key={s.symbol} className="border border-leverage/10 rounded-xl p-4 bg-surface">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <a href={`https://finance.yahoo.com/quote/${s.symbol}`} target="_blank" rel="noopener noreferrer" className="text-base font-bold text-ink hover:text-accent transition-colors">{s.symbol}</a>
                        {p && <span className="text-[10px] bg-leverage-light text-leverage px-2 py-0.5 rounded-lg font-semibold">{p.leverage}x {p.direction}</span>}
                        <SignalBadge type={s.signal_type} />
                        <span className="text-xs text-ink-tertiary">{p?.name || s.name}</span>
                      </div>
                      <div className="mb-2"><ConfidenceBar value={s.confidence} /></div>
                      <p className="text-xs text-ink-secondary">{s.reasoning}</p>
                    </div>
                    <div className="text-right ml-6 shrink-0">
                      <div className="grid grid-cols-3 gap-3 text-center text-sm mb-2">
                        <div><div className="text-[9px] text-ink-tertiary">Entry</div><div className="font-mono font-semibold text-ink">€{s.entry_price}</div></div>
                        <div><div className="text-[9px] text-loss">SL</div><div className="font-mono font-semibold text-loss">€{s.stop_loss}</div></div>
                        <div><div className="text-[9px] text-gain">TP</div><div className="font-mono font-semibold text-gain">€{s.take_profit}</div></div>
                      </div>
                      <div className="text-[10px] text-ink-tertiary mb-2">
                        {s.position_size} Stk · Max-Loss <span className="text-loss font-semibold">€{s.max_loss.toLocaleString()}</span>
                        {p && p.leverage > 1 && <> · Exposure <span className="text-leverage font-semibold">€{(s.effective_exposure || 0).toLocaleString()}</span></>}
                      </div>
                      <button onClick={() => {
                        api.journal.create({ symbol: s.symbol, trade_date: new Date().toISOString().split("T")[0], direction: p?.direction === "SHORT" ? "SHORT" : "LONG", entry_price: s.entry_price, position_size: s.position_size, stop_loss: s.stop_loss, take_profit: s.take_profit, setup_type: `Hebel ${p?.leverage}x · ${s.confidence.toFixed(0)}%`, notes: s.reasoning }).then(() => {
                          if (confirm(`✅ Trade im Journal geloggt!\n\n${s.position_size}x ${s.symbol} @ ${s.currency_symbol || "€"}${s.entry_price}\n\nJetzt bei deinem Broker ausführen?\n→ OK öffnet Yahoo Finance für ${s.symbol}`)) {
                            window.open(`https://finance.yahoo.com/quote/${s.symbol}`, "_blank");
                          }
                          window.location.reload();
                        });
                      }} className="bg-leverage text-white hover:bg-leverage/90 font-semibold text-xs px-3 py-1.5 rounded-xl transition-all active:scale-[0.98]">Ins Journal eintragen</button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* === CRYPTO + ROHSTOFFE === */}
      {(data.products.crypto.length > 0 || data.products.commodities.length > 0) && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {data.products.crypto.length > 0 && (
            <div className="card">
              <h2 className="section-label mb-3">Crypto ETFs</h2>
              {data.products.crypto.map((s) => (
                <div key={s.symbol} className="flex items-center justify-between py-2 border-b border-border/50 last:border-0">
                  <div>
                    <a href={`https://finance.yahoo.com/quote/${s.symbol}`} target="_blank" rel="noopener noreferrer" className="font-semibold text-ink hover:text-accent transition-colors">{s.symbol}</a>
                    <span className="text-xs text-ink-tertiary ml-2">{s.product?.name || s.name}</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="font-mono text-sm text-ink-secondary">€{s.entry_price}</span>
                    <SignalBadge type={s.signal_type} />
                    <span className="text-sm font-semibold text-ink">{s.confidence.toFixed(0)}%</span>
                  </div>
                </div>
              ))}
            </div>
          )}
          {data.products.commodities.length > 0 && (
            <div className="card">
              <h2 className="section-label mb-3">Rohstoffe</h2>
              {data.products.commodities.map((s) => (
                <div key={s.symbol} className="flex items-center justify-between py-2 border-b border-border/50 last:border-0">
                  <div>
                    <a href={`https://finance.yahoo.com/quote/${s.symbol}`} target="_blank" rel="noopener noreferrer" className="font-semibold text-ink hover:text-accent transition-colors">{s.symbol}</a>
                    <span className="text-xs text-ink-tertiary ml-2">{s.product?.name || s.name}</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="font-mono text-sm text-ink-secondary">€{s.entry_price}</span>
                    <SignalBadge type={s.signal_type} />
                    <span className="text-sm font-semibold text-ink">{s.confidence.toFixed(0)}%</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* === MARKTÜBERBLICK === */}
      <MarketOverview indices={data.indices} sectors={data.sectors} movers={data.movers} macro={data.macro.indicators} />

      <p className="text-center text-[10px] text-ink-faint pb-4">
        Keine Anlageberatung · Algorithmische Signale · Max. 2% Risiko pro Trade · Eigene Recherche erforderlich
      </p>
    </div>
  );
}
