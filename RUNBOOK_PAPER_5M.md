# Paper-Trading Runbook (5m) — Production / Paper-Only / No-Change

## 0) Scope & Hard Constraints
- **[System]** 5m stack only: Data → Features → Targets → XGB Training → Signals → Execution (paper-only) → Backtest → Paper-Gate
- **[Prohibitions]**
  - **NO** live trading
  - **NO** retraining
  - **NO** parameter tuning
  - **NO** execution changes (SL/TP/fees/slippage fixed)
  - **NO** threshold change (`0.55` fixed)
- **[Single Source of Truth]** `python main.py paper-gate-5m` output is the only GO/NO-GO decision tool.
- **[Operator Authority]** Operator can only:
  - start/stop paper
  - collect logs
  - escalate incidents
  - restore data pipelines

---

## 1) Daily Checklist (Before Market) — Pre-Start

### 1.1 Mandatory command sequence (no deviations)
Run in order (all must return exit code `0`):
- **[Data verify]** `python main.py verify-datasets-5m --config <config>`
- **[Features verify]** `python main.py verify-features-5m --config <config>`
- **[Targets verify]** `python main.py verify-targets-5m --config <config>`
- **[Signals verify]** `python main.py verify-signals-5m --config <config>`
- **[Executions verify]** `python main.py verify-executions-5m --config <config>`
- **[Backtest verify]** `python main.py verify-backtest-5m --config <config>`
- **[Paper Gate]** `python main.py paper-gate-5m --config <config>`

### 1.2 Acceptable ranges (must be TRUE in gate checklist)
From `paper-gate-5m` JSON:
- **[Profit Factor]** `profit_factor >= 1.15`
- **[Max Drawdown]** `max_drawdown <= 0.20`
- **[Trades/day]** `5 <= trades_per_day <= 20`
- **[WinRate]** `0.52 <= winrate <= 0.56`
- **[Worst window]** `worst_window_return >= -0.06`
- **[Stability]**
  - `pct_windows_pf_ge_1_1 >= 0.70`
  - `two_consecutive_pf_lt_0_9 == false`
  - `vshape_detected == false`
- **[Cost pressure]** `avg_gross_pnl_per_trade >= 2 * avg_cost_per_trade`
- **[Freshness]**
  - `ohlcv_lag_le_1_candle == true`
  - `funding_lag_le_2_candles == true`
  - `oi_lag_le_2_candles == true`
  - `sentiment_not_realtime == true`
- **[Safety configs exist]**
  - `ai_data/paper/kill_switch.json` exists
  - `ai_data/paper/drift_monitoring.json` exists
  - `ai_data/paper/latency_budget.json` exists

### 1.3 STOP conditions (pre-start)
Immediate NO-START if any of the following:
- **[Gate]** `paper-gate-5m` returns `NO-GO`
- **[Any verify fails]** any `verify-*` returns non-zero exit code
- **[Artifacts missing]** any required file missing:
  - `ai_data/backtests/backtest_5m.json`
  - `ai_data/backtests/equity_5m.parquet`
  - `ai_data/executions/executions_5m.parquet`
- **[Freshness fail]** any lag check fails
- **[Safety configs missing]** any of the 3 required `ai_data/paper/*.json` missing

### 1.4 Start authorization
Start paper only if:
- **[Gate verdict]** `verdict == "PAPER-GO"`
- **[Checklist]** all checklist items are `true`
- **[Operator sign-off]** operator records:
  - `run_date_utc`
  - gate JSON archived (see After Market)

---

## 2) Daily Checklist (After Market) — Post-Run

### 2.1 What to record (mandatory)
Archive the following files as-is (no edits):
- **[Gate snapshot]** output JSON of:
  - `python main.py paper-gate-5m --config <config>`
- **[Status snapshots]**
  - `python main.py dataset-status-5m --config <config>`
  - `python main.py feature-status-5m --config <config>`
  - `python main.py target-status-5m --config <config>`
  - `python main.py signal-status-5m --config <config>`
  - `python main.py execution-status-5m --config <config>`
  - `python main.py backtest-status-5m --config <config>`
- **[Paper safety configs]**
  - `ai_data/paper/kill_switch.json`
  - `ai_data/paper/drift_monitoring.json`
  - `ai_data/paper/latency_budget.json`
- **[Operational logs]**
  - last 24h application logs from configured log dir
  - any incident notes with timestamps

### 2.2 What to ignore (explicit)
- **[Ignore]** single-day PnL
- **[Ignore]** single-day winrate
- **[Ignore]** narrative explanations

### 2.3 Red flags (post-run)
Trigger incident workflow if any:
- **[Data]** any missing candles or timestamp gaps detected by validators
- **[Freshness]** any lag check fails at any time during session
- **[Safety]** kill-switch triggered (daily/weekly loss or losing streak rule)
- **[Equity integrity]** equity time index non-monotonic or NaN/inf
- **[Winrate drift]** winrate drops > 5% vs baseline gate winrate for 2 consecutive days
- **[Latency]** RTT p95 > 500 ms for any continuous 15-minute period

---

## 3) Weekly Review — Continue vs Stop

### 3.1 Required computations (no substitutions)
Compute using paper session logs and the system’s stored artifacts:
- **[Weekly trades/day]** total_trades / 7
- **[Weekly winrate]** wins / total_trades
- **[Weekly net PnL]** sum(net_pnl)
- **[Weekly profit factor]** sum(net profits) / abs(sum(net losses))
- **[Weekly max drawdown]** from weekly equity series
- **[Weekly median trade return]** median(net_pnl_per_trade)
  - **Acceptable:** `> 0`

### 3.2 Acceptable ranges (weekly)
Hard pass bands:
- **[Trades/day]** `5–20`
- **[WinRate]** `52–56%`
- **[Profit Factor]** `>= 1.10`
- **[Max DD]** `<= 20%`

### 3.3 Continue vs STOP (weekly decision)
- **[CONTINUE]** if all weekly ranges pass AND no hard-stop events occurred.
- **[STOP WEEK]** if any:
  - weekly `max DD > 20%`
  - weekly `profit factor < 1.0`
  - weekly trades/day outside `[5,20]` and cause is not explainable by verified data downtime
  - any “hard stop” event occurred (see section 5)

---

## 4) Incident Playbooks (Action-Only)

### 4.1 Data gap
- **[Detect]** any missing timestamps / verify failure / freshness fail
- **[Action]**
  - STOP paper immediately
  - re-run: `verify-datasets-5m`, `verify-features-5m`, `verify-targets-5m`, `verify-signals-5m`, `verify-executions-5m`, `verify-backtest-5m`
  - if any fail: NO restart

### 4.2 Latency spike
- **[Detect]** RTT > 300ms average OR p95 > 500ms
- **[Action]**
  - STOP paper immediately
  - do not restart until latency within budget for 30 consecutive minutes

### 4.3 Losing streak
- **[Detect]** 10 losing trades in a row
- **[Action]**
  - COOLDOWN 24h (no trades)

### 4.4 Sudden winrate drop
- **[Detect]** winrate down > 5% vs baseline gate winrate for 2 consecutive days
- **[Action]**
  - PAUSE paper immediately (no new trades allowed)

### 4.5 Drift alert
- **[Detect]** PSI threshold breach or p_buy/p_sell distribution shift beyond config
- **[Action]**
  - PAUSE immediately
  - no restart until explicit approval logged

---

## 5) Hard STOP Rules (No Override)
Immediate halt. No human override.
- **[Daily loss]** daily loss ≥ 3% → STOP DAY
- **[Weekly loss]** weekly loss ≥ 8% → STOP WEEK
- **[Losing streak]** 10 consecutive losing trades → COOLDOWN 24h
- **[Data missing / NaN]** any NaN/inf in live inputs or outputs → IMMEDIATE STOP
- **[Freshness fail]** lag thresholds violated → IMMEDIATE STOP
- **[Latency]** RTT p95 > 500ms for 15 minutes → IMMEDIATE STOP
- **[Gate fail]** `paper-gate-5m == NO-GO` at any pre-start check → NO START

---

## 6) Change Policy (Paper Phase)

### 6.1 Absolutely forbidden during paper
- retraining, recalibration, feature changes
- threshold change (`0.55`)
- execution changes (SL/TP/fees/slippage/state machine)
- backtest reruns with altered logic/windowing

### 6.2 What requires full reset + new backtest + new gate
Any change to any of:
- features schema
- targets definition
- training procedure/parameters
- signal logic
- execution logic
- backtest logic

---

## 7) Paper Exit Criteria (Success / Failure)

### 7.1 Minimum duration
- **[Minimum]** 2 weeks continuous paper operation without forbidden changes
- **[Preferred]** 4 weeks

### 7.2 Success criteria
All must be true for the full minimum duration:
- no hard stops
- `paper-gate-5m` remained `PAPER-GO` on every pre-start day
- zero data-gap incidents
- zero latency hard-stop incidents
- weekly review pass each week

### 7.3 Failure criteria
Any of:
- hard-stop events repeated twice in a 2-week window
- data freshness failures recurring on ≥ 3 days/week
- winrate out of `[0.52,0.56]` for 5 consecutive days
- weekly PF < 1.0 at any weekly review
- max DD > 20% at any point

---

## V-shape heuristic definition
- **V-shape definition:** `worst_window_return <= -6%` followed by the next window return `>= +6%`
