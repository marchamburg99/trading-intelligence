import { lazy, Suspense } from "react";

const COLORS = ["#22c55e", "#f59e0b", "#ef4444"];

const LazyGauge = lazy(() =>
  import("recharts").then((mod) => ({
    default: ({ value, color }: { value: number; color: string }) => {
      const chartData = [
        { name: "score", value: value },
        { name: "remaining", value: 100 - value },
      ];
      return (
        <mod.PieChart width={120} height={80}>
          <mod.Pie
            data={chartData}
            cx={60}
            cy={70}
            startAngle={180}
            endAngle={0}
            innerRadius={35}
            outerRadius={50}
            dataKey="value"
            stroke="none"
          >
            <mod.Cell fill={color} />
            <mod.Cell fill="#F5F5F4" />
          </mod.Pie>
        </mod.PieChart>
      );
    },
  }))
);

export function SentimentGauge({ value }: { value: number }) {
  const color = value >= 60 ? COLORS[0] : value >= 40 ? COLORS[1] : COLORS[2];
  const label = value >= 60 ? "Bullish" : value >= 40 ? "Neutral" : "Bearish";

  return (
    <div className="flex flex-col items-center">
      <Suspense fallback={<div className="w-[120px] h-[80px]" />}>
        <LazyGauge value={value} color={color} />
      </Suspense>
      <p className="text-2xl font-bold font-mono -mt-2">{value.toFixed(0)}</p>
      <p className="text-xs text-ink-tertiary">{label}</p>
    </div>
  );
}
