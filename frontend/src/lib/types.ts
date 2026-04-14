export interface Exchange {
  id: number;
  name: string;
  slug: string;
}

export interface TradingPair {
  id: number;
  symbol: string;
  timeframe: string;
  active: boolean;
  exchange: Exchange;
}

export interface Indicators {
  ema_9: number | null;
  ema_21: number | null;
  ema_50: number | null;
  ema_200: number | null;
  rsi: number | null;
  vwap: number | null;
}

export interface Candle {
  timestamp: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  indicators: Indicators;
}

export interface Alert {
  id: number;
  triggered_at: string;
  message: string;
  sent: boolean;
  rule_name: string;
  symbol: string;
  timeframe: string;
  exchange_slug: string;
}

export interface PairsResponse {
  pairs: TradingPair[];
  count: number;
}

export interface CandlesResponse {
  pair_id: number;
  symbol: string;
  timeframe: string;
  candles: Candle[];
  count: number;
}

export interface AlertsResponse {
  alerts: Alert[];
  count: number;
}
