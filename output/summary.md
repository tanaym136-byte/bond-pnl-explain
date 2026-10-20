# Daily P&L attribution: results

Period: 02 Sep 2026 to 19 Oct 2026 (32 P&L days). Book: 10 bonds, 7 trades in the blotter. Opening risk: a 1bp rise in Treasury yields changes the book's value by -$14.2k, and a 1bp widening in credit spreads by -$30.9k.

## P&L by driver

| Driver | September | Period to date |
| --- | ---: | ---: |
| Accrual | +$193.9k | +$299.1k |
| Roll | +$22.4k | +$37.7k |
| Rates | -$803.9k | -$630.0k |
| Convexity | +$4.9k | +$6.1k |
| Credit | +$216.8k | -$32.6k |
| New trades | +$129.9k | +$133.9k |
| Amendments | -$120.0k | -$120.0k |
| Cancellations | +$0 | +$2.0k |
| Unexplained | -$682 | -$255 |
| Actual | -$356.6k | -$304.1k |

## How well the risk explains the P&L

* Days without an unexplained break: 29 of 32. On those days the average unexplained amount was $475; the three largest were $8.0k on 08 Oct, $906 on 10 Sep, $596 on 23 Sep.
* Share of gross daily P&L explained on those days: 99.4%.
* Days with an unexplained break: 3.
* Book value roll-forward: largest difference $0 across the three periods tested.

## Control exceptions

| Date | Control | Item | Detail |
| --- | --- | --- | --- |
| 2026-09-16 | Trade review (NEW) | T1002 A_UTIL_33 | price -2.95 pts from independent mark (tolerance 0.75) | P&L effect +$117.8k |
| 2026-09-17 | Trade review (AMEND) | T1002 A_UTIL_33 | Price corrected from 92.57 to 95.57: keying error, confirmed with trader | P&L effect -$120.0k |
| 2026-10-01 | Trade review (NEW) | T1005 UST_36 | possible duplicate of T1006 | P&L effect -$2.0k |
| 2026-10-01 | Trade review (NEW) | T1006 UST_36 | possible duplicate of T1005 | P&L effect -$2.0k |
| 2026-10-02 | Trade review (CANCEL) | T1006 UST_36 | Duplicate of T1005: trade message sent twice to the booking system | P&L effect +$2.0k |
| 2026-10-05 | IPV | BBB_NRG_45 | official 87.701 vs independent 87.554: +$11.7k |
| 2026-10-05 | Stale price | BBB_NRG_45 | official 87.701 unchanged; independent moved -0.147 |
| 2026-10-05 | Unexplained P&L | book | unexplained +$11.8k vs threshold +$10.0k |
| 2026-10-06 | IPV | BBB_NRG_45 | official 87.701 vs independent 87.835: -$10.7k |
| 2026-10-06 | Stale price | BBB_NRG_45 | official 87.701 unchanged; independent moved +0.280 |
| 2026-10-06 | Unexplained P&L | book | unexplained -$22.5k vs threshold +$10.0k |
| 2026-10-07 | Stale price | BBB_NRG_45 | official 87.701 unchanged; independent moved -0.229 |
| 2026-10-07 | Unexplained P&L | book | unexplained +$18.3k vs threshold +$10.0k |

## Book value roll-forward

| From | To | Opening value | P&L | Net cash received | Closing value | Difference |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| 2026-09-01 | 2026-09-30 | 34,272,292.75 | -356,644.71 | -420,521.09 | 34,336,169.13 | 0.00 |
| 2026-09-30 | 2026-10-19 | 34,336,169.13 | 52,568.52 | 7,924,365.76 | 26,464,371.88 | 0.00 |
| 2026-09-01 | 2026-10-19 | 34,272,292.75 | -304,076.19 | 7,503,844.67 | 26,464,371.88 | 0.00 |

## Daily commentary

* 02 Sep: +$170.3k: credit +$160.7k (BBB -5.1bp, BB -11.1bp); carry +$6.8k (accrual and roll-down)
* 03 Sep: +$19.1k: rates +$51.8k (10y -2bp); credit -$39.5k (BBB +0.9bp, BB +2.9bp)
* 04 Sep: -$15: rates -$30.4k (10y +1bp); credit +$24.0k (BBB -0.7bp, BB -1.7bp)
* 08 Sep: +$55.3k: credit +$38.8k (BBB -1.5bp, BB -2.9bp); carry +$26.9k (accrual and roll-down)
* 09 Sep: -$26.4k: rates -$43.5k (10y +3bp); credit +$10.6k (BBB -0.4bp, BB +0.9bp)
* 10 Sep: -$49.5k: rates -$175.2k (10y +12bp); credit +$109.7k (BBB -3.1bp, BB -9.3bp)
* 11 Sep: -$15.9k: rates -$51.7k (10y +1bp); credit +$27.9k (BBB -1.0bp, BB -5.9bp)
* 14 Sep: +$71.3k: credit +$66.4k (BBB -2.0bp, BB -2.1bp); carry +$22.9k (accrual and roll-down)
* 15 Sep: -$256.2k: credit -$214.0k (BBB +6.1bp, BB +12.2bp); rates -$50.4k (10y +3bp)
* 16 Sep: +$48.5k: new trades +$117.8k (day-one P&L); rates -$50.6k (10y +1bp)
* 17 Sep: +$49.8k: rates +$142.2k (10y -7bp); amendments -$120.0k (price corrections)
* 18 Sep: -$115.9k: rates -$131.3k (10y +7bp); carry +$8.3k (accrual and roll-down)
* 21 Sep: +$108.6k: rates +$62.3k (10y -5bp); carry +$25.1k (accrual and roll-down)
* 22 Sep: +$88.4k: credit +$68.3k (BBB -2.2bp, BB -5.9bp); rates +$11.7k (10y +0bp)
* 23 Sep: -$232.9k: rates -$276.1k (10y +15bp); credit +$33.5k (BBB -1.1bp, BB -1.2bp)
* 24 Sep: -$114.1k: rates -$84.4k (10y +7bp); credit -$37.3k (BBB +1.1bp, BB +4.3bp)
* 25 Sep: +$52.4k: rates +$40.3k (10y -1bp); carry +$7.4k (accrual and roll-down)
* 28 Sep: -$155.9k: rates -$129.4k (10y +7bp); credit -$48.7k (BBB +1.5bp, BB +3.7bp)
* 29 Sep: -$1.0k: rates -$14.7k (10y +2bp); carry +$7.4k (accrual and roll-down)
* 30 Sep: -$52.3k: rates -$44.3k (10y +3bp); credit -$15.0k (BBB +0.6bp, BB +1.5bp)
* 01 Oct: +$24.2k: rates +$107.1k (10y -5bp); credit -$86.2k (BBB +3.1bp, BB +4.8bp)
* 02 Oct: -$67.7k: rates -$39.1k (10y +4bp); credit -$36.6k (BBB +1.4bp, BB +3.1bp)
* 05 Oct: +$38.4k: credit +$26.4k (BBB -0.7bp, BB -1.1bp); carry +$18.0k (accrual and roll-down). UNEXPLAINED +$11.8k above threshold, investigate
* 06 Oct: +$55.3k: rates +$50.2k (10y -4bp); credit +$13.5k (BBB -0.5bp, BB +3.1bp). UNEXPLAINED -$22.5k above threshold, investigate
* 07 Oct: -$9.6k: credit -$32.8k (BBB +0.8bp, BB +1.6bp); carry +$6.3k (accrual and roll-down). UNEXPLAINED +$18.3k above threshold, investigate
* 08 Oct: -$80.5k: credit -$102.7k (BBB +2.2bp, BB +6.2bp); rates +$23.8k (10y -6bp)
* 09 Oct: +$15.3k: credit +$30.0k (BBB -0.3bp, BB +0.1bp); rates -$21.1k (10y +2bp)
* 13 Oct: +$48.9k: carry +$25.7k (accrual and roll-down); rates +$11.9k (10y -3bp)
* 14 Oct: -$35.6k: credit -$48.9k (BBB +1.3bp, BB +4.4bp); rates +$7.0k (10y -2bp)
* 15 Oct: +$124.7k: rates +$69.1k (10y -9bp); credit +$48.8k (BBB -1.1bp, BB -3.3bp)
* 16 Oct: +$48.0k: rates +$28.0k (10y -1bp); credit +$13.6k (BBB -0.8bp, BB +0.7bp)
* 19 Oct: -$108.9k: credit -$85.6k (BBB +2.9bp, BB +2.4bp); rates -$42.7k (10y +6bp)
