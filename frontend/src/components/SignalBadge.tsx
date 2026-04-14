import { clsx } from "clsx";
import type { SignalType } from "@/types";

const STYLES: Record<SignalType, string> = {
  BUY: "bg-gain-bg text-gain border-gain-light",
  SELL: "bg-loss-bg text-loss border-loss-light",
  HOLD: "bg-surface-muted text-ink-secondary border-border",
  AVOID: "bg-warn-bg text-warn border-warn-light",
};

export function SignalBadge({ type }: { type: SignalType }) {
  return (
    <span
      className={clsx(
        "inline-flex items-center px-2 py-0.5 rounded-lg text-[11px] font-semibold border",
        STYLES[type]
      )}
    >
      {type}
    </span>
  );
}
