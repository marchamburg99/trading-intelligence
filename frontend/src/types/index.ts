export type SignalType = "BUY" | "SELL" | "HOLD" | "AVOID";

export interface Signal {
  id: number;
  symbol: string;
  name: string;
  sector: string;
  date: string;
  signal_type: SignalType;
  confidence: number;
  entry_price: number | null;
  stop_loss: number | null;
  take_profit: number | null;
  risk_reward_ratio: number;
  position_size: number;
  risk_rating: number;
  expected_hold_days: number;
  reasoning: string;
  ta_score: number;
  fundamental_score: number;
  sentiment_score: number;
  macro_score: number;
}

export interface MacroAmpel {
  ampel: "GREEN" | "YELLOW" | "RED";
  indicators: Record<string, string>;
}

export interface SentimentData {
  symbol: string;
  composite_score: number;
  news_sentiment: number;
  reddit_mentions: number;
}

export interface HedgeFundFiling {
  id: number;
  fund_name: string;
  filing_date: string;
  total_value: number | null;
  position_count: number;
}

export interface Paper {
  id: number;
  title: string;
  authors: string;
  source: string;
  url: string;
  published_date: string;
  ai_summary: string;
  trading_implication: string;
  relevance_score: number;
  tags: string[];
}

export interface BacktestResult {
  symbol: string;
  total_trades: number;
  win_rate: number;
  profit_factor: number;
  max_drawdown: number;
  sharpe_ratio: number;
  total_return: number;
  equity_curve: { date: string; equity: number }[];
}

export interface JournalEntry {
  id: number;
  symbol: string;
  trade_date: string;
  direction: string;
  entry_price: number | null;
  exit_price: number | null;
  position_size: number;
  pnl: number | null;
  pnl_percent: number | null;
  setup_type: string;
  is_closed: boolean;
  notes: string;
  lessons: string;
}

export interface JournalStats {
  total_trades: number;
  wins: number;
  losses: number;
  win_rate: number;
  total_pnl: number;
  avg_pnl: number;
  best_trade: number;
  worst_trade: number;
}
