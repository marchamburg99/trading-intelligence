import { clsx } from "clsx";

export function ConfidenceBar({ value }: { value: number }) {
  const color =
    value >= 70 ? "bg-gain" : value >= 40 ? "bg-warn" : "bg-loss";

  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 bg-surface-muted rounded-full overflow-hidden">
        <div
          className={clsx("h-full rounded-full transition-all", color)}
          style={{ width: `${Math.min(100, Math.max(0, value))}%` }}
        />
      </div>
      <span className="text-[11px] font-mono font-medium text-ink-secondary w-10 text-right">
        {value.toFixed(0)}%
      </span>
    </div>
  );
}
