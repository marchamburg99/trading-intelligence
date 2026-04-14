import { clsx } from "clsx";

const COLORS = {
  GREEN: "bg-gain",
  YELLOW: "bg-warn",
  RED: "bg-loss",
};

const LABELS = {
  GREEN: "Bullish",
  YELLOW: "Neutral",
  RED: "Bearish",
};

export function MacroAmpel({ status }: { status: "GREEN" | "YELLOW" | "RED" }) {
  return (
    <div className="flex items-center gap-2">
      <div className={clsx("w-2.5 h-2.5 rounded-full", COLORS[status])} />
      <span className="text-sm font-medium text-ink">{LABELS[status]}</span>
    </div>
  );
}
