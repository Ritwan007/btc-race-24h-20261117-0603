# cbBTC Mean-Reversion Bot — make.fun btc-race-24h-20261117-0603

![competition](https://make.fun/badge/btc-race-24h-20261117-0603.svg)
![rank](https://make.fun/badge/btc-race-24h-20261117-0603/Ritwan007/btc-race-24h-20261117-0603/rank.svg)
![reward](https://make.fun/badge/btc-race-24h-20261117-0603/Ritwan007/btc-race-24h-20261117-0603/reward.svg)

A bot for the make.fun competition
[Race a BTC trading bot live for 24 hours](https://make.fun/bounty/btc-race-24h-20261117-0603):
it trades Coinbase Wrapped BTC (cbBTC) against USDC on 1-minute
on-chain bars with $1,000 of paper money, speaking
agent-fun/bars-replay/v1.

## Strategy

Mean reversion against a six-hour trailing mean, built for a quiet,
rangebound tape (the full measurement record is in
[FINDINGS.md](FINDINGS.md)):

- buy with 80% of cash when a close prints at least 50 bps under the
  trailing 360-bar mean of closes
- sell the whole position on the first close back at or above that mean
- disaster stop at −150 bps under the true fill price, and a 360-bar
  time exit — neither fired on the dev window

Dev window, driver-verified with the kit's own fill math: net PnL
**+8.278476 USDC**, 8 fills, max drawdown 0.579%.

## Layout

- `main.py` — the bot (Python 3.13, standard library only)
- `vendor/makefun_bars.py` — the kit's protocol SDK shim, byte-identical
- `FINDINGS.md` — the window analysis and every variant measured

## License

MIT — see [LICENSE](LICENSE).
