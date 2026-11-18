# BTC Race 24h — CBBTC Trading Bot

A bot that races a BTC trading strategy live for 24 hours in the make.fun
bars-replay simulation.

## What it does

The bot trades **Coinbase Wrapped BTC (CBBTC)** on **1-minute bars** in the
make.fun bars-replay simulation, starting from **$1,000 of paper money**. It
reads the replayed price bars, decides when to buy and sell, and reports its
final equity at the end of the 24-hour window.

## Strategy

Long only, one position at a time, full-size buys.

- **Enter:** when the fast EMA (55) crosses above the slow EMA (165), and the
  60-minute momentum is at least +30 bps (0.30%). The momentum check confirms
  the uptrend before the bot commits.
- **Exit:** when the fast EMA crosses back below the slow EMA, or when the
  position hits a **150 bps take-profit** or a **150 bps stop-loss**
  (150 bps = 1.50%).
- **Slippage:** max 100 bps (1.00%) per fill.

In plain language: the bot buys when the short-term trend turns up and the
last hour already confirms upward momentum, and it gets out when the trend
turns back down or the trade has moved 1.5% in either direction.

## Files

- `main.py` — the bot.
- `vendor/makefun_bars.py` — the kit's vendored Python shim for the
  bars-replay simulation.

## How to run

```sh
python3 -P -s main.py
```

Standard library only. No network access, no clock access, fully
deterministic — the same bars always produce the same trades.

## Dev-window result

On the published 24-hour dev window:

- **Net PnL:** +$14.28 after all fees
- **Max drawdown:** 0.64%
- **Trades:** 2 (1 round trip)
- **Fees:** $0.81
