interface Index { symbol: string; name: string; price: number; change_1d: number; change_20d: number }
interface Sector { symbol: string; name: string; change_1d: number; change_20d: number }
interface Mover { symbol: string; name: string; price: number; change: number }
interface MacroInd { value: number; status: string; date: string }

function Chg({ value }: { value: number }) {
  const c = value > 0 ? "text-gain" : value < 0 ? "text-loss" : "text-ink-tertiary";
  return <span className={`font-mono text-sm font-semibold ${c}`}>{value > 0 ? "+" : ""}{value.toFixed(2)}%</span>;
}

export function MarketOverview({
  indices, sectors, movers, macro,
}: {
  indices: Index[];
  sectors: Sector[];
  movers: { gainers: Mover[]; losers: Mover[] };
  macro: Record<string, MacroInd>;
}) {
  return (
    <div className="grid grid-cols-12 gap-4">
      <div className="col-span-5 card">
        <h2 className="section-label mb-3">Indizes</h2>
        {indices.map((idx) => (
          <div key={idx.symbol} className="flex items-center justify-between py-2 border-b border-border/50 last:border-0 text-sm">
            <span className="font-medium text-ink w-28">{idx.name}</span>
            <span className="font-mono text-ink-secondary">${idx.price.toLocaleString()}</span>
            <Chg value={idx.change_1d} />
            <span className="text-[10px] text-ink-faint w-14 text-right">{idx.change_20d > 0 ? "+" : ""}{idx.change_20d}% 20d</span>
          </div>
        ))}
      </div>

      <div className="col-span-4 card">
        <h2 className="section-label mb-3">Sektor-Rotation 20d</h2>
        {sectors.map((s) => (
          <div key={s.symbol} className="flex items-center justify-between py-1.5 text-sm">
            <span className="w-20 text-ink-secondary text-[13px]">{s.name}</span>
            <div className="flex-1 mx-3">
              <div className="h-1.5 bg-surface-muted rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full ${s.change_20d >= 0 ? "bg-gain/40" : "bg-loss/40"}`}
                  style={{ width: `${Math.min(100, Math.abs(s.change_20d) * 8)}%`, marginLeft: s.change_20d < 0 ? "auto" : undefined }}
                />
              </div>
            </div>
            <Chg value={s.change_20d} />
          </div>
        ))}
      </div>

      <div className="col-span-3 space-y-4">
        <div className="card">
          <h2 className="section-label mb-2">Makro</h2>
          {Object.entries(macro).map(([key, ind]) => (
            <div key={key} className="flex items-center justify-between py-1 text-sm">
              <div className="flex items-center gap-1.5">
                <div className={`w-1.5 h-1.5 rounded-full ${ind.status === "GREEN" ? "bg-gain" : ind.status === "RED" ? "bg-loss" : "bg-warn"}`} />
                <span className="text-xs text-ink-secondary">{key}</span>
              </div>
              <span className="font-mono text-xs text-ink">{ind.value}</span>
            </div>
          ))}
        </div>
        <div className="card">
          <h2 className="section-label mb-2 text-gain">Gewinner</h2>
          {movers.gainers.map((m) => (
            <div key={m.symbol} className="flex justify-between text-sm py-0.5">
              <span className="font-medium text-ink">{m.symbol}</span>
              <Chg value={m.change} />
            </div>
          ))}
        </div>
        <div className="card">
          <h2 className="section-label mb-2 text-loss">Verlierer</h2>
          {movers.losers.map((m) => (
            <div key={m.symbol} className="flex justify-between text-sm py-0.5">
              <span className="font-medium text-ink">{m.symbol}</span>
              <Chg value={m.change} />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
