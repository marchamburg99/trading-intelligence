import { lazy, Suspense, useState } from "react";
import { useFetch } from "@/hooks/useFetch";
import { api } from "@/services/api";
import { MacroAmpel } from "@/components/MacroAmpel";
import type { MacroAmpel as MacroAmpelType } from "@/types";

const RechartsModule = lazy(() =>
  import("recharts").then((mod) => ({
    default: ({
      data,
    }: {
      data: MacroPoint[];
    }) => (
      <mod.ResponsiveContainer width="100%" height={300}>
        <mod.LineChart data={data}>
          <mod.CartesianGrid strokeDasharray="3 3" stroke="#E7E5E4" />
          <mod.XAxis dataKey="date" tick={{ fontSize: 11, fill: "#A8A29E" }} />
          <mod.YAxis tick={{ fontSize: 11, fill: "#A8A29E" }} />
          <mod.Tooltip
            contentStyle={{ backgroundColor: "#FFFFFF", border: "1px solid #E7E5E4" }}
          />
          <mod.Line type="monotone" dataKey="value" stroke="#3b82f6" strokeWidth={2} dot={false} />
        </mod.LineChart>
      </mod.ResponsiveContainer>
    ),
  }))
);

interface MacroOverview {
  [key: string]: { value: number; previous: number | null; status: string | null; date: string };
}

interface MacroPoint {
  date: string;
  value: number;
}

const INDICATOR_LABELS: Record<string, string> = {
  CPI: "Verbraucherpreisindex (CPI)",
  FED_FUNDS: "Fed Funds Rate",
  YIELD_SPREAD: "Yield Curve (10Y-2Y)",
  NFP: "Non-Farm Payrolls",
  VIX: "Volatilitätsindex (VIX)",
};

export function Macro() {
  const { data: overview } = useFetch<MacroOverview>(
    () => api.macro.overview() as Promise<MacroOverview>,
    []
  );
  const { data: ampel } = useFetch<MacroAmpelType>(
    () => api.macro.ampel() as Promise<MacroAmpelType>,
    []
  );
  const { data: calendar } = useFetch<{ date: string; event: string; importance: string; impact: string }[]>(
    () => api.macro.calendar() as Promise<{ date: string; event: string; importance: string; impact: string }[]>,
    []
  );
  const [selected, setSelected] = useState("VIX");
  const { data: history } = useFetch<MacroPoint[]>(
    () => api.macro.history(selected) as Promise<MacroPoint[]>,
    [selected]
  );

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Makro Dashboard</h1>
        <p className="text-ink-tertiary mt-1">Wirtschaftsindikatoren & Ampel-System</p>
      </div>

      {/* Ampel */}
      <div className="card">
        <h2 className="text-lg font-semibold mb-4">Makro-Ampel</h2>
        {ampel ? (
          <div className="flex items-center gap-6">
            <MacroAmpel status={ampel.ampel} />
            <div className="flex gap-4">
              {Object.entries(ampel.indicators || {}).map(([key, status]) => (
                <div key={key} className="text-center">
                  <MacroAmpel status={status as "GREEN" | "YELLOW" | "RED"} />
                  <p className="text-xs text-ink-tertiary mt-1">{key}</p>
                </div>
              ))}
            </div>
          </div>
        ) : (
          <p className="text-ink-tertiary">Lade...</p>
        )}
      </div>

      {/* Wirtschaftskalender */}
      {calendar && calendar.length > 0 && (
        <div className="card">
          <h2 className="section-label mb-3">Wirtschaftskalender</h2>
          <div className="space-y-2">
            {calendar.map((e, i) => (
              <div key={i} className="flex items-center justify-between py-2 border-b border-border/50 last:border-0 text-sm">
                <div className="flex items-center gap-3">
                  <span className={`w-2 h-2 rounded-full ${e.importance === "HIGH" ? "bg-loss" : "bg-warn"}`} />
                  <span className="font-medium">{e.event}</span>
                </div>
                <div className="flex items-center gap-4">
                  <span className="text-xs text-ink-tertiary">{e.impact}</span>
                  <span className="font-mono text-xs text-ink-secondary">{e.date}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Indicators Overview */}
      <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-4">
        {overview &&
          Object.entries(overview).map(([key, data]) => (
            <button
              key={key}
              type="button"
              className={`card cursor-pointer transition-all text-left ${selected === key ? "ring-2 ring-accent" : ""}`}
              onClick={() => setSelected(key)}
            >
              <p className="text-xs text-ink-tertiary">{INDICATOR_LABELS[key] || key}</p>
              <p className="text-2xl font-bold font-mono mt-1">{data.value?.toFixed(2)}</p>
              {data.previous !== null && (
                <p className={`text-xs mt-1 ${data.value > data.previous ? "text-loss" : "text-gain"}`}>
                  {data.value > data.previous ? "+" : ""}
                  {(data.value - data.previous).toFixed(2)} vs. vorher
                </p>
              )}
              <p className="text-xs text-ink-faint mt-1">{data.date}</p>
            </button>
          ))}
      </div>

      {/* Chart */}
      <div className="card">
        <h2 className="text-lg font-semibold mb-4">{INDICATOR_LABELS[selected] || selected}</h2>
        {history && history.length > 0 ? (
          <Suspense fallback={<div className="h-[300px] flex items-center justify-center text-ink-tertiary">Lade Chart...</div>}>
            <RechartsModule data={history} />
          </Suspense>
        ) : (
          <p className="text-ink-tertiary">Keine Daten verfügbar.</p>
        )}
      </div>
    </div>
  );
}
