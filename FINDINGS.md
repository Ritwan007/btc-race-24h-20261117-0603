# Findings — btc-race-24h-20261117-0603

## The window

The dev window (1,440 one-minute cbBTC bars, the 24 hours ending at the
2026-11-17T06:03Z opening) is a quiet, rangebound tape: 64,461.04 →
64,775.95 (+0.489%), high 65,466.84, low 63,874.36 — a band about 2.5%
wide. The 1-minute close-to-close standard deviation is 6.4 bps; only
18 bars move 20 bps or more and only 3 move 35 bps or more (all rises);
there is **no single-bar drop of 35 bps in the whole window**. 171 bars
are perfectly flat. Four-hour blocks: −0.23 / −0.39 / +1.13 / +1.04 /
−1.01 / −0.03%. Lag-1 autocorrelation of 1-minute returns is +0.153.

## Measurement method

Every number below comes from the kit's own fill math (fee 4 bps,
slippage 2 bps, constant-product impact against each bar's open depth,
fills at the next bar's open, end-of-window flatten at the last close).
The in-process simulator used for screening was cross-validated against
the kit's `grade-local` on this exact window before any variant was
trusted: buy-and-hold grades **+1.067187** (1 trade, max DD 2.1189434%,
fees 0.800588) by grade-local and by the simulator, to the micro-USDC.
Finalists were then re-measured as real bots through a protocol driver
(hello/batches/fills over stdio, two runs, reply streams byte-identical
for every bot). grade-local cannot run a Python bot on this machine
(its process driver is node-only and Docker is absent), so the driver
numbers are the verified ones for the Python finalists.

## Baselines (grade-local, this window)

| Bot | Net PnL | Trades | Max DD | Fees |
|---|---|---|---|---|
| buy-and-hold (house) | +1.067187 | 1 | 2.119% | 0.800588 |
| momentum (house) | +2.445627 | 1 | 2.119% | 0.801139 |
| hold-cash (house) | 0.000000 | 0 | 0% | 0 |
| ema-cross (house) | −106.214838 | 68 | 10.96% | 25.737382 |
| rsi-bollinger | −24.252523 | 11 | 2.79% | 4.752530 |
| adx-momentum | −32.655586 | 26 | 3.60% | 10.261969 |

## Variants (driver-verified real bots)

| Variant | Net PnL | Trades | Max DD | Fees |
|---|---|---|---|---|
| **Mean reversion 360/50, exit at mean, stop −150, 80% (this repo)** | **+8.278476** | 8 | 0.579% | 2.570862 |
| Profit-lock hold (lock +100, trail 60, stop −180) | +4.362282 | 2 | 1.734% | 0.801906 |
| Slow confirmed hold (mean120 + ret240 ≥ +20, stop −250) | +2.109737 | 1 | 2.119% | 0.801005 |
| Staged hold (60% + add on −45 bps pullback, stop −200) | +1.023263 | 2 | 2.119% | 0.800570 |
| Donchian breakout 120, trail 80, stop −200 | −17.650025 | 7 | 1.989% | 3.170901 |
| Patient dip buyer (the 20261115-0828 entry, unchanged) | 0.000000 | 0 | 0% | 0 |

## Screened in-process (same simulator; all on the full window)

- EMA trend 8/21 −106.95 · 20/60 −68.74 · 30/120 −49.10 · 60/240 −40.01 · 45/180 −24.17
- Trailing momentum holds (look 30–240, thresholds 20–40 bps): −1.04 to −3.33; with a −60 bps exit: −18.04
- Breakout holds (120–300-bar highs, trails 60–120): −7.28 to −18.54
- Confirmed holds (other parameter cells): −3.33 to −1.03
- Staged holds (other cells): +0.57 to +0.97
- Profit-lock (other cells): one identical +4.3623 event for every lock 90–120 / trail 60 cell; the +150/80 cell −0.24
- Mean reversion, lookback 120 / entry 40: −0.78 (12 trades — too twitchy)
- Dip buyer ≥20 bps, TP +25, stop −120, 40%: −6.01 (6 trades)

## Why the chosen shape is trusted

- **Broad pocket, not a spike.** Around (lookback 360, entry 50 bps,
  exit at mean): 216 of 225 cells of lookback {300…420} × entry
  {40…60} × stop {120,150,200} × size {40,50,65%} are positive; with a
  fixed take-profit instead of the mean exit, 36 of 36 cells are
  positive. The −150 stop never fired on this window at any size (all
  exits were the reversion), so the result does not rest on it.
- **Both halves positive.** Standalone on bars 0–719 the chosen
  configuration makes +6.9153; on bars 720–1439, +1.3632. (The
  profit-lock runner-up fails this test: +4.3623 / −5.7805 — it is one
  good first leg, and was rejected for exactly that.)
- **No single lucky trade.** The 4 round trips made +0.45, +3.17,
  +3.30 and +1.37 (fills at bars 366/464, 487/492, 574/583, 1082/1286).
- **Size curve is smooth.** 50% → +6.6409, 65% → +7.6798, 80% →
  +8.2785, 90% → +8.4309, 100% → +8.3898 (impact starts to bite). 80%
  was chosen under the peak, not at it.
- **Guardrails.** 8 fills ≥ 1 trade; max drawdown 0.579% ≤ 25%.
- **Not a house-bot clone.** Its action log (4 buys at 80% of cash, 4
  sells at the mean) matches no baseline's; buy-and-hold and the house
  momentum bot never sell before the flatten.

## Honest limits

The dev window rewards this shape because it is rangebound. The race
window is unseen: in a strongly trending 24 hours a mean-reversion bot
earns less than a hold (its entries wait for dips that may not come,
and its exits cap each trade at the mean), and in a falling tape its
−150 bps stop and 360-bar time exit bound each trade's loss to about
1.5% of the position. What the dev number certifies is only the gate:
this entry made money on the dev window, so it races.
