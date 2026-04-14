import { useState } from "react";
import { api } from "@/services/api";

interface AnalysisResult {
  symbol: string;
  signal_type: string;
  confidence: number;
  entry_price: number;
  stop_loss: number;
  take_profit: number;
  risk_reward_ratio: number;
  risk_rating: number;
  expected_hold_days: number;
  reasoning: string;
  key_risks: string[];
  technical_summary: string;
  macro_context: string;
  model: string;
  error?: string;
}

export function AIAnalysis() {
  const [symbol, setSymbol] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleAnalyze = async () => {
    if (!symbol.trim()) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const data = await api.analyze.run({ symbol: symbol.trim().toUpperCase() }) as AnalysisResult;
      if (data.error) {
        setError(data.error);
      } else {
        setResult(data);
      }
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Analyse fehlgeschlagen";
      setError(msg);
    }
    setLoading(false);
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold">KI-Analyse</h1>
        <p className="text-ink-tertiary text-sm">Claude AI analysiert einen Ticker mit allen verfuegbaren Daten</p>
      </div>

      <div className="card">
        <div className="flex gap-3">
          <label className="flex-1 block">
            <span className="text-[10px] text-ink-tertiary block mb-1">Ticker-Symbol</span>
            <input
              value={symbol}
              onChange={(e) => setSymbol(e.target.value.toUpperCase())}
              onKeyDown={(e) => e.key === "Enter" && handleAnalyze()}
              placeholder="z.B. AAPL, MSFT, TSLA"
              className="input font-mono"
            />
          </label>
          <div className="flex items-end">
            <button onClick={handleAnalyze} disabled={loading || !symbol.trim()} className="btn-primary whitespace-nowrap">
              {loading ? "Analysiert..." : "Analyse starten"}
            </button>
          </div>
        </div>
        {loading && (
          <div className="mt-4 flex items-center gap-3">
            <div className="w-5 h-5 border-2 border-accent/30 border-t-accent rounded-full animate-spin" />
            <span className="text-sm text-ink-tertiary">Claude analysiert {symbol}... (10-20 Sekunden)</span>
          </div>
        )}
        {error && (
          <div className="mt-4 bg-loss-bg border border-loss-light rounded-xl p-4">
            <p className="text-sm text-loss">{error}</p>
          </div>
        )}
      </div>

      {result && (
        <div className="space-y-4">
          <div className="card">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <a href={`https://finance.yahoo.com/quote/${result.symbol}`} target="_blank" rel="noopener noreferrer" className="text-2xl font-bold hover:text-accent transition-colors">{result.symbol}</a>
                <span className={`px-3 py-1 rounded-xl text-sm font-bold ${
                  result.signal_type === "BUY" ? "bg-gain-bg text-gain border border-gain-light" :
                  result.signal_type === "SELL" ? "bg-loss-bg text-loss border border-loss-light" :
                  result.signal_type === "AVOID" ? "bg-warn-bg text-warn border border-warn-light" :
                  "bg-surface-muted text-ink-secondary border border-border"
                }`}>{result.signal_type}</span>
                <span className="text-lg font-bold text-accent">{result.confidence}%</span>
              </div>
              <span className="text-[10px] text-ink-faint">Powered by {result.model}</span>
            </div>

            <div className="bg-surface-muted rounded-xl p-4 mb-4">
              <div className="grid grid-cols-3 md:grid-cols-6 gap-4 text-center text-sm">
                <div><div className="text-[10px] text-ink-tertiary">Einstieg</div><div className="font-mono font-bold">${result.entry_price}</div></div>
                <div><div className="text-[10px] text-loss">Stop-Loss</div><div className="font-mono font-bold text-loss">${result.stop_loss}</div></div>
                <div><div className="text-[10px] text-gain">Take-Profit</div><div className="font-mono font-bold text-gain">${result.take_profit}</div></div>
                <div><div className="text-[10px] text-ink-tertiary">R:R</div><div className="font-mono font-bold">1:{result.risk_reward_ratio}</div></div>
                <div><div className="text-[10px] text-ink-tertiary">Risiko</div><div className="font-bold">{result.risk_rating}/5</div></div>
                <div><div className="text-[10px] text-ink-tertiary">Haltedauer</div><div className="font-bold">{result.expected_hold_days}d</div></div>
              </div>
            </div>

            <div className="space-y-4">
              <div>
                <h3 className="section-label mb-2">Begruendung</h3>
                <p className="text-sm text-ink-secondary leading-relaxed">{result.reasoning}</p>
              </div>
              {result.technical_summary && (
                <div>
                  <h3 className="section-label mb-2">Technische Analyse</h3>
                  <p className="text-sm text-ink-secondary leading-relaxed">{result.technical_summary}</p>
                </div>
              )}
              {result.macro_context && (
                <div>
                  <h3 className="section-label mb-2">Makro-Kontext</h3>
                  <p className="text-sm text-ink-secondary leading-relaxed">{result.macro_context}</p>
                </div>
              )}
              {result.key_risks && result.key_risks.length > 0 && (
                <div>
                  <h3 className="section-label mb-2 text-loss">Risiken</h3>
                  <ul className="space-y-1">
                    {result.key_risks.map((risk, i) => (
                      <li key={i} className="text-sm text-ink-secondary flex items-start gap-2">
                        <span className="text-loss mt-0.5">&#8226;</span>{risk}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
