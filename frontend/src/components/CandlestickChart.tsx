import { useEffect, useRef } from "react";
import { createChart } from "lightweight-charts";

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

  useEffect(() => {
    if (!containerRef.current || data.length === 0) return;

    const chart = createChart(containerRef.current, {
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
      crosshair: {
        mode: 0,
      },
      rightPriceScale: {
        borderColor: "#E7E5E4",
      },
      timeScale: {
        borderColor: "#E7E5E4",
        timeVisible: false,
      },
    });

    const candleSeries = chart.addCandlestickSeries({
      upColor: "#15803D",
      downColor: "#DC2626",
      borderUpColor: "#15803D",
      borderDownColor: "#DC2626",
      wickUpColor: "#15803D",
      wickDownColor: "#DC2626",
    });

    candleSeries.setData(
      data.map((d) => ({
        time: d.date,
        open: d.open,
        high: d.high,
        low: d.low,
        close: d.close,
      }))
    );

    chart.timeScale().fitContent();

    const handleResize = () => {
      if (containerRef.current) {
        chart.applyOptions({ width: containerRef.current.clientWidth });
      }
    };
    window.addEventListener("resize", handleResize);

    return () => {
      window.removeEventListener("resize", handleResize);
      chart.remove();
    };
  }, [data, height]);

  return <div ref={containerRef} className="w-full" />;
}
