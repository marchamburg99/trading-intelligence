import { useState } from "react";
import { api } from "@/services/api";

interface ScanResult {
  symbol: string;
  name: string;
  sector: string;
  rsi_14: number;
  macd: number;
  macd_signal: number;
  ema_200: number;
  atr_14: number;
}

export function Scanner() {
  const [rsiBellow, setRsiBelow] = useState<string>("");
  const [macdBullish, setMacdBullish] = useState<string>("");
  const [scanning, setScanning] = useState(false);
  const [results, setResults] = useState<ScanResult[]>([]);

  const runScan = async () => {
    setScanning(true);
    const params = new URLSearchParams();
    if (rsiBellow) params.set("rsi_below", rsiBellow);
    if (macdBullish === "true") params.set("macd_bullish", "true");
    if (macdBullish === "false") params.set("macd_bullish", "false");

    try {
      const data = (await api.scanner.scan(params.toString())) as ScanResult[];
      setResults(data);
    } catch {
      setResults([]);
    }
    setScanning(false);
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Stock Scanner</h1>
        <p className="text-ink-tertiary mt-1">Filtere nach technischen Kriterien</p>
      </div>

      <div className="card">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <label className="block">
            <span className="text-sm text-ink-tertiary block mb-1">RSI unter</span>
            <input
              type="number"
              value={rsiBellow}
              onChange={(e) => setRsiBelow(e.target.value)}
              placeholder="z.B. 30"
              className="input w-full"
            />
          </label>
          <label className="block">
            <span className="text-sm text-ink-tertiary block mb-1">MACD</span>
            <select
              value={macdBullish}
              onChange={(e) => setMacdBullish(e.target.value)}
              className="input w-full"
            >
              <option value="">Egal</option>
              <option value="true">Bullish (MACD &gt; Signal)</option>
              <option value="false">Bearish (MACD &lt; Signal)</option>
            </select>
          </label>
          <div className="flex items-end">
            <button onClick={runScan} disabled={scanning} className="btn-primary w-full">
              {scanning ? "Scanne..." : "Scan starten"}
            </button>
          </div>
        </div>
      </div>

      {results.length > 0 && (
        <div className="card">
          <h2 className="text-lg font-semibold mb-4">{results.length} Ergebnisse</h2>
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs text-ink-tertiary border-b border-border">
                <th className="pb-3">Symbol</th>
                <th className="pb-3">Name</th>
                <th className="pb-3">Sektor</th>
                <th className="pb-3">RSI</th>
                <th className="pb-3">MACD</th>
                <th className="pb-3">ATR</th>
              </tr>
            </thead>
            <tbody>
              {results.map((r) => (
                <tr key={r.symbol} className="border-b border-border/50">
                  <td className="py-3 font-semibold">{r.symbol}</td>
                  <td className="py-3 text-ink-tertiary">{r.name}</td>
                  <td className="py-3 text-ink-tertiary">{r.sector}</td>
                  <td className="py-3 font-mono">{r.rsi_14?.toFixed(1)}</td>
                  <td className="py-3">
                    <span className={r.macd > (r.macd_signal || 0) ? "text-gain" : "text-loss"}>
                      {r.macd?.toFixed(2)}
                    </span>
                  </td>
                  <td className="py-3 font-mono">{r.atr_14?.toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
