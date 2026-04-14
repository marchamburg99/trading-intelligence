import { useState } from "react";
import { useSearchParams } from "react-router-dom";

export function Risk() {
  const [searchParams] = useSearchParams();

  const paramEntry = searchParams.get("entry_price");
  const paramStop = searchParams.get("stop_loss");
  const paramCapital = searchParams.get("capital");

  const [capital, setCapital] = useState(paramCapital ? Number(paramCapital) : 100000);
  const [riskPercent, setRiskPercent] = useState(2);
  const [entryPrice, setEntryPrice] = useState(paramEntry ? Number(paramEntry) : 0);
  const [stopLoss, setStopLoss] = useState(paramStop ? Number(paramStop) : 0);

  const riskAmount = capital * (riskPercent / 100);
  const riskPerShare = Math.abs(entryPrice - stopLoss);
  const positionSize = riskPerShare > 0 ? Math.floor(riskAmount / riskPerShare) : 0;
  const positionValue = positionSize * entryPrice;
  const portfolioPercent = capital > 0 ? (positionValue / capital) * 100 : 0;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Risiko-Rechner</h1>
        <p className="text-ink-tertiary mt-1">Position Sizing & Depot-Analyse</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Input */}
        <div className="card space-y-4">
          <h2 className="text-lg font-semibold">Position Sizing</h2>
          <label className="block">
            <span className="text-sm text-ink-tertiary block mb-1">Depot-Kapital (€)</span>
            <input
              type="number"
              value={capital}
              onChange={(e) => setCapital(Number(e.target.value))}
              className="input font-mono w-full"
            />
          </label>
          <label className="block">
            <span className="text-sm text-ink-tertiary block mb-1">Risiko pro Trade (%)</span>
            <input
              type="number"
              value={riskPercent}
              onChange={(e) => setRiskPercent(Number(e.target.value))}
              step={0.5}
              min={0.5}
              max={5}
              className="input font-mono w-full"
            />
          </label>
          <label className="block">
            <span className="text-sm text-ink-tertiary block mb-1">Einstiegspreis (€)</span>
            <input
              type="number"
              value={entryPrice || ""}
              onChange={(e) => setEntryPrice(Number(e.target.value))}
              step={0.01}
              className="input font-mono w-full"
            />
          </label>
          <label className="block">
            <span className="text-sm text-ink-tertiary block mb-1">Stop-Loss (€)</span>
            <input
              type="number"
              value={stopLoss || ""}
              onChange={(e) => setStopLoss(Number(e.target.value))}
              step={0.01}
              className="input font-mono w-full"
            />
          </label>
        </div>

        {/* Output */}
        <div className="space-y-4">
          <div className="card">
            <p className="text-sm text-ink-tertiary">Max. Risiko-Betrag</p>
            <p className="text-3xl font-bold font-mono text-loss">€{riskAmount.toFixed(2)}</p>
          </div>
          <div className="card">
            <p className="text-sm text-ink-tertiary">Risiko pro Aktie</p>
            <p className="text-3xl font-bold font-mono">€{riskPerShare.toFixed(2)}</p>
          </div>
          <div className="card">
            <p className="text-sm text-ink-tertiary">Position Size</p>
            <p className="text-3xl font-bold font-mono text-accent">{positionSize} Aktien</p>
          </div>
          <div className="card">
            <p className="text-sm text-ink-tertiary">Positionswert</p>
            <p className="text-3xl font-bold font-mono">€{positionValue.toFixed(2)}</p>
            <p className="text-sm text-ink-tertiary mt-1">{portfolioPercent.toFixed(1)}% des Depots</p>
          </div>
        </div>
      </div>
    </div>
  );
}
