import { useFetch } from "@/hooks/useFetch";
import { api } from "@/services/api";
import type { HedgeFundFiling } from "@/types";

interface ClusterSignal {
  symbol: string;
  fund_count: number;
  total_value: number | null;
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
                <tr key={f.id} className="border-b border-border/50 hover:bg-surface-muted/50">
                  <td className="py-3 font-semibold">{f.fund_name}</td>
                  <td className="py-3 text-ink-tertiary">{f.filing_date}</td>
                  <td className="py-3 font-mono">
                    {f.total_value ? `€${(f.total_value / 1e6).toFixed(0)}M` : "—"}
                  </td>
                  <td className="py-3 font-mono">{f.position_count}</td>
                </tr>
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
