import { useState } from "react";
import { useFetch } from "@/hooks/useFetch";
import { api } from "@/services/api";

interface DiscoverySuggestion {
  symbol: string;
  name: string | null;
  sector: string | null;
  score: number;
  scores: { hedge_fund: number; technical: number; sector: number };
  source: string;
  reason: string;
  fund_count: number | null;
  fund_names: string[] | null;
  current_price: number | null;
  rsi: number | null;
}

interface DiscoveryResponse {
  count: number;
  updated_at: string | null;
  suggestions: DiscoverySuggestion[];
}

const SOURCE_LABELS: Record<string, { label: string; color: string }> = {
  combined: { label: "Kombiniert", color: "bg-accent/10 text-accent border-accent/20" },
  hedge_fund_cluster: { label: "Hedge Funds", color: "bg-purple-50 text-purple-700 border-purple-200" },
  sector_momentum: { label: "Sektor-Momentum", color: "bg-gain-bg text-gain border-gain-light" },
  technical_setup: { label: "Technisch", color: "bg-warn-bg text-warn border-warn-light" },
};

function ScoreBar({ value, label, color }: { value: number; label: string; color: string }) {
  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <span className="text-[10px] text-ink-tertiary uppercase tracking-wider">{label}</span>
        <span className="text-[10px] font-mono font-semibold text-ink-secondary">{value.toFixed(0)}</span>
      </div>
      <div className="h-1.5 bg-surface-muted rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${Math.min(100, value)}%` }} />
      </div>
    </div>
  );
}

function DiscoveryCard({ s, onAdd }: { s: DiscoverySuggestion; onAdd: (sym: string) => void }) {
  const [adding, setAdding] = useState(false);
  const [added, setAdded] = useState(false);
  const src = SOURCE_LABELS[s.source] || SOURCE_LABELS.combined;

  const handleAdd = async () => {
    setAdding(true);
    try {
      await onAdd(s.symbol);
      setAdded(true);
    } catch {
      alert(`Fehler: ${s.symbol} konnte nicht hinzugefuegt werden`);
    }
    setAdding(false);
  };

  return (
    <div className="border border-border rounded-2xl p-5 shadow-card bg-surface hover:shadow-card-hover transition-shadow">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2.5">
          <a
            href={`https://finance.yahoo.com/quote/${s.symbol}`}
            target="_blank"
            rel="noopener noreferrer"
            className="text-lg font-bold text-ink hover:text-accent transition-colors"
          >
            {s.symbol}
          </a>
          <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-lg border ${src.color}`}>
            {src.label}
          </span>
          {s.sector && (
            <span className="text-[10px] bg-surface-muted text-ink-tertiary px-2 py-0.5 rounded-lg">
              {s.sector}
            </span>
          )}
        </div>
        <div className="text-right">
          <div className="text-[10px] text-ink-tertiary uppercase tracking-wider">Score</div>
          <div className={`text-xl font-bold ${
            s.score >= 70 ? "text-gain" : s.score >= 55 ? "text-accent" : "text-ink-secondary"
          }`}>
            {s.score.toFixed(0)}
          </div>
        </div>
      </div>

      {s.name && <p className="text-sm text-ink-tertiary mb-2">{s.name}</p>}

      <div className="bg-surface-muted rounded-xl p-4 mb-3 border border-border/50">
        <div className="grid grid-cols-3 gap-4">
          <ScoreBar value={s.scores.hedge_fund} label="Hedge Funds" color="bg-purple-500" />
          <ScoreBar value={s.scores.technical} label="Technisch" color="bg-accent" />
          <ScoreBar value={s.scores.sector} label="Sektor" color="bg-gain" />
        </div>
        <div className="border-t border-border/50 mt-3 pt-3 grid grid-cols-3 gap-4 text-center text-sm">
          {s.current_price && (
            <div>
              <div className="text-[10px] text-ink-tertiary">Kurs</div>
              <div className="font-mono font-semibold text-ink">${s.current_price.toFixed(2)}</div>
            </div>
          )}
          {s.rsi != null && (
            <div>
              <div className="text-[10px] text-ink-tertiary">RSI</div>
              <div className={`font-mono font-semibold ${
                s.rsi < 30 ? "text-gain" : s.rsi > 70 ? "text-loss" : "text-ink"
              }`}>
                {s.rsi.toFixed(1)}
              </div>
            </div>
          )}
          {s.fund_count != null && (
            <div>
              <div className="text-[10px] text-ink-tertiary">Fonds</div>
              <div className="font-mono font-semibold text-purple-700">{s.fund_count}</div>
            </div>
          )}
        </div>
      </div>

      <p className="text-sm text-ink-secondary mb-3 leading-relaxed">{s.reason}</p>

      {s.fund_names && s.fund_names.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mb-3">
          {s.fund_names.map((name) => (
            <span key={name} className="text-[10px] bg-purple-50 text-purple-600 px-2 py-0.5 rounded-md border border-purple-100">
              {name}
            </span>
          ))}
        </div>
      )}

      <div className="flex items-center justify-between">
        <a
          href={`/watchlist?symbol=${s.symbol}`}
          className="text-[11px] text-ink-tertiary hover:text-accent transition-colors"
        >
          Chart ansehen
        </a>
        {added ? (
          <span className="text-sm font-semibold text-gain">Hinzugefuegt</span>
        ) : (
          <button
            onClick={handleAdd}
            disabled={adding}
            className="bg-accent text-white hover:bg-accent-hover font-semibold text-sm px-4 py-2 rounded-xl transition-all active:scale-[0.98] disabled:opacity-50"
          >
            {adding ? "..." : "+ Zur Watchlist"}
          </button>
        )}
      </div>
    </div>
  );
}

export function Discovery() {
  const [filter, setFilter] = useState<string>("all");
  const params = filter !== "all" ? `source=${filter}` : "";
  const { data, loading, error, refetch } = useFetch<DiscoveryResponse>(
    () => api.discovery.suggestions(params) as Promise<DiscoveryResponse>,
    [filter],
  );

  const handleAdd = async (symbol: string) => {
    await api.discovery.addToWatchlist(symbol);
    refetch();
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-ink">Discovery</h1>
          <p className="text-ink-tertiary text-sm mt-1">
            Proaktive Vorschlaege basierend auf Hedge-Fund-Clustering, Sektor-Momentum und technischen Setups
          </p>
        </div>
        <div className="flex items-center gap-3">
          {data?.updated_at && (
            <span className="text-[10px] text-ink-faint">
              Stand: {new Date(data.updated_at).toLocaleString("de-DE")}
            </span>
          )}
          <span className="text-sm font-semibold text-ink-secondary">{data?.count || 0} Vorschlaege</span>
        </div>
      </div>

      <div className="flex gap-2">
        {[
          { key: "all", label: "Alle" },
          { key: "combined", label: "Kombiniert" },
          { key: "hedge_fund_cluster", label: "Hedge Funds" },
          { key: "sector_momentum", label: "Sektor-Momentum" },
          { key: "technical_setup", label: "Technisch" },
        ].map((f) => (
          <button
            key={f.key}
            onClick={() => setFilter(f.key)}
            className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
              filter === f.key
                ? "bg-accent text-white"
                : "bg-surface-muted text-ink-secondary hover:text-ink hover:bg-surface-muted/80 border border-border"
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-20">
          <div className="w-6 h-6 border-2 border-accent/30 border-t-accent rounded-full animate-spin" />
          <span className="ml-3 text-sm text-ink-tertiary">Lade Vorschlaege...</span>
        </div>
      ) : error ? (
        <div className="card border-loss/20 bg-loss-bg/30 text-center py-8">
          <p className="text-loss font-semibold mb-2">Fehler beim Laden</p>
          <p className="text-sm text-ink-secondary">{error}</p>
        </div>
      ) : data && data.suggestions.length > 0 ? (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {data.suggestions.map((s) => (
            <DiscoveryCard key={s.symbol} s={s} onAdd={handleAdd} />
          ))}
        </div>
      ) : (
        <div className="card text-center py-12">
          <p className="text-ink-tertiary text-lg mb-2">Keine Vorschlaege verfuegbar</p>
          <p className="text-ink-faint text-sm">
            Die Discovery-Pipeline laeuft taeglich um 05:00 UTC. Stelle sicher, dass Hedge-Fund-Daten und OHLCV-Daten vorhanden sind.
          </p>
        </div>
      )}
    </div>
  );
}
