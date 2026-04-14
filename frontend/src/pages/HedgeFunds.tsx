import { useState } from "react";
import { useFetch } from "@/hooks/useFetch";
import { api } from "@/services/api";
import type { HedgeFundFiling } from "@/types";

interface ClusterSignal {
  symbol: string;
  fund_count: number;
  total_value: number | null;
}

interface Position {
  symbol: string;
  company_name: string;
  value: number | null;
  shares: number | null;
  change: number | null;
}

export function HedgeFunds() {
  const { data: filings, loading } = useFetch<HedgeFundFiling[]>(
    () => api.hedgefunds.filings() as Promise<HedgeFundFiling[]>,
    []
  );
  const { data: clusters } = useFetch<ClusterSignal[]>(
    () => api.hedgefunds.clusters() as Promise<ClusterSignal[]>,
    []
  );
  const [selectedFilingId, setSelectedFilingId] = useState<number | null>(null);
  const [positions, setPositions] = useState<Position[]>([]);
  const [loadingPositions, setLoadingPositions] = useState(false);

  const handleFilingClick = async (filingId: number) => {
    if (selectedFilingId === filingId) {
      setSelectedFilingId(null);
      setPositions([]);
      return;
    }
    setSelectedFilingId(filingId);
    setLoadingPositions(true);
    try {
      const data = (await api.hedgefunds.positions(filingId)) as Position[];
      setPositions(data.slice(0, 20));
    } catch {
      setPositions([]);
    }
    setLoadingPositions(false);
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Hedge Fund Tracker</h1>
        <p className="text-ink-tertiary mt-1">13F-Filings & institutionelle Cluster-Signale</p>
      </div>

      {/* Cluster Signals */}
      {clusters && clusters.length > 0 && (
        <div className="card">
          <h2 className="text-lg font-semibold mb-4">Cluster-Signale (3+ Fonds)</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {clusters.map((c) => (
              <div key={c.symbol} className="bg-gain-bg border border-gain/30 rounded-xl p-4">
                <p className="font-bold text-lg">{c.symbol}</p>
                <p className="text-sm text-gain">{c.fund_count} Fonds kaufen</p>
                {c.total_value && (
                  <p className="text-xs text-ink-tertiary">€{(c.total_value / 1000).toFixed(0)}M</p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recent Filings */}
      <div className="card">
        <h2 className="text-lg font-semibold mb-4">Neueste 13F-Filings</h2>
        {loading ? (
          <p className="text-ink-tertiary">Lade...</p>
        ) : filings && filings.length > 0 ? (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs text-ink-tertiary border-b border-border">
                <th className="pb-3">Fund</th>
                <th className="pb-3">Filing-Datum</th>
                <th className="pb-3">Gesamtwert</th>
                <th className="pb-3">Positionen</th>
              </tr>
            </thead>
            <tbody>
              {filings.map((f) => (
                <>
                  <tr
                    key={f.id}
                    onClick={() => handleFilingClick(f.id)}
                    className="border-b border-border/50 hover:bg-surface-muted/50 cursor-pointer"
                  >
                    <td className="py-3 font-semibold">{f.fund_name}</td>
                    <td className="py-3 text-ink-tertiary">{f.filing_date}</td>
                    <td className="py-3 font-mono">
                      {f.total_value ? `€${(f.total_value / 1e6).toFixed(0)}M` : "—"}
                    </td>
                    <td className="py-3 font-mono">{f.position_count}</td>
                  </tr>
                  {selectedFilingId === f.id && (
                    <tr key={`pos-${f.id}`}>
                      <td colSpan={4} className="p-0">
                        <div className="bg-surface-muted/50 border-t border-border/30 px-4 py-3">
                          {loadingPositions ? (
                            <p className="text-sm text-ink-tertiary">Lade Positionen...</p>
                          ) : positions.length > 0 ? (
                            <>
                              <p className="text-xs text-ink-tertiary mb-2 font-semibold">Top {positions.length} Positionen</p>
                              <table className="w-full text-xs">
                                <thead>
                                  <tr className="text-left text-ink-tertiary border-b border-border/50">
                                    <th className="pb-2">Symbol</th>
                                    <th className="pb-2">Unternehmen</th>
                                    <th className="pb-2 text-right">Wert ($)</th>
                                    <th className="pb-2 text-right">Shares</th>
                                    <th className="pb-2 text-right">Aenderung</th>
                                  </tr>
                                </thead>
                                <tbody>
                                  {positions.map((p) => (
                                    <tr key={p.symbol} className="border-b border-border/30">
                                      <td className="py-1.5">
                                        <a
                                          href={`https://finance.yahoo.com/quote/${p.symbol}`}
                                          target="_blank"
                                          rel="noopener noreferrer"
                                          className="font-semibold text-ink hover:text-accent transition-colors"
                                        >
                                          {p.symbol}
                                        </a>
                                      </td>
                                      <td className="py-1.5 text-ink-tertiary">{p.company_name}</td>
                                      <td className="py-1.5 text-right font-mono">
                                        {p.value ? `$${(p.value / 1e6).toFixed(1)}M` : "—"}
                                      </td>
                                      <td className="py-1.5 text-right font-mono">
                                        {p.shares ? p.shares.toLocaleString() : "—"}
                                      </td>
                                      <td className="py-1.5 text-right font-mono">
                                        {p.change != null ? (
                                          <span className={p.change > 0 ? "text-gain" : p.change < 0 ? "text-loss" : ""}>
                                            {p.change > 0 ? "+" : ""}{p.change.toFixed(1)}%
                                          </span>
                                        ) : "—"}
                                      </td>
                                    </tr>
                                  ))}
                                </tbody>
                              </table>
                            </>
                          ) : (
                            <p className="text-sm text-ink-tertiary">Keine Positionen gefunden.</p>
                          )}
                        </div>
                      </td>
                    </tr>
                  )}
                </>
              ))}
            </tbody>
          </table>
        ) : (
          <p className="text-ink-tertiary">Keine Filings vorhanden.</p>
        )}
      </div>
    </div>
  );
}
