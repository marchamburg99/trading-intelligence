"""Tests für die Signal Engine v2."""
import pytest
from unittest.mock import MagicMock
from signals.engine import compute_ta_score, compute_macro_score
from core.models import Indicator, Ticker, MacroData, MacroStatus


def make_indicator(**kwargs):
    defaults = {
        "rsi_14": 50, "macd": 0.5, "macd_signal": 0.3,
        "ema_21": 150, "ema_50": 145, "ema_200": 130,
        "bb_upper": 160, "bb_middle": 150, "bb_lower": 140,
        "atr_14": 3.0, "obv": 1000000,
        "stoch_k": 50, "stoch_d": 50,
        "macd_histogram": 0.2,
    }
    defaults.update(kwargs)
    ind = MagicMock(spec=Indicator)
    for k, v in defaults.items():
        setattr(ind, k, v)
    return ind


class TestTAScore:
    def test_oversold_rsi_boosts_score(self):
        ind = make_indicator(rsi_14=25)
        score, signals = compute_ta_score(ind, close=148.0)
        assert score > 60
        assert any("RSI oversold" in s for s in signals)

    def test_overbought_rsi_lowers_score(self):
        ind = make_indicator(rsi_14=75)
        score, signals = compute_ta_score(ind, close=148.0)
        assert score < 50
        assert any("RSI overbought" in s for s in signals)

    def test_bullish_macd_crossover(self):
        ind = make_indicator(macd=1.5, macd_signal=0.5)
        score, signals = compute_ta_score(ind, close=148.0)
        assert any("MACD bullish" in s for s in signals)

    def test_strong_uptrend_ema_alignment(self):
        ind = make_indicator(ema_21=155, ema_50=150, ema_200=130)
        score, signals = compute_ta_score(ind, close=160.0)
        assert score > 65
        assert any("bullish" in s for s in signals)

    def test_strong_downtrend(self):
        ind = make_indicator(ema_21=130, ema_50=140, ema_200=150)
        score, signals = compute_ta_score(ind, close=125.0)
        assert score < 40

    def test_near_lower_bollinger(self):
        ind = make_indicator(bb_lower=140, bb_upper=160)
        score, signals = compute_ta_score(ind, close=141.0)
        assert any("BB" in s for s in signals)

    def test_stochastic_oversold(self):
        ind = make_indicator(stoch_k=15, stoch_d=18)
        score, signals = compute_ta_score(ind, close=148.0)
        assert any("Stochastic" in s for s in signals)

    def test_score_clamped_0_100(self):
        ind = make_indicator(
            rsi_14=20, macd=5, macd_signal=-2,
            ema_21=155, ema_50=150, ema_200=130,
            stoch_k=10, stoch_d=10,
        )
        score, _ = compute_ta_score(ind, close=160.0)
        assert 0 <= score <= 100


class TestMacroScore:
    def test_low_vix_boosts_score(self):
        db = MagicMock()
        vix_mock = MagicMock()
        vix_mock.value = 14
        yield_mock = MagicMock()
        yield_mock.value = 1.5
        fed_data = []

        call_count = [0]
        def query_side_effect(model):
            q = MagicMock()
            q.filter.return_value = q
            q.order_by.return_value = q
            q.limit.return_value = q
            q.all.return_value = fed_data
            if model == MacroData:
                q.first.side_effect = [vix_mock, yield_mock]
            return q

        db.query.side_effect = query_side_effect
        score, signals = compute_macro_score(db)
        assert score > 60

    def test_high_vix_lowers_score(self):
        db = MagicMock()
        vix_mock = MagicMock()
        vix_mock.value = 35
        yield_mock = MagicMock()
        yield_mock.value = -0.5
        fed_data = []

        def query_side_effect(model):
            q = MagicMock()
            q.filter.return_value = q
            q.order_by.return_value = q
            q.limit.return_value = q
            q.all.return_value = fed_data
            if model == MacroData:
                q.first.side_effect = [vix_mock, yield_mock]
            return q

        db.query.side_effect = query_side_effect
        score, signals = compute_macro_score(db)
        assert score < 30
