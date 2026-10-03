# Data manifest (pre-holdout audit)

Audit run: `p01-data-audit-20261002T162128Z-40820a9`
Source read-only path: `/home/xaume/SQX_CLAUDE_FOREX/data/raw`
Policy: `configs/splits.yaml`, local `Europe/Athens`, half-open intervals.

The auditor streamed each file only through `2022-12-30 23:45:00`. It stopped
before parsing the first `2023-01-01 00:00:00` payload. Consequently the final
holdout row count and checksum are intentionally `sealed/None`; this document
does not reveal its last available candle.

## Series audit

| Symbol | First accessible | Last accessible | Dev rows | Dev-WF rows | Procedure rows | Gaps | Weekend gaps | Unexpected gaps | Max gap (min) |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| EURUSD | 2003-05-05 03:00 | 2022-12-30 23:45 | 291701 | 99664 | 99820 | 1087 | 917 | 170 | 4335 |
| GBPUSD | 2003-05-05 03:00 | 2022-12-30 23:45 | 291673 | 99662 | 99815 | 1083 | 917 | 166 | 4335 |
| NZDUSD | 2003-08-04 03:00 | 2022-12-30 23:45 | 285199 | 99652 | 99809 | 1108 | 904 | 204 | 4335 |
| USDCAD | 2003-08-04 03:00 | 2022-12-30 23:45 | 285348 | 99662 | 99811 | 1096 | 904 | 192 | 4335 |
| USDCHF | 2003-05-05 03:00 | 2022-12-30 23:45 | 291568 | 99664 | 99783 | 1106 | 917 | 189 | 4335 |
| USDJPY | 2003-05-05 03:00 | 2022-12-30 23:45 | 291591 | 99662 | 99818 | 1086 | 911 | 175 | 4335 |
| XAUUSD | 2003-05-05 03:00 | 2022-12-30 23:45 | 286087 | 94499 | 94605 | 5192 | 939 | 4253 | 4590 |

`XAUUSD` is detected but is not in the configured FX universe and is not used
by the pipeline. Gaps are reported, never filled; weekend gaps are only the
simple Friday-to-Monday classification. Unexpected gaps still require
broker-calendar classification before continuity is accepted.

## SHA256 of accessible raw partition lines

Hashes cover the exact raw CSV lines in each accessible partition. They are not
whole-file hashes, because hashing the sealed suffix would be premature.

| Symbol | DEV/TRAIN | DEVELOPMENT WF | PROCEDURE VALIDATION | FINAL HOLDOUT |
|---|---|---|---|---|
| EURUSD | `01218f966fc6599f7db7d4daae302bea5c0de745082eafeefc987fa8e59b01dc` | `ece477ce7f99810091dfe8b7430fbf2de981ea550f0e49e5abc40385c79f8cfc` | `cab6a503ce9cca426e767bcc1eccc69a601d5b3e4f38af1eea74b7f96d5c8f8e` | sealed / None |
| GBPUSD | `7db89460e27c05f6fb4a73f1eaeba3ea6c13e0348534cf57b9bb8162fb108586` | `86e9d6dabf6a3400a0afee5cdac1fd362817451672aae64363e095c20e7bab42` | `45d75b459613c20580539f564aecfe0547d13b4a60b0774d1116137e2dd78f07` | sealed / None |
| NZDUSD | `a145c4d5345dd503e15bad4e18f797f3ae1f4284c2c212a1d8df17b797108e80` | `e70547a7119515933c9b04c0985a76b2b535198cb81f17cbdecd175d352c0779` | `ff4a681bdc17403e499e49e12867a35eea4afe8962e0d25fe7c1e94643dcc87f` | sealed / None |
| USDCAD | `8134e20e745a09cd171eec3ed10cf6f04bae13e0416fdc2ad423103de552948b` | `3e6de51da8b3dd11d8ebd1fb6ead5ae4e1d1ebf9f10859f3d993b35f21873948` | `c39473db3e0c5344f9d1b0793f11a6695c6e7670241542c9aaf215c161c2090f` | sealed / None |
| USDCHF | `876e3ad51fa094ed8b0c138fa43efaf7603a664742923b657b6f896ed7815ad0` | `b9191478cba91545ef1bda6d4a6af6e8ea15a02f4d7a0250e30ad1de458fc9b7` | `9f1de2c42d908f50c1d974b8866c1d5e51ce0b8a1a27872ae3d11649889d8c0a` | sealed / None |
| USDJPY | `b8951d38346887fc1aede331fd4b6036a4f377ea7fc8136d79b038e947af1396` | `a35c6359b2555d4984b600634d3ef4510327ea789df55d00f055e15b45c0c785` | `b3814f89f61789efb7648a0b9323b309ef4203044b42e3cbfcf592c0c8517ce8` | sealed / None |
| XAUUSD | `9c0bf805b655069737b5efdcf7d59882a6c337949aa35976af7b942ba2f840c1` | `a5ad98c9e8da1c878f4e68566904da5cf234fbe8dbb7ec6ab0e84f3c605eae61` | `44cdbfc0a2d5351cb1cdd3da6828f421586e282575a816b8c782661e28bae5dc` | sealed / None |

Spread, bid/ask, rollover and broker execution specifications are not present
in these OHLCV files. They must be supplied or explicitly modelled before any
selection or performance claim.

## Symbol specifications

| Symbol | Instrument scope | Price decimal / pip convention | Volume |
|---|---|---|---|
| EURUSD, GBPUSD, USDCHF, USDCAD, NZDUSD | configured FX universe | 5 decimals, `pip=0.0001` | provider tick-volume, not comparable |
| USDJPY | configured FX universe | 3 decimals, `pip=0.01` | provider tick-volume, not comparable |
| XAUUSD | detected, excluded from FX phases | 2 decimals; separate instrument convention required | provider tick-volume, not comparable |

The raw files do not contain bid/ask, spread or rollover fields. The existing
overflow guard for provider volume is retained in `configs/data.yaml`; volume is
not part of the strategy grammar.

## Local EURUSD P02–P04 input

The first authorised local execution uses the pre-holdout file
`data/raw/EURUSD_15M.csv`:

| File | M15 rows | Derived H1 rows | Coverage | Period | SHA256 |
|---|---:|---:|---:|---|---|
| `data/raw/EURUSD_15M.csv` | 491,185 | 122,817 | 99.9642% | 2003-05-05 through 2022-12-30 | `29e4b0148de66dae4a23dabb9464365ce68bfcf0901de9cf4037b33ad731adf4` |

This artifact ends before the configured final-holdout boundary and is the
only symbol used by the first real P02–P04 run. Generation and selection are
restricted to `dev_train`, `[2003-01-01, 2015-01-01)`; no later partition is
loaded by the run orchestrator.
