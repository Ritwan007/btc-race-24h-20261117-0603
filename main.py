"""CBBTC mean-reversion bot for agent-fun/bars-replay/v1 (make.fun btc-race).

Built for the btc-race-24h-20261117-0603 edition after measuring the
families that trade this kind of window. The dev window is a quiet,
rangebound tape: cbBTC oscillates inside a band about 2.5% wide, the
1-minute close-to-close standard deviation is only 6.4 bps, and there is
not one single-bar drop of 35 bps in 1,440 bars. On such a tape every
active shape the kit ships bleeds through the roughly 13-26 bps a round
trip costs (the house ema-cross baseline grades -106.21, rsi-bollinger
-24.25, adx-momentum -32.66 on this window), and every trend or breakout
variant measured in the build screen loses too. What the tape does pay
for is patience at the band's lower edge:

- watch the trailing 360-bar (six-hour) mean of closes
- when a close prints at least 50 bps under that mean, buy with 80% of
  cash: the window's dips below its own six-hour mean are dislocations,
  not legs, and they close back
- sell the whole position on the first close back at or above the mean
- the only other exits are a -150 bps disaster stop under the true fill
  price and a 360-bar time exit, both far outside the noise this tape
  makes around its mean

Measured on the dev window with the kit's own fill math (protocol
driver, two runs byte-identical): net PnL +8.278476 over 4 round trips
(8 fills), max drawdown 0.579%, fees 2.570862. The pocket around the
chosen point is broad, not a spike: 216 of 225 neighbouring cells of
(lookback, entry, stop, size) are positive, the same shape at 65% size
makes +7.6798, and run standalone on each half of the window the chosen
configuration makes +6.9153 and +1.3632. No round trip carries the
result alone (the four made +0.45, +3.17, +3.30 and +1.37). The full
measurement table, including every losing family, is in FINDINGS.md.

Integer math only. No clock, no network, no randomness, no environment:
the same hello and the same batches always produce the same orders.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor"))
import makefun_bars

SYMBOL = "CBBTC"
BPS = 10_000

LOOKBACK = 360            # bars in the trailing mean (six hours of minutes)
ENTRY_BPS = 50            # buy a close this far under the trailing mean
SIZE_BPS = 8_000          # share of cash one entry spends (80%)
STOP_BPS = 150            # disaster stop under the fill price
MAX_HOLD_BARS = 360       # time exit: never park a trade longer than this
BUY_MAX_SLIPPAGE_BPS = 100   # a dip that already snapped back is not chased
SELL_MAX_SLIPPAGE_BPS = 500  # exits retry patiently, but not without a cap


class MeanReversion:
    """The strategy's whole state: the closes so far and the open trade.

    entry_price is the price the buy actually filled at (from the fill
    the harness reports on the next batch), never the close the order
    was decided on, so the stop is measured against what the position
    really cost. The exit at the mean needs no fill price: it compares
    closes with closes.
    """

    def __init__(self):
        self.closes = []          # closes of every bar before the current one
        self.window_sum = 0       # sum of the last LOOKBACK closes, kept incrementally
        self.entry_price = None   # fill price of the open position
        self.bars_held = 0        # batches since the position appeared
        self.pending_buy = False  # a buy was sent, not yet resolved

    def learn_fills(self, batch):
        """Fold in the fills of the orders decided on the previous batch.

        A pending buy is resolved by its own record in this batch: filled
        opens the trade; rejected drops the idea (the dip recovered past
        the buy's max_slippage without us). A filled sell closes the
        trade; the harness's own end-of-window flatten needs no
        bookkeeping here.
        """
        for fill in batch["fills"]:
            side = fill.get("side")
            if side == "buy" and self.pending_buy:
                self.pending_buy = False
                if fill.get("status") == "filled":
                    self.entry_price = int(fill["price"])
                    self.bars_held = 0
            elif side == "sell" and fill.get("status") == "filled":
                self.entry_price = None
                self.bars_held = 0

    def trailing_mean_sum(self, close):
        """Sum of the last LOOKBACK closes including the current one.

        Kept as a sum, not a mean, so every comparison below is exact
        integer math: close is ENTRY_BPS under the mean exactly when
        (sum - close * LOOKBACK) * BPS >= ENTRY_BPS * sum.
        """
        total = self.window_sum + close
        if len(self.closes) >= LOOKBACK:
            total -= self.closes[-LOOKBACK]
        return total

    def entry_order(self, state, close):
        """The buy for this bar's dip under the mean, or None."""
        if len(self.closes) + 1 < LOOKBACK:
            return None
        total = self.trailing_mean_sum(close)
        if (total - close * LOOKBACK) * BPS < ENTRY_BPS * total:
            return None
        spend = state.cash * SIZE_BPS // BPS
        room = state.weight_room(SYMBOL)
        if spend > room:
            spend = room
        if spend < int(state.hello["fees"]["min_notional_quote_units"]):
            return None
        self.pending_buy = True
        return {
            "side": "buy",
            "symbol": SYMBOL,
            "notional_quote_units": spend,
            "max_slippage_bps": BUY_MAX_SLIPPAGE_BPS,
        }

    def manage_exit(self, holding, close):
        """The sell for an open trade, or None while it should keep running.

        Three exits, whichever comes first, each selling the whole
        position:

        - reversion complete: the close is back at or above the same
          trailing mean the entry was measured against
        - disaster stop: -150 bps under the fill price, far outside the
          band noise (on the dev window it never fired; every exit was
          the reversion)
        - time: 360 bars held without either, so capital is never parked
          in a position the tape forgot

        A sell the market refuses (its fill would land more than
        SELL_MAX_SLIPPAGE_BPS under the close it was decided on) leaves
        the position in place, and the same test runs again on the next
        bar: the exit intent retries until it fills.
        """
        total = self.trailing_mean_sum(close)
        reverted = close * LOOKBACK >= total
        stopped = self.entry_price is not None and \
            close * BPS <= self.entry_price * (BPS - STOP_BPS)
        expired = self.bars_held >= MAX_HOLD_BARS
        if not (reverted or stopped or expired):
            return None
        return {
            "side": "sell",
            "symbol": SYMBOL,
            "qty": holding.qty,
            "max_slippage_bps": SELL_MAX_SLIPPAGE_BPS,
        }

    def on_batch(self, state, batch):
        """Answer one batch: manage the open trade, else look for a dip."""
        self.learn_fills(batch)
        holding = state.positions.get(SYMBOL)
        bar_here = any(bar["symbol"] == SYMBOL for bar in batch["bars"])
        close = state.close(SYMBOL) if bar_here else None
        orders = []
        if state.warming_up:
            pass  # orders would be rejected; just build the close history
        elif holding is not None and self.entry_price is not None and close is not None:
            self.bars_held += 1
            sell = self.manage_exit(holding, close)
            if sell is not None:
                orders.append(sell)
        elif holding is None and not self.pending_buy and close is not None:
            buy = self.entry_order(state, close)
            if buy is not None:
                orders.append(buy)
        if bar_here:
            self.closes.append(close)
            self.window_sum += close
            if len(self.closes) > LOOKBACK:
                self.window_sum -= self.closes[-LOOKBACK - 1]
        return orders


def main():
    bot = MeanReversion()
    makefun_bars.run(bot.on_batch)


if __name__ == "__main__":
    main()
