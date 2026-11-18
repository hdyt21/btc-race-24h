"""BTC race bot for make.fun btc-race-24h-20261118-1444.

Strategy: EMA crossover on the 1-minute close of CBBTC (Coinbase Wrapped BTC),
long only, at most one open position.

- Two EMAs of the close price: fast span 55, slow span 165. Each EMA starts
  empty; once span closes have been seen it is seeded with their simple
  average, then updated each bar as value += (2 / (span + 1)) * (close - value).
- A cross down is when the gap (fast minus slow) turns negative from a
  non-negative previous value; a cross up is the reverse (gap turns positive
  from a non-positive previous value). The down flag is set on a cross down
  and cleared whenever the gap is None or >= 0.
- When flat, buy on a cross up only with momentum confirmation: more than 60
  closes seen and the 60-minute return at least 30 basis points. The buy
  spends min(cash, weight_room), at least the $1 minimum notional.
- When holding, sell the whole position if any exit fires: a cross down
  (down flag set), a take-profit of +150 basis points over cost, or a
  stop-loss of -150 basis points under cost.
- No orders during warm-up bars or when no close exists yet.

Constants:
    SYMBOL = "CBBTC"
    FAST_SPAN = 55
    SLOW_SPAN = 165
    MAX_SLIPPAGE_BPS = 100
    MIN_NOTIONAL = 1_000_000 quote units ($1; start capital is 1_000_000_000)
    TAKE_PROFIT_BPS = 150
    STOP_LOSS_BPS = 150
    MOMENTUM_LOOKBACK = 60 bars
    MOMENTUM_MIN_BPS = 30

Determinism: orders are a pure function of the bars seen so far. No network,
no wall clock, no file access, no unseeded randomness; standard library only
plus the vendored makefun_bars shim.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor"))

import makefun_bars

SYMBOL = "CBBTC"
FAST_SPAN = 55
SLOW_SPAN = 165
MAX_SLIPPAGE_BPS = 100
MIN_NOTIONAL = 1_000_000
TAKE_PROFIT_BPS = 150
STOP_LOSS_BPS = 150
MOMENTUM_LOOKBACK = 60
MOMENTUM_MIN_BPS = 30

_closes = []
_fast = None
_slow = None
_prev_gap = None
_down = False


def _update_ema(current, span, close):
    """Advance one EMA by one close; seed with the simple average at span closes."""
    if current is None:
        if len(_closes) == span:
            return sum(_closes) / span
        return None
    return current + (2.0 / (span + 1)) * (close - current)


def on_batch(state, batch):
    global _fast, _slow, _prev_gap, _down

    if state.warming_up:
        return []

    close = state.close(SYMBOL)
    if close is None:
        return []

    _closes.append(close)
    _fast = _update_ema(_fast, FAST_SPAN, close)
    _slow = _update_ema(_slow, SLOW_SPAN, close)

    if _fast is None or _slow is None:
        gap = None
    else:
        gap = _fast - _slow

    old_prev_gap = _prev_gap

    if gap is None or gap >= 0:
        _down = False
    if gap is not None and gap < 0 and old_prev_gap is not None and old_prev_gap >= 0:
        _down = True

    _prev_gap = gap

    holding = state.positions.get(SYMBOL)
    if holding is not None and holding.qty > 0:
        value = state.value(SYMBOL, holding.qty)
        cost = holding.cost
        if (
            _down
            or value * 10000 >= cost * (10000 + TAKE_PROFIT_BPS)
            or value * 10000 <= cost * (10000 - STOP_LOSS_BPS)
        ):
            return [
                {
                    "side": "sell",
                    "symbol": SYMBOL,
                    "qty": holding.qty,
                    "max_slippage_bps": MAX_SLIPPAGE_BPS,
                }
            ]
        return []

    # Flat: buy only on a cross up with momentum confirmation.
    cross_up = (
        gap is not None
        and gap > 0
        and old_prev_gap is not None
        and old_prev_gap <= 0
    )
    if not cross_up:
        return []
    if len(_closes) <= MOMENTUM_LOOKBACK:
        return []
    momentum_bps = (close * 10000) // _closes[-61] - 10000
    if momentum_bps < MOMENTUM_MIN_BPS:
        return []
    notional = min(state.cash, state.weight_room(SYMBOL))
    if notional < MIN_NOTIONAL:
        return []
    return [
        {
            "side": "buy",
            "symbol": SYMBOL,
            "notional_quote_units": notional,
            "max_slippage_bps": MAX_SLIPPAGE_BPS,
        }
    ]


if __name__ == "__main__":
    makefun_bars.run(on_batch)
