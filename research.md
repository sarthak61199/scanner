# Setup research - 2026-10-25

Train: before 2025-10-23. Test: after (held out). Results in R after 0.25% costs.

**Pass rules:** train n >= 100 and avgR > 0.1; test n >= 30 and avgR >= 0.0; train still positive without its best year; test drawdown <= 15R (portfolio of max 5 open trades, same-day signals by momentum - test_taken/taken_avgR are those trades, and taken_avgR must also be >= 0.0); a filter must beat the unfiltered setup (same exit/stop) in test.

396 combinations tested. Note: testing many combinations means some pass by luck.

## Validated (saved to validated_setups.json)

| setup | exit | stop | train_n | train_avgR | ex_best_yr | test_n | test_avgR | test_win | test_taken | taken_avgR | test_DD_R |
|---|---|---|---|---|---|---|---|---|---|---|---|
| breakout+deliv_not_low | chandelier | 2.0 | 1457 | 0.369 | 0.044 | 338 | 0.154 | 0.317 | 70 | 0.145 | 12.0 |
| pullback+accumulation | chandelier | 1.5 | 1951 | 0.425 | 0.063 | 485 | 0.009 | 0.297 | 78 | 0.339 | 11.8 |

## All passing combinations (20)

| setup | exit | stop | train_n | train_avgR | ex_best_yr | test_n | test_avgR | test_win | test_taken | taken_avgR | test_DD_R |
|---|---|---|---|---|---|---|---|---|---|---|---|
| breakout+deliv_not_low | chandelier | 2.0 | 1457 | 0.369 | 0.044 | 338 | 0.154 | 0.317 | 70 | 0.145 | 12.0 |
| breakout+market_up | chandelier | 1.5 | 2839 | 0.492 | 0.129 | 210 | 0.118 | 0.29 | 33 | 0.733 | 6.3 |
| breakout+deliv_not_low | chandelier | 3.0 | 1457 | 0.286 | 0.034 | 338 | 0.084 | 0.331 | 67 | 0.009 | 13.3 |
| breakout+deliv_not_low | ema_trail | 3.0 | 1457 | 0.359 | 0.029 | 338 | 0.071 | 0.317 | 61 | 0.181 | 9.7 |
| breakout+market_up | chandelier | 2.0 | 2839 | 0.413 | 0.122 | 210 | 0.066 | 0.319 | 27 | 0.167 | 6.3 |
| breakout+accumulation | chandelier | 2.0 | 1105 | 0.352 | 0.026 | 273 | 0.059 | 0.286 | 74 | 0.1 | 15.0 |
| breakout+sector_top | ema_trail | 2.0 | 1150 | 0.407 | 0.018 | 289 | 0.049 | 0.311 | 64 | 0.171 | 11.8 |
| breakout+sector_top | ema_trail | 1.5 | 1150 | 0.494 | 0.017 | 290 | 0.044 | 0.279 | 74 | 0.36 | 12.7 |
| breakout+accumulation | chandelier | 3.0 | 1105 | 0.26 | 0.019 | 273 | 0.024 | 0.304 | 64 | 0.137 | 7.8 |
| breakout+breadth_ok | ema_trail | 2.0 | 2826 | 0.498 | 0.117 | 378 | 0.015 | 0.307 | 45 | 0.32 | 5.9 |
| breakout+sector_top | fixed | 3.0 | 1150 | 0.342 | 0.118 | 285 | 0.013 | 0.432 | 52 | 0.134 | 6.7 |
| breakout+sector_top | fixed | 2.0 | 1150 | 0.288 | 0.084 | 288 | 0.012 | 0.396 | 75 | 0.102 | 10.4 |
| breakout+sector_top | breakeven | 3.0 | 1150 | 0.291 | 0.089 | 286 | 0.01 | 0.374 | 58 | 0.182 | 5.3 |
| breakout+sector_top | ema_trail | 3.0 | 1150 | 0.287 | 0.003 | 289 | 0.01 | 0.315 | 61 | 0.111 | 9.4 |
| pullback+accumulation | chandelier | 1.5 | 1951 | 0.425 | 0.063 | 485 | 0.009 | 0.297 | 78 | 0.339 | 11.8 |
| breakout+breadth_ok | ema_trail | 1.5 | 2826 | 0.595 | 0.136 | 378 | 0.008 | 0.275 | 55 | 0.546 | 11.2 |
| breakout | chandelier | 3.0 | 2900 | 0.287 | 0.073 | 583 | 0.005 | 0.328 | 66 | 0.076 | 8.5 |
| breakout+breadth_ok | ema_trail | 3.0 | 2826 | 0.363 | 0.088 | 378 | 0.004 | 0.32 | 45 | 0.165 | 4.5 |
| pullback+accumulation | chandelier | 2.0 | 1951 | 0.33 | 0.037 | 484 | 0.003 | 0.329 | 72 | 0.194 | 9.9 |
| pullback+accumulation | chandelier | 3.0 | 1951 | 0.234 | 0.034 | 481 | 0.002 | 0.339 | 65 | 0.207 | 5.7 |

## Closest misses (failed one rule)

| setup | exit | stop | train_n | train_avgR | ex_best_yr | test_n | test_avgR | test_win | test_taken | taken_avgR | test_DD_R | failed |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| breakout+oversold | chandelier | 3.0 | 171 | 0.432 | 0.21 | 29 | 0.215 | 0.207 | 28 | 0.255 | 8.6 | test n 29 < 30 |
| breakout+deliv_not_low | ema_trail | 2.0 | 1457 | 0.472 | 0.038 | 338 | 0.129 | 0.311 | 71 | 0.11 | 15.4 | test drawdown 15.4R > 15R |
| breakout+deliv_high | ema_trail | 2.0 | 680 | 0.424 | -0.084 | 171 | 0.126 | 0.269 | 62 | 0.191 | 13.5 | train without best year -0.084 <= 0 |
| breakout+oversold | fixed | 3.0 | 171 | 0.38 | 0.221 | 29 | 0.124 | 0.483 | 26 | 0.195 | 4.1 | test n 29 < 30 |
| breakout+accumulation | ema_trail | 2.0 | 1105 | 0.456 | -0.026 | 273 | 0.103 | 0.278 | 68 | 0.055 | 12.0 | train without best year -0.026 <= 0 |
| breakout+accumulation | chandelier | 1.5 | 1105 | 0.434 | 0.047 | 274 | 0.094 | 0.259 | 80 | 0.425 | 18.5 | test drawdown 18.5R > 15R |
| breakout+deliv_not_low | ema_trail | 1.5 | 1457 | 0.575 | 0.019 | 340 | 0.062 | 0.268 | 86 | 0.053 | 20.9 | test drawdown 20.9R > 15R |
| breakout+deliv_high | ema_trail | 3.0 | 680 | 0.31 | -0.066 | 171 | 0.056 | 0.275 | 59 | 0.145 | 7.3 | train without best year -0.066 <= 0 |
| breakout+accumulation | ema_trail | 3.0 | 1105 | 0.34 | -0.012 | 273 | 0.051 | 0.286 | 62 | 0.113 | 7.2 | train without best year -0.012 <= 0 |
| breakout+deliv_not_low | chandelier | 1.5 | 1457 | 0.439 | 0.041 | 340 | 0.048 | 0.268 | 87 | 0.027 | 32.5 | test drawdown 32.5R > 15R |
