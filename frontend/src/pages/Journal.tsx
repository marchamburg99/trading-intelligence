import { useState } from "react";
import { useFetch } from "@/hooks/useFetch";
import { api } from "@/services/api";
import type { JournalEntry, JournalStats } from "@/types";

function Pnl({ value }: { value: number | null }) {
  if (value == null) return <span className="text-ink-faint">—</span>;
  const c = value > 0 ? "text-gain" : value < 0 ? "text-loss" : "text-ink-tertiary";
  return <span className={`font-mono font-bold ${c}`}>{value > 0 ? "+" : ""}€{value.toFixed(2)}</span>;
}

export function Journal() {
  const { data: entries, loading, refetch } = useFetch<JournalEntry[]>(
    () => api.journal.list() as Promise<JournalEntry[]>, []
  );
  const { data: stats, refetch: refetchStats } = useFetch<JournalStats>(
    () => api.journal.stats() as Promise<JournalStats>, []
  );

  const [showForm, setShowForm] = useState(false);
  const [editId, setEditId] = useState<number | null>(null);
  const [closeId, setCloseId] = useState<number | null>(null);
  const [closePrice, setClosePrice] = useState("");
  const [closeLessons, setCloseLessons] = useState("");

  const [form, setForm] = useState({
    symbol: "", trade_date: new Date().toISOString().split("T")[0],
    direction: "LONG", entry_price: "", position_size: "",
    stop_loss: "", take_profit: "", setup_type: "", notes: "",
  });

  // Edit-State
  const [editForm, setEditForm] = useState<Record<string, string>>({});

  const handleCreate = async () => {
    await api.journal.create({
      ...form,
      entry_price: Number(form.entry_price),
      position_size: Number(form.position_size),
      stop_loss: form.stop_loss ? Number(form.stop_loss) : undefined,
      take_profit: form.take_profit ? Number(form.take_profit) : undefined,
    });
    setShowForm(false);
    setForm({ symbol: "", trade_date: new Date().toISOString().split("T")[0], direction: "LONG", entry_price: "", position_size: "", stop_loss: "", take_profit: "", setup_type: "", notes: "" });
    refetch(); refetchStats();
  };

  const handleStartEdit = (e: JournalEntry) => {
    setEditId(e.id);
    setEditForm({
      entry_price: e.entry_price?.toString() || "",
      position_size: e.position_size?.toString() || "",
      stop_loss: e.stop_loss?.toString() || "",
      take_profit: e.take_profit?.toString() || "",
      setup_type: e.setup_type || "",
      notes: e.notes || "",
      lessons: e.lessons || "",
      direction: e.direction || "LONG",
    });
  };

  const handleSaveEdit = async () => {
    if (!editId) return;
    const data: Record<string, unknown> = {};
    if (editForm.entry_price) data.entry_price = Number(editForm.entry_price);
    if (editForm.position_size) data.position_size = Number(editForm.position_size);
    if (editForm.stop_loss) data.stop_loss = Number(editForm.stop_loss);
    if (editForm.take_profit) data.take_profit = Number(editForm.take_profit);
    if (editForm.setup_type !== undefined) data.setup_type = editForm.setup_type;
    if (editForm.notes !== undefined) data.notes = editForm.notes;
    if (editForm.lessons !== undefined) data.lessons = editForm.lessons;
    if (editForm.direction) data.direction = editForm.direction;
    await api.journal.update(editId, data);
    setEditId(null);
    refetch(); refetchStats();
  };

  const handleClose = async (id: number) => {
    if (!closePrice) return;
    await api.journal.close(id, { exit_price: Number(closePrice), lessons: closeLessons || undefined });
    setCloseId(null); setClosePrice(""); setCloseLessons("");
    refetch(); refetchStats();
  };

  const handleDelete = async (id: number) => {
    if (!confirm("Trade wirklich löschen?")) return;
    await api.journal.remove(id);
    refetch(); refetchStats();
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold">Trade Journal</h1>
          <p className="text-ink-tertiary text-sm">Dokumentiere und analysiere deine Trades</p>
        </div>
        <button onClick={() => setShowForm(!showForm)} className="btn-primary text-sm">+ Neuer Trade</button>
      </div>

      {/* Stats */}
      {stats && stats.total_trades > 0 && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="card text-center">
            <p className="text-xs text-ink-tertiary">Trades</p>
            <p className="text-2xl font-bold">{stats.total_trades}</p>
          </div>
          <div className="card text-center">
            <p className="text-xs text-ink-tertiary">Win-Rate</p>
            <p className="text-2xl font-bold text-gain">{stats.win_rate.toFixed(1)}%</p>
          </div>
          <div className="card text-center">
            <p className="text-xs text-ink-tertiary">Gesamt P&L</p>
            <p className={`text-2xl font-bold ${stats.total_pnl >= 0 ? "text-gain" : "text-loss"}`}>€{stats.total_pnl.toFixed(2)}</p>
          </div>
          <div className="card text-center">
            <p className="text-xs text-ink-tertiary">Avg P&L</p>
            <p className={`text-2xl font-bold ${stats.avg_pnl >= 0 ? "text-gain" : "text-loss"}`}>€{stats.avg_pnl.toFixed(2)}</p>
          </div>
        </div>
      )}

      {/* New Trade Form */}
      {showForm && (
        <div className="card space-y-3">
          <h2 className="text-sm font-bold">Neuen Trade erfassen</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <label className="block"><span className="text-[10px] text-ink-tertiary block mb-0.5">Symbol</span>
              <input value={form.symbol} onChange={e => setForm({ ...form, symbol: e.target.value })} placeholder="AAPL" className="input w-full" /></label>
            <label className="block"><span className="text-[10px] text-ink-tertiary block mb-0.5">Datum</span>
              <input type="date" value={form.trade_date} onChange={e => setForm({ ...form, trade_date: e.target.value })} className="input w-full" /></label>
            <label className="block"><span className="text-[10px] text-ink-tertiary block mb-0.5">Richtung</span>
              <select value={form.direction} onChange={e => setForm({ ...form, direction: e.target.value })} className="input w-full">
                <option value="LONG">LONG</option><option value="SHORT">SHORT</option></select></label>
            <label className="block"><span className="text-[10px] text-ink-tertiary block mb-0.5">Einstieg (€)</span>
              <input value={form.entry_price} onChange={e => setForm({ ...form, entry_price: e.target.value })} type="number" step="0.01" className="input font-mono w-full" /></label>
            <label className="block"><span className="text-[10px] text-ink-tertiary block mb-0.5">Stückzahl</span>
              <input value={form.position_size} onChange={e => setForm({ ...form, position_size: e.target.value })} type="number" className="input font-mono w-full" /></label>
            <label className="block"><span className="text-[10px] text-ink-tertiary block mb-0.5">Stop-Loss (€)</span>
              <input value={form.stop_loss} onChange={e => setForm({ ...form, stop_loss: e.target.value })} type="number" step="0.01" className="input font-mono w-full" /></label>
            <label className="block"><span className="text-[10px] text-ink-tertiary block mb-0.5">Take-Profit (€)</span>
              <input value={form.take_profit} onChange={e => setForm({ ...form, take_profit: e.target.value })} type="number" step="0.01" className="input font-mono w-full" /></label>
            <label className="block"><span className="text-[10px] text-ink-tertiary block mb-0.5">Setup</span>
              <input value={form.setup_type} onChange={e => setForm({ ...form, setup_type: e.target.value })} className="input w-full" /></label>
          </div>
          <label className="block"><span className="text-[10px] text-ink-tertiary block mb-0.5">Notizen</span>
            <textarea value={form.notes} onChange={e => setForm({ ...form, notes: e.target.value })} className="input w-full" rows={2} /></label>
          <button onClick={handleCreate} className="btn-primary text-sm">Trade speichern</button>
        </div>
      )}

      {/* Trade List */}
      {loading ? <p className="text-ink-tertiary">Lade...</p> : entries && entries.length > 0 ? (
        <div className="space-y-3">
          {entries.map((e) => (
            <div key={e.id} className={`card p-4 ${!e.is_closed ? "border-accent/20" : e.pnl && e.pnl > 0 ? "border-gain/10" : e.pnl && e.pnl < 0 ? "border-loss/10" : ""}`}>
              {editId === e.id ? (
                /* === EDIT MODE === */
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <h3 className="font-bold">{e.symbol} bearbeiten</h3>
                    <div className="flex gap-2">
                      <button onClick={handleSaveEdit} className="btn-primary text-xs px-3 py-1">Speichern</button>
                      <button onClick={() => setEditId(null)} className="btn-secondary text-xs px-3 py-1">Abbrechen</button>
                    </div>
                  </div>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                    <label className="block"><span className="text-[10px] text-ink-tertiary block mb-0.5">Richtung</span>
                      <select value={editForm.direction} onChange={ev => setEditForm({ ...editForm, direction: ev.target.value })} className="input w-full">
                        <option value="LONG">LONG</option><option value="SHORT">SHORT</option></select></label>
                    <label className="block"><span className="text-[10px] text-ink-tertiary block mb-0.5">Einstieg (€)</span>
                      <input value={editForm.entry_price} onChange={ev => setEditForm({ ...editForm, entry_price: ev.target.value })} type="number" step="0.01" className="input font-mono w-full" /></label>
                    <label className="block"><span className="text-[10px] text-ink-tertiary block mb-0.5">Stückzahl</span>
                      <input value={editForm.position_size} onChange={ev => setEditForm({ ...editForm, position_size: ev.target.value })} type="number" className="input font-mono w-full" /></label>
                    <label className="block"><span className="text-[10px] text-ink-tertiary block mb-0.5">Setup</span>
                      <input value={editForm.setup_type} onChange={ev => setEditForm({ ...editForm, setup_type: ev.target.value })} className="input w-full" /></label>
                    <label className="block"><span className="text-[10px] text-loss block mb-0.5">Stop-Loss (€)</span>
                      <input value={editForm.stop_loss} onChange={ev => setEditForm({ ...editForm, stop_loss: ev.target.value })} type="number" step="0.01" className="input font-mono w-full border-loss/30" /></label>
                    <label className="block"><span className="text-[10px] text-gain block mb-0.5">Take-Profit (€)</span>
                      <input value={editForm.take_profit} onChange={ev => setEditForm({ ...editForm, take_profit: ev.target.value })} type="number" step="0.01" className="input font-mono w-full border-gain/30" /></label>
                  </div>
                  <label className="block"><span className="text-[10px] text-ink-tertiary block mb-0.5">Notizen</span>
                    <textarea value={editForm.notes} onChange={ev => setEditForm({ ...editForm, notes: ev.target.value })} className="input w-full" rows={2} /></label>
                  <label className="block"><span className="text-[10px] text-ink-tertiary block mb-0.5">Lektionen</span>
                    <textarea value={editForm.lessons} onChange={ev => setEditForm({ ...editForm, lessons: ev.target.value })} className="input w-full" rows={2} /></label>
                </div>
              ) : closeId === e.id ? (
                /* === CLOSE MODE === */
                <div className="space-y-3">
                  <h3 className="font-bold">{e.symbol} schließen</h3>
                  <div className="grid grid-cols-3 gap-3">
                    <label className="block"><span className="text-[10px] text-ink-tertiary block mb-0.5">Ausstiegskurs (€)</span>
                      <input value={closePrice} onChange={ev => setClosePrice(ev.target.value)} type="number" step="0.01" autoFocus className="input font-mono w-full" /></label>
                    <label className="block col-span-2"><span className="text-[10px] text-ink-tertiary block mb-0.5">Was habe ich gelernt?</span>
                      <input value={closeLessons} onChange={ev => setCloseLessons(ev.target.value)} placeholder="z.B. Stop-Loss zu eng, hätte halten sollen..." className="input w-full" /></label>
                  </div>
                  <div className="flex gap-2">
                    <button onClick={() => handleClose(e.id)} className="bg-warn hover:bg-warn/80 text-black px-3 py-1.5 rounded-xl text-sm font-bold">Trade schließen</button>
                    <button onClick={() => setCloseId(null)} className="btn-secondary text-xs px-3 py-1">Abbrechen</button>
                  </div>
                </div>
              ) : (
                /* === VIEW MODE === */
                <div>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <a href={`https://finance.yahoo.com/quote/${e.symbol}`} target="_blank" rel="noopener noreferrer" className="font-bold text-lg hover:text-accent transition-colors">{e.symbol}</a>
                      <span className={`text-xs font-bold px-2 py-0.5 rounded-xl ${e.direction === "LONG" ? "bg-gain-bg text-gain" : "bg-loss-bg text-loss"}`}>{e.direction}</span>
                      <span className={`text-xs px-2 py-0.5 rounded-full ${e.is_closed ? "bg-surface-muted text-ink-tertiary" : "bg-accent/20 text-accent"}`}>
                        {e.is_closed ? "Geschlossen" : "Offen"}
                      </span>
                      {e.setup_type && <span className="text-xs text-ink-tertiary">{e.setup_type}</span>}
                    </div>
                    <div className="flex items-center gap-2">
                      {!e.is_closed && (
                        <button onClick={() => { setCloseId(e.id); fetch(`/api/quotes/${e.symbol}`).then(r=>r.json()).then(q=>{ if(q.price) setClosePrice(String(q.price)); }).catch(()=>{}); }} className="text-xs bg-warn-bg text-warn hover:bg-warn-bg/80 px-2 py-1 rounded-xl">
                          Schließen
                        </button>
                      )}
                      <button onClick={() => handleStartEdit(e)} className="text-xs text-ink-tertiary hover:text-ink px-2 py-1">Bearbeiten</button>
                      <button onClick={() => handleDelete(e.id)} className="text-xs text-ink-faint hover:text-loss px-2 py-1">Löschen</button>
                    </div>
                  </div>

                  <div className="grid grid-cols-3 md:grid-cols-7 gap-3 mt-3 text-sm">
                    <div><span className="text-[10px] text-ink-tertiary block">Datum</span><span className="text-ink-tertiary">{e.trade_date}</span></div>
                    <div><span className="text-[10px] text-ink-tertiary block">Einstieg</span><span className="font-mono">€{e.entry_price?.toFixed(2)}</span></div>
                    <div><span className="text-[10px] text-ink-tertiary block">Ausstieg</span><span className="font-mono">{e.exit_price ? `€${e.exit_price.toFixed(2)}` : "—"}</span></div>
                    <div><span className="text-[10px] text-ink-tertiary block">Stück</span><span>{e.position_size}</span></div>
                    <div><span className="text-[10px] text-ink-tertiary block">P&L</span><Pnl value={e.pnl} /></div>
                    <div><span className="text-[10px] text-ink-tertiary block">P&L %</span>{e.pnl_percent != null ? <span className={`font-mono ${e.pnl_percent >= 0 ? "text-gain" : "text-loss"}`}>{e.pnl_percent > 0 ? "+" : ""}{e.pnl_percent.toFixed(2)}%</span> : "—"}</div>
                  </div>

                  {(e.notes || e.lessons) && (
                    <div className="mt-3 pt-2 border-t border-border text-xs text-ink-tertiary space-y-1">
                      {e.notes && <p>{e.notes}</p>}
                      {e.lessons && <p className="text-warn/70">Lektion: {e.lessons}</p>}
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      ) : (
        <div className="card text-center py-12">
          <p className="text-ink-tertiary text-lg mb-2">Noch keine Trades</p>
          <p className="text-ink-faint text-sm">Trades werden automatisch erfasst wenn du auf dem Dashboard "Trade ausführen" klickst</p>
        </div>
      )}
    </div>
  );
}
