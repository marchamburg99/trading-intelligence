/**
 * Zeigt Preise mit Originalwährung + EUR-Umrechnung.
 * Beispiel: $259.20 (€219.70) oder nur €144.22 für EUR-Ticker
 */
export function Price({
  value,
  currency = "USD",
  currencySymbol = "$",
  eurValue,
  className = "",
}: {
  value: number;
  currency?: string;
  currencySymbol?: string;
  eurValue?: number | null;
  className?: string;
}) {
  if (currency === "EUR") {
    return <span className={`font-mono ${className}`}>€{value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>;
  }

  return (
    <span className={`font-mono ${className}`}>
      {currencySymbol}{value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
      {eurValue != null && (
        <span className="text-ink-tertiary text-[10px] ml-1">(€{eurValue.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })})</span>
      )}
    </span>
  );
}

export function PriceCompact({
  value,
  currencySymbol = "$",
  eurValue,
}: {
  value: number;
  currencySymbol?: string;
  eurValue?: number | null;
}) {
  return (
    <span className="font-mono">
      {currencySymbol}{value.toFixed(2)}
      {eurValue != null && <span className="text-ink-faint text-[9px] ml-0.5">€{eurValue.toFixed(0)}</span>}
    </span>
  );
}
