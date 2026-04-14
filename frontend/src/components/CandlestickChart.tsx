import { useEffect, useRef } from "react";
import { createChart, type IChartApi } from "lightweight-charts";

interface OHLCVPoint {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export function CandlestickChart({ data, height = 350 }: { data: OHLCVPoint[]; height?: number }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);

  // Chart einmal erstellen
  useEffect(() => {
    if (!containerRef.current) return;

    const chart = createChart(containerRef.current, {
      width: containerRef.current.clientWidth,
      height,
      layout: {
        background: { color: "transparent" },
        textColor: "#57534E",
        fontFamily: "'DM Sans', system-ui, sans-serif",
        fontSize: 11,
      },
      grid: {
        vertLines: { color: "#F5F5F4" },
        horzLines: { color: "#F5F5F4" },
      },
      crosshair: { mode: 0 },
      rightPriceScale: { borderColor: "#E7E5E4" },
      timeScale: { borderColor: "#E7E5E4", timeVisible: false },
    });

    chartRef.current = chart;

    const handleResize = () => {
      if (containerRef.current) {
        chart.applyOptions({ width: containerRef.current.clientWidth });
      }
    };
    window.addEventListener("resize", handleResize);

    return () => {
      window.removeEventListener("resize", handleResize);
      chart.remove();
      chartRef.current = null;
    };
  }, [height]);

  // Daten setzen/aktualisieren (ohne Chart neu zu erstellen)
  useEffect(() => {
    const chart = chartRef.current;
    if (!chart || data.length === 0) return;

    // Alle bestehenden Series entfernen
    try {
      // lightweight-charts hat keine "removeAllSeries", also neu aufbauen
      const series = chart.addCandlestickSeries({
        upColor: "#15803D",
        downColor: "#DC2626",
        borderUpColor: "#15803D",
        borderDownColor: "#DC2626",
        wickUpColor: "#15803D",
        wickDownColor: "#DC2626",
      });

      series.setData(
        data.map((d) => ({
          time: d.date as string,
          open: d.open,
          high: d.high,
          low: d.low,
          close: d.close,
        }))
      );

      chart.timeScale().fitContent();

      return () => {
        try { chart.removeSeries(series); } catch { /* already removed */ }
      };
    } catch {
      // Chart wurde bereits entfernt
    }
  }, [data]);

  return <div ref={containerRef} className="w-full" style={{ minHeight: height }} />;
}
