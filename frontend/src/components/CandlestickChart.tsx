import { useEffect, useRef } from "react";
import { createChart, type IChartApi, type ISeriesApi } from "lightweight-charts";

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
  const seriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);

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

    const series = chart.addCandlestickSeries({
      upColor: "#15803D",
      downColor: "#DC2626",
      borderUpColor: "#15803D",
      borderDownColor: "#DC2626",
      wickUpColor: "#15803D",
      wickDownColor: "#DC2626",
    });

    chartRef.current = chart;
    seriesRef.current = series;

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
      seriesRef.current = null;
    };
  }, [height]);

  useEffect(() => {
    const series = seriesRef.current;
    if (!series || data.length === 0) return;

    series.setData(
      data.map((d) => ({
        time: d.date as string,
        open: d.open,
        high: d.high,
        low: d.low,
        close: d.close,
      }))
    );

    chartRef.current?.timeScale().fitContent();
  }, [data]);

  return <div ref={containerRef} className="w-full" style={{ minHeight: height }} />;
}
