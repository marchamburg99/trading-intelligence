import { useState } from "react";
import { useFetch } from "@/hooks/useFetch";
import { api } from "@/services/api";
import { SignalBadge } from "@/components/SignalBadge";
import { ConfidenceBar } from "@/components/ConfidenceBar";
import type { Signal, SignalType } from "@/types";

export function Signals() {
  const [filter, setFilter] = useState<SignalType | "">("");
  const [minConf, setMinConf] = useState(0);

  const params = new URLSearchParams();
  if (filter) params.set("signal_type", filter);
  if (minConf > 0) params.set("min_confidence", String(minConf));

  const { data: signals, loading } = useFetch<Signal[]>(
    () => api.signals.list(params.toString()) as Promise<Signal[]>,
    [filter, minConf]
  );

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Signal-Feed</h1>
        <p className="text-ink-tertiary mt-1">Alle aktiven Trading-Signale</p>
      </div>

      {/* Filters */}
      <div className="flex gap-4 items-center">
        <select
          value={filter}
          onChange={(e) => setFilter(e.target.value as SignalType | "")}
          className="input"
        >
          <option value="">Alle Signale</option>
          <option value="BUY">BUY</option>
          <option value="SELL">SELL</option>
          <option value="HOLD">HOLD</option>
          <option value="AVOID">AVOID</option>
        </select>
        <label className="flex items-center gap-2">
          <span className="text-sm text-ink-tertiary">Min. Konfidenz:</span>
          <input
            type="range"
            min={0}
            max={100}
            value={minConf}
            onChange={(e) => setMinConf(Number(e.target.value))}
            className="w-32"
          />
          <span className="text-sm font-mono w-10">{minConf}%</span>
        </label>
      </div>

      {/* Signal Cards */}
      {loading ? (
        <p className="text-ink-tertiary">Lade Signale...</p>
      ) : signals && signals.length > 0 ? (
        <div className="space-y-4">
          {signals.map((s) => (
            <div key={s.id} className="card">
              <div className="flex items-start justify-between">
                <div>
                  <div className="flex items-center gap-3">
                    <h3 className="text-lg font-semibold">{s.symbol}</h3>
                    <SignalBadge type={s.signal_type} />
                    <span className="text-xs text-ink-tertiary">{s.sector}</span>
                  </div>
                  <p className="text-sm text-ink-tertiary mt-1">{s.name}</p>
                </div>
                <span className="text-xs text-ink-tertiary">{s.date}</span>
              </div>

              <div className="mt-4">
                <ConfidenceBar value={s.confidence} />
              </div>

              <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mt-4 text-sm">
                <div>
                  <p className="text-ink-tertiary">Einstieg</p>
                  <p className="font-semibold font-mono">${s.entry_price?.toFixed(2) ?? "—"}</p>
                </div>
                <div>
                  <p className="text-ink-tertiary">Stop-Loss</p>
                  <p className="font-semibold font-mono text-loss">${s.stop_loss?.toFixed(2) ?? "—"}</p>
                </div>
                <div>
                  <p className="text-ink-tertiary">Take-Profit</p>
                  <p className="font-semibold font-mono text-gain">${s.take_profit?.toFixed(2) ?? "—"}</p>
                </div>
                <div>
                  <p className="text-ink-tertiary">R:R</p>
                  <p className="font-semibold font-mono">1:{s.risk_reward_ratio?.toFixed(1)}</p>
                </div>
                <div>
                  <p className="text-ink-tertiary">Haltedauer</p>
                  <p className="font-semibold">{s.expected_hold_days} Tage</p>
                </div>
              </div>

              <p className="text-sm text-ink-tertiary mt-4 border-t border-border pt-3">
                {s.reasoning}
              </p>
            </div>
          ))}
        </div>
      ) : (
        <p className="text-ink-tertiary">Keine Signale gefunden.</p>
      )}
    </div>
  );
}
