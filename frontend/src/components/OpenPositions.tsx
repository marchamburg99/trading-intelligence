import { useState } from "react";

interface Position {
  id: number; symbol: string; direction: string; entry_price: number;
  current_price: number | null; stop_loss: number | null; take_profit: number | null;
  position_size: number; unrealized_pnl: number; unrealized_pct: number;
  trade_date: string; days_held: number; setup_type: string; alert: string | null;
}

function Pnl({ value, suffix = "" }: { value: number; suffix?: string }) {
  const c = value > 0 ? "text-gain" : value < 0 ? "text-loss" : "text-ink-tertiary";
  return <span className={`font-mono font-semibold ${c}`}>{value > 0 ? "+" : ""}{value.toFixed(2)}{suffix}</span>;
}

function CloseButton({ position }: { position: Position }) {
  const [closing, setClosing] = useState(false);

  const handleClose = async () => {
    setClosing(true);
    try {
      const quoteRes = await fetch(`/api/quotes/${position.symbol}`);
      const quote = await quoteRes.json();
      const currentPrice = quote.price ?? position.current_price;

      const input = prompt(
        `Position schließen?\n\n${position.symbol} ${position.direction}\n${position.position_size} Stk. @ Einstieg €${position.entry_price.toFixed(2)}\n\nAusstiegskurs:`,
        currentPrice?.toFixed(2) ?? "",
      );
      if (!input) { setClosing(false); return; }

      const exitPrice = parseFloat(input);
      if (isNaN(exitPrice) || exitPrice <= 0) { setClosing(false); return; }

      await fetch(`/api/journal/${position.id}/close`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ exit_price: exitPrice }),
      });
      window.location.reload();
    } catch {
      alert("Fehler beim Schließen der Position.");
      setClosing(false);
    }
  };

  return (
    <button
      onClick={handleClose}
      disabled={closing}
      className="text-[10px] bg-loss-bg text-loss hover:bg-loss hover:text-white px-2 py-1 rounded-lg font-semibold transition-all disabled:opacity-50"
    >
      {closing ? "..." : "Schließen"}
    </button>
  );
}

export function OpenPositions({
  positions, unrealized_total, realized_total, win_rate,
}: {
  positions: Position[];
  unrealized_total: number;
  realized_total: number;
  win_rate: number;
}) {
  if (positions.length === 0) return null;

  return (
    <div className="card">
      <div className="flex items-center justify-between mb-4">
        <h2 className="section-label">Offene Positionen</h2>
        <div className="flex items-center gap-4 text-sm">
          <span className="text-ink-tertiary">Unrealisiert:</span>
          <Pnl value={unrealized_total} />
          <span className="text-border">|</span>
          <span className="text-ink-tertiary">Realisiert:</span>
          <Pnl value={realized_total} />
          <span className="text-border">|</span>
          <span className="text-ink-tertiary">Win-Rate:</span>
          <span className="font-mono font-semibold text-ink">{win_rate}%</span>
        </div>
      </div>
      <table className="w-full text-sm">
        <thead>
          <tr className="text-[10px] uppercase tracking-wider text-ink-tertiary border-b border-border">
            <th className="pb-2 text-left">Symbol</th>
            <th className="pb-2 text-left">Richtung</th>
            <th className="pb-2 text-right">Einstieg</th>
            <th className="pb-2 text-right">Aktuell</th>
            <th className="pb-2 text-right">SL</th>
            <th className="pb-2 text-right">TP</th>
            <th className="pb-2 text-right">Stk.</th>
            <th className="pb-2 text-right">P&L</th>
            <th className="pb-2 text-right">%</th>
            <th className="pb-2 text-right">Tage</th>
            <th className="pb-2 text-center">Status</th>
            <th className="pb-2 text-center">Aktion</th>
          </tr>
        </thead>
        <tbody>
          {positions.map((p) => (
            <tr key={p.id} className={`border-b border-border/50 ${p.alert ? "bg-loss-bg/50" : ""}`}>
              <td className="py-2.5 font-semibold"><a href={`https://finance.yahoo.com/quote/${p.symbol}`} target="_blank" rel="noopener noreferrer" className="hover:text-accent transition-colors">{p.symbol}</a></td>
              <td className={`py-2.5 font-medium ${p.direction === "LONG" ? "text-gain" : "text-loss"}`}>{p.direction}</td>
              <td className="py-2.5 text-right font-mono text-ink-secondary">€{p.entry_price.toFixed(2)}</td>
              <td className="py-2.5 text-right font-mono font-semibold">{p.current_price ? `€${p.current_price.toFixed(2)}` : "—"}</td>
              <td className="py-2.5 text-right font-mono text-loss/50">{p.stop_loss ? `€${p.stop_loss.toFixed(2)}` : "—"}</td>
              <td className="py-2.5 text-right font-mono text-gain/50">{p.take_profit ? `€${p.take_profit.toFixed(2)}` : "—"}</td>
              <td className="py-2.5 text-right text-ink-secondary">{p.position_size}</td>
              <td className="py-2.5 text-right"><Pnl value={p.unrealized_pnl} /></td>
              <td className="py-2.5 text-right"><Pnl value={p.unrealized_pct} suffix="%" /></td>
              <td className="py-2.5 text-right text-ink-tertiary">{p.days_held}d</td>
              <td className="py-2.5 text-center">
                {p.alert === "STOP_LOSS_NEAR" && <span className="text-[10px] bg-loss-bg text-loss px-2 py-0.5 rounded-lg font-semibold animate-pulse">SL NAHE</span>}
                {p.alert === "TAKE_PROFIT_NEAR" && <span className="text-[10px] bg-gain-bg text-gain px-2 py-0.5 rounded-lg font-semibold">TP NAHE</span>}
                {!p.alert && <span className="text-[10px] text-ink-faint">OK</span>}
              </td>
              <td className="py-2.5 text-center"><CloseButton position={p} /></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
