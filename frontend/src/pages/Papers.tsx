import { useState } from "react";
import { useFetch } from "@/hooks/useFetch";
import { api } from "@/services/api";
import type { Paper } from "@/types";

export function Papers() {
  const [search, setSearch] = useState("");
  const { data: papers, loading } = useFetch<Paper[]>(
    () => api.papers.list(search ? `search=${search}` : "") as Promise<Paper[]>,
    [search]
  );
  const [expanded, setExpanded] = useState<number | null>(null);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Research Papers</h1>
        <p className="text-ink-tertiary mt-1">KI-zusammengefasste Quantitative Finance Papers</p>
      </div>

      <input
        type="text"
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        placeholder="Suche nach Titel, Tag..."
        className="input w-full"
      />

      {loading ? (
        <p className="text-ink-tertiary">Lade...</p>
      ) : papers && papers.length > 0 ? (
        <div className="space-y-4">
          {papers.map((p) => (
            <button key={p.id} type="button" className="card cursor-pointer w-full text-left" onClick={() => setExpanded(expanded === p.id ? null : p.id)}>
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <h3 className="font-semibold">{p.title}</h3>
                  <p className="text-xs text-ink-tertiary mt-1">
                    {p.authors} — {p.source} — {p.published_date}
                  </p>
                </div>
                {p.relevance_score && (
                  <span className="text-sm font-bold text-accent ml-4">
                    {p.relevance_score.toFixed(0)}%
                  </span>
                )}
              </div>
              {p.tags && (
                <div className="flex gap-2 mt-2">
                  {p.tags.map((tag) => (
                    <span key={tag} className="text-xs bg-surface-muted px-2 py-0.5 rounded-full">
                      {tag}
                    </span>
                  ))}
                </div>
              )}
              {expanded === p.id && (
                <div className="mt-4 pt-4 border-t border-border space-y-3">
                  {p.ai_summary && (
                    <div>
                      <h4 className="text-sm font-medium text-ink-tertiary">KI-Zusammenfassung</h4>
                      <p className="text-sm mt-1 whitespace-pre-line">{p.ai_summary}</p>
                    </div>
                  )}
                  {p.trading_implication && (
                    <div>
                      <h4 className="text-sm font-medium text-ink-tertiary">Trading-Implikation</h4>
                      <p className="text-sm mt-1 text-gain">{p.trading_implication}</p>
                    </div>
                  )}
                  {p.url && (
                    <a
                      href={p.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-sm text-accent hover:underline"
                      onClick={(e) => e.stopPropagation()}
                    >
                      Paper öffnen
                    </a>
                  )}
                </div>
              )}
            </button>
          ))}
        </div>
      ) : (
        <p className="text-ink-tertiary">Keine Papers gefunden.</p>
      )}
    </div>
  );
}
