const BASE = "/api";

async function fetchJSON<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) {
    // Handle 307 redirect — refetch with trailing slash
    if (res.status === 307) {
      const withSlash = await fetch(`${BASE}${path}${path.includes("?") ? "" : "/"}`);
      if (!withSlash.ok) throw new Error(`API error: ${withSlash.status}`);
      return withSlash.json();
    }
    throw new Error(`API error: ${res.status}`);
  }
  return res.json();
}

async function postJSON<T>(path: string, body: unknown): Promise<T> {
  const url = `${BASE}${path}`;
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

async function putJSON<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

async function deleteJSON<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { method: "DELETE" });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export const api = {
  signals: {
    list: (params?: string) => fetchJSON(`/signals/${params ? `?${params}` : ""}`),
    top: () => fetchJSON("/signals/top"),
    forSymbol: (symbol: string) => fetchJSON(`/signals/${symbol}`),
  },
  watchlist: {
    list: () => fetchJSON("/watchlist/"),
    add: (data: { symbol: string; notes?: string }) => postJSON("/watchlist/", data),
    remove: (symbol: string) => deleteJSON(`/watchlist/${symbol}`),
  },
  tickers: {
    list: (search?: string) => fetchJSON(`/tickers/${search ? `?search=${search}` : ""}`),
    detail: (symbol: string) => fetchJSON(`/tickers/${symbol}`),
  },
  macro: {
    overview: () => fetchJSON("/macro/"),
    history: (indicator: string) => fetchJSON(`/macro/history/${indicator}`),
    ampel: () => fetchJSON("/macro/ampel"),
    calendar: () => fetchJSON("/macro/calendar"),
  },
  hedgefunds: {
    filings: () => fetchJSON("/hedgefunds/filings"),
    positions: (id: number) => fetchJSON(`/hedgefunds/filings/${id}/positions`),
    clusters: () => fetchJSON("/hedgefunds/clusters"),
  },
  papers: {
    list: (params?: string) => fetchJSON(`/papers/${params ? `?${params}` : ""}`),
    detail: (id: number) => fetchJSON(`/papers/${id}`),
    summarize: () => postJSON<{ status: string; remaining_unsummarized: number }>("/papers/summarize", {}),
  },
  sentiment: {
    forSymbol: (symbol: string) => fetchJSON(`/sentiment/${symbol}`),
    heatmap: () => fetchJSON("/sentiment/"),
  },
  backtest: {
    run: (data: { symbol: string; months?: number }) => postJSON("/backtest/run", data),
    results: (symbol?: string) => fetchJSON(`/backtest/results${symbol ? `?symbol=${symbol}` : ""}`),
  },
  journal: {
    list: () => fetchJSON("/journal/"),
    create: (data: unknown) => postJSON("/journal/", data),
    update: (id: number, data: unknown) => putJSON(`/journal/${id}`, data),
    close: (id: number, data: { exit_price: number; lessons?: string }) => postJSON(`/journal/${id}/close`, data),
    remove: (id: number) => deleteJSON(`/journal/${id}`),
    stats: () => fetchJSON("/journal/stats"),
    performance: () => fetchJSON("/journal/performance"),
    portfolio: () => fetchJSON("/journal/portfolio"),
    updatePortfolio: (data: { initial_capital: number }) => putJSON("/journal/portfolio", data),
  },
  analyze: {
    run: (data: { symbol: string; portfolio_capital?: number }) => postJSON("/analyze/", data),
  },
  scanner: {
    scan: (params: string) => fetchJSON(`/scanner/?${params}`),
  },
  dashboard: {
    overview: () => fetchJSON("/dashboard/overview"),
  },
  discovery: {
    suggestions: (params?: string) => fetchJSON(`/discovery/suggestions${params ? `?${params}` : ""}`),
    addToWatchlist: (symbol: string) => postJSON(`/discovery/suggestions/${symbol}/add-to-watchlist`, {}),
  },
};
