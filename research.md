# Setup research - 2026-10-25

Train: before 2025-10-23. Test: after (held out). Results in R after 0.25% costs.

**Pass rules:** train n >= 100 and avgR > 0.1; test n >= 30 and avgR >= 0.0; train still positive without its best year; test drawdown <= 15R (portfolio of max 5 open trades, same-day signals by momentum - test_taken/taken_avgR are those trades, and taken_avgR must also be >= 0.0); a filter must beat the unfiltered setup (same exit/stop) in test.

576 combinations tested. Note: testing many combinations means some pass by luck.

## Validated (saved to validated_setups.json)

| setup | exit | stop | train_n | train_avgR | ex_best_yr | test_n | test_avgR | test_win | test_taken | taken_avgR | test_DD_R |
|---|---|---|---|---|---|---|---|---|---|---|---|
| breakout+deliv_not_low | chandelier | 2.0 | 1458 | 0.369 | 0.044 | 338 | 0.154 | 0.317 | 70 | 0.145 | 12.0 |
| pullback+accumulation | chandelier | 1.5 | 1951 | 0.425 | 0.063 | 485 | 0.009 | 0.297 | 78 | 0.339 | 11.8 |

## All passing combinations (32)

| setup | exit | stop | train_n | train_avgR | ex_best_yr | test_n | test_avgR | test_win | test_taken | taken_avgR | test_DD_R |
|---|---|---|---|---|---|---|---|---|---|---|---|
| breakout+deliv_not_low | chandelier | 2.0 | 1458 | 0.369 | 0.044 | 338 | 0.154 | 0.317 | 70 | 0.145 | 12.0 |
| breakout+market_up | chandelier | 1.5 | 2841 | 0.492 | 0.128 | 210 | 0.118 | 0.29 | 33 | 0.733 | 6.3 |
| breakout+deliv_not_low | chandelier | 3.0 | 1458 | 0.285 | 0.034 | 338 | 0.084 | 0.331 | 67 | 0.009 | 13.3 |
| breakout+deliv_not_low | ema_trail | 3.0 | 1458 | 0.358 | 0.029 | 338 | 0.071 | 0.317 | 61 | 0.181 | 9.7 |
| breakout+crude_calm | chandelier | 2.0 | 2763 | 0.389 | 0.088 | 494 | 0.071 | 0.322 | 66 | 0.301 | 12.1 |
| breakout+market_up | chandelier | 2.0 | 2841 | 0.412 | 0.121 | 210 | 0.066 | 0.319 | 27 | 0.167 | 6.3 |
| breakout+accumulation | chandelier | 2.0 | 1105 | 0.352 | 0.026 | 273 | 0.059 | 0.286 | 74 | 0.1 | 15.0 |
| breakout+crude_calm | ema_trail | 2.0 | 2763 | 0.478 | 0.091 | 494 | 0.051 | 0.314 | 66 | 0.004 | 13.8 |
| breakout+sector_top | ema_trail | 2.0 | 1150 | 0.407 | 0.018 | 289 | 0.049 | 0.311 | 64 | 0.171 | 11.8 |
| breakout+sector_top | ema_trail | 1.5 | 1150 | 0.494 | 0.017 | 290 | 0.044 | 0.279 | 74 | 0.36 | 12.7 |
| breakout+inr_stable | chandelier | 2.0 | 2839 | 0.4 | 0.103 | 492 | 0.042 | 0.305 | 66 | 0.498 | 11.9 |
| breakout+crude_calm | chandelier | 3.0 | 2763 | 0.286 | 0.068 | 494 | 0.039 | 0.342 | 59 | 0.167 | 7.6 |
| breakout+accumulation | chandelier | 3.0 | 1105 | 0.26 | 0.019 | 273 | 0.024 | 0.304 | 64 | 0.137 | 7.8 |
| breakout+yields_calm | chandelier | 3.0 | 2577 | 0.304 | 0.09 | 564 | 0.02 | 0.333 | 62 | 0.111 | 7.4 |
| breakout+crude_calm | ema_trail | 3.0 | 2763 | 0.353 | 0.073 | 494 | 0.019 | 0.322 | 62 | 0.019 | 9.5 |
| breakout+breadth_ok | ema_trail | 2.0 | 2828 | 0.497 | 0.117 | 378 | 0.015 | 0.307 | 45 | 0.32 | 5.9 |
| breakout+sector_top | fixed | 3.0 | 1150 | 0.342 | 0.118 | 285 | 0.013 | 0.432 | 52 | 0.134 | 6.7 |
| breakout+inr_stable | chandelier | 3.0 | 2839 | 0.291 | 0.076 | 492 | 0.013 | 0.327 | 61 | 0.234 | 8.9 |
| breakout+sector_top | fixed | 2.0 | 1150 | 0.288 | 0.084 | 288 | 0.012 | 0.396 | 75 | 0.102 | 10.4 |
| breakout+yields_calm | ema_trail | 2.0 | 2577 | 0.518 | 0.122 | 564 | 0.011 | 0.303 | 73 | 0.035 | 13.7 |
| breakout+sector_top | breakeven | 3.0 | 1150 | 0.291 | 0.089 | 286 | 0.01 | 0.374 | 58 | 0.182 | 5.3 |
| breakout+sector_top | ema_trail | 3.0 | 1150 | 0.287 | 0.003 | 289 | 0.01 | 0.315 | 61 | 0.111 | 9.4 |
| pullback+accumulation | chandelier | 1.5 | 1951 | 0.425 | 0.063 | 485 | 0.009 | 0.297 | 78 | 0.339 | 11.8 |
| breakout+breadth_ok | ema_trail | 1.5 | 2828 | 0.594 | 0.136 | 378 | 0.008 | 0.275 | 55 | 0.546 | 11.2 |
| breakout | chandelier | 3.0 | 2902 | 0.287 | 0.072 | 583 | 0.005 | 0.328 | 66 | 0.076 | 8.5 |
| breakout+crude_calm | fixed | 3.0 | 2763 | 0.348 | 0.16 | 491 | 0.005 | 0.436 | 56 | 0.096 | 9.3 |
| breakout+yields_calm | fixed | 3.0 | 2577 | 0.367 | 0.176 | 559 | 0.005 | 0.44 | 59 | 0.224 | 6.7 |
| breakout+breadth_ok | ema_trail | 3.0 | 2828 | 0.363 | 0.088 | 378 | 0.004 | 0.32 | 45 | 0.165 | 4.5 |
| breakout+yields_calm | breakeven | 3.0 | 2577 | 0.316 | 0.145 | 561 | 0.004 | 0.381 | 66 | 0.097 | 9.3 |
| breakout+crude_calm | breakeven | 3.0 | 2763 | 0.299 | 0.127 | 491 | 0.003 | 0.373 | 64 | 0.025 | 8.2 |
| pullback+accumulation | chandelier | 2.0 | 1951 | 0.33 | 0.037 | 484 | 0.003 | 0.329 | 72 | 0.194 | 9.9 |
| pullback+accumulation | chandelier | 3.0 | 1951 | 0.234 | 0.034 | 481 | 0.002 | 0.339 | 65 | 0.207 | 5.7 |

## Closest misses (failed one rule)

| setup | exit | stop | train_n | train_avgR | ex_best_yr | test_n | test_avgR | test_win | test_taken | taken_avgR | test_DD_R | failed |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| breakout+oversold | chandelier | 3.0 | 171 | 0.432 | 0.21 | 29 | 0.215 | 0.207 | 28 | 0.255 | 8.6 | test n 29 < 30 |
| breakout+deliv_not_low | ema_trail | 2.0 | 1458 | 0.471 | 0.038 | 338 | 0.129 | 0.311 | 71 | 0.11 | 15.4 | test drawdown 15.4R > 15R |
| breakout+deliv_high | ema_trail | 2.0 | 680 | 0.424 | -0.084 | 171 | 0.126 | 0.269 | 62 | 0.191 | 13.5 | train without best year -0.084 <= 0 |
| breakout+oversold | fixed | 3.0 | 171 | 0.38 | 0.221 | 29 | 0.124 | 0.483 | 26 | 0.195 | 4.1 | test n 29 < 30 |
| breakout+accumulation | ema_trail | 2.0 | 1105 | 0.456 | -0.026 | 273 | 0.103 | 0.278 | 68 | 0.055 | 12.0 | train without best year -0.026 <= 0 |
| breakout+accumulation | chandelier | 1.5 | 1105 | 0.434 | 0.047 | 274 | 0.094 | 0.259 | 80 | 0.425 | 18.5 | test drawdown 18.5R > 15R |
| breakout+crude_calm | chandelier | 1.5 | 2763 | 0.465 | 0.088 | 496 | 0.075 | 0.288 | 78 | 0.579 | 18.3 | test drawdown 18.3R > 15R |
| breakout+deliv_not_low | ema_trail | 1.5 | 1458 | 0.574 | 0.019 | 340 | 0.062 | 0.268 | 86 | 0.053 | 20.9 | test drawdown 20.9R > 15R |
| breakout+deliv_high | ema_trail | 3.0 | 680 | 0.31 | -0.066 | 171 | 0.056 | 0.275 | 59 | 0.145 | 7.3 | train without best year -0.066 <= 0 |
| breakout+accumulation | ema_trail | 3.0 | 1105 | 0.34 | -0.012 | 273 | 0.051 | 0.286 | 62 | 0.113 | 7.2 | train without best year -0.012 <= 0 |
