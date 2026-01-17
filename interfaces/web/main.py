from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, PlainTextResponse, Response
import pandas as pd

from core.config import load_config
from core.exceptions import BinanceAITraderError
from core.logger import setup_logger
from data_pipeline.pipeline import validate_data
from features.pipeline import build_features
from market.pipeline import detect_regime_pipeline
from strategies.sim import run_strategy_sim
from targets.pipeline import build_targets
from training.pipeline import train_offline
from trading.paper_trading import paper_trade_once
from trading.copy_trading import copy_trade_once
from monitoring.alerts import read_last_alert
from monitoring.events import read_recent_events
from monitoring.metrics import read_metrics

app = FastAPI(title="Binance AI Trader")


def _ai_data_root() -> Path:
    return (Path.cwd() / "ai_data").resolve()


def _model_cards_root() -> Path:
    return (Path.cwd() / "model_registry" / "model_cards").resolve()


def _safe_ai_data_path(user_path: str | Path) -> Path:
    p = Path(user_path)
    if not p.is_absolute():
        p = (Path.cwd() / p).resolve()
    else:
        p = p.resolve()

    root = _ai_data_root()
    if root not in p.parents and p != root:
        raise HTTPException(status_code=400, detail="Path must be within ai_data/")
    return p


def _parse_paths(raw: str) -> list[str]:
    items = [p.strip() for p in raw.replace("\n", ",").split(",")]
    return [p for p in items if p]


def _load_and_setup_logger(config_path: str | Path):
    cfg = load_config(config_path)
    logger = setup_logger(cfg)
    return cfg, logger


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return """<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>Binance AI Trader</title>
  <style>
    body { font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Arial; margin: 24px; }
    .grid { display: grid; grid-template-columns: 1fr; gap: 16px; max-width: 980px; }
    .card { border: 1px solid #e5e7eb; border-radius: 10px; padding: 14px; }
    label { display:block; font-weight:600; margin-top:10px; }
    input, textarea, select { width: 100%; padding: 8px; margin-top: 6px; box-sizing: border-box; }
    button { margin-top: 12px; padding: 10px 12px; border-radius: 8px; border: 1px solid #111827; background: #111827; color: white; cursor: pointer; }
    pre { background: #0b1020; color: #e5e7eb; padding: 12px; border-radius: 10px; overflow:auto; }
    .muted { color: #6b7280; }
    .filelist { max-height: 220px; overflow: auto; border: 1px solid #e5e7eb; border-radius: 10px; padding: 10px; }
    .fileitem { padding: 6px 8px; border-radius: 8px; cursor: pointer; }
    .fileitem:hover { background: #f3f4f6; }
    .tabs { display:flex; gap:8px; }
    .tabbtn { padding: 8px 10px; border-radius: 8px; border:1px solid #e5e7eb; background:#fff; cursor:pointer; }
    .tabbtn.active { border-color:#111827; }
    iframe { width: 100%; height: 280px; border: 1px solid #e5e7eb; border-radius: 10px; background: #fff; }
    .row { display:grid; grid-template-columns: 1fr 1fr; gap: 12px; }
    @media (max-width: 820px) { .row { grid-template-columns: 1fr; } }
  </style>
</head>
<body>
  <h1>Binance AI Trader (Web)</h1>
  <p>Запускає існуючі пайплайни (ті ж, що CLI). Вводь шляхи локально на диску сервера.</p>

  <div class=\"grid\">
    <div class=\"card\">
      <h2>Config</h2>
      <label>config_path</label>
      <input id=\"config_path\" value=\"config/config.yaml\" />
    </div>

    <div class=\"card\">
      <h2>Monitoring</h2>
      <button onclick=\"loadHealth()\">health</button>
      <button onclick=\"loadMetrics()\">metrics</button>
      <button onclick=\"loadAlerts()\">alerts</button>
      <button onclick=\"loadEvents()\">events</button>
      <div class=\"muted\">Outputs to JSON tab.</div>
    </div>

    <div class=\"card\">
      <h2>ai_data browser</h2>
      <div class=\"muted\">Click a file to insert into the last focused input field.</div>
      <button onclick=\"loadFiles()\">Load ai_data files</button>
      <div id=\"files\" class=\"filelist\"></div>
    </div>

    <div class=\"card\">
      <h2>train-offline</h2>
      <div class=\"row\">
        <div>
          <label>inputs</label>
          <textarea id=\"to_inputs\" rows=\"2\"></textarea>
        </div>
        <div>
          <label>target_col</label>
          <input id=\"to_target\" value=\"future_log_return\" />
          <label>train_frac / val_frac</label>
          <input id=\"to_train_frac\" value=\"0.70\" />
          <input id=\"to_val_frac\" value=\"0.15\" />
          <label>alpha</label>
          <input id=\"to_alpha\" value=\"1.0\" />
        </div>
      </div>
      <button onclick=\"runTrainOffline()\">Run train-offline</button>
    </div>

    <div class=\"card\">
      <h2>Model cards</h2>
      <div class=\"muted\">Load model cards and click to view JSON.</div>
      <button onclick=\"loadModelCards()\">Load model cards</button>
      <div id=\"model_cards\" class=\"filelist\"></div>
    </div>

    <div class=\"card\">
      <h2>paper-trade once</h2>
      <div class=\"muted\">Runs one paper trading step using the last row of the input dataset.</div>
      <div class=\"row\">
        <div>
          <label>inputs</label>
          <textarea id=\"pt_inputs\" rows=\"2\"></textarea>
        </div>
        <div>
          <label>model_id</label>
          <input id=\"pt_model_id\" placeholder=\"m_...\" />
          <label>fee_bps / slippage_bps</label>
          <input id=\"pt_fee\" value=\"1.0\" />
          <input id=\"pt_slip\" value=\"1.0\" />
          <label>lookback (eligible scan)</label>
          <input id=\"pt_lookback\" value=\"200\" />
          <label>require_eligible_row</label>
          <select id=\"pt_require\"><option value=\"true\">true</option><option value=\"false\">false</option></select>
          <label>enforce_trade_validity</label>
          <select id=\"pt_enforce_tv\"><option value=\"true\">true</option><option value=\"false\">false</option></select>
          <label>position_mode</label>
          <select id=\"pt_pos_mode\"><option value=\"risk_scaled\">risk_scaled</option><option value=\"sign\">sign</option></select>
          <label>max_leverage</label>
          <input id=\"pt_max_lev\" value=\"1.0\" />
        </div>
      </div>
      <button onclick=\"runPaperTradeOnce()\">Run paper-trade-once</button>
      <div class=\"muted\">Emergency stop file: <code>ai_data/paper/STOP</code> (create to block trades)</div>
    </div>

    <div class=\"card\">
      <h2>copy-trade once</h2>
      <div class=\"muted\">Runs one copy-trading step from an expert signal JSON under ai_data/.</div>
      <div class=\"row\">
        <div>
          <label>signal_path (within ai_data/)</label>
          <input id=\"ct_signal\" placeholder=\"ai_data/copy/signals/demo.json\" />
        </div>
        <div>
          <label>allocation / max_leverage</label>
          <input id=\"ct_alloc\" value=\"1.0\" />
          <input id=\"ct_max_lev\" value=\"1.0\" />
          <label>fee_bps / slippage_bps</label>
          <input id=\"ct_fee\" value=\"1.0\" />
          <input id=\"ct_slip\" value=\"1.0\" />
        </div>
      </div>
      <button onclick=\"runCopyTradeOnce()\">Run copy-trade-once</button>
      <div class=\"muted\">State: <code>ai_data/copy_paper/state.json</code></div>
    </div>

    <div class=\"card\">
      <h2>validate-data</h2>
      <label>inputs (comma/newline separated)</label>
      <textarea id=\"vd_inputs\" rows=\"2\"></textarea>
      <label>write_registry</label>
      <select id=\"vd_registry\"><option value=\"true\">true</option><option value=\"false\">false</option></select>
      <button onclick=\"runValidate()\">Run validate-data</button>
    </div>

    <div class=\"card\">
      <h2>build-features</h2>
      <div class=\"row\">
        <div>
          <label>inputs</label>
          <textarea id=\"bf_inputs\" rows=\"2\"></textarea>
        </div>
        <div>
          <label>output_path</label>
          <input id=\"bf_output\" placeholder=\"ai_data/my_datasets/features.parquet\" />
        </div>
      </div>
      <button onclick=\"runBuildFeatures()\">Run build-features</button>
    </div>

    <div class=\"card\">
      <h2>build-targets</h2>
      <div class=\"row\">
        <div>
          <label>inputs</label>
          <textarea id=\"bt_inputs\" rows=\"2\"></textarea>
        </div>
        <div>
          <label>output_path</label>
          <input id=\"bt_output\" placeholder=\"ai_data/my_datasets/targets.parquet\" />
        </div>
      </div>
      <div class=\"row\">
        <div>
          <label>horizon</label>
          <input id=\"bt_horizon\" value=\"1\" />
        </div>
        <div>
          <label>lower_q / upper_q</label>
          <input id=\"bt_lower\" value=\"0.33\" />
          <input id=\"bt_upper\" value=\"0.66\" />
        </div>
      </div>
      <button onclick=\"runBuildTargets()\">Run build-targets</button>
    </div>

    <div class=\"card\">
      <h2>detect-regime</h2>
      <div class=\"row\">
        <div>
          <label>inputs</label>
          <textarea id=\"dr_inputs\" rows=\"2\"></textarea>
        </div>
        <div>
          <label>output_path</label>
          <input id=\"dr_output\" placeholder=\"ai_data/my_datasets/regime.parquet\" />
        </div>
      </div>
      <div class=\"row\">
        <div>
          <label>vol_high_q</label>
          <input id=\"dr_vol\" value=\"0.80\" />
        </div>
        <div>
          <label>bb_width_high_q</label>
          <input id=\"dr_bb\" value=\"0.80\" />
        </div>
      </div>
      <div class=\"row\">
        <div>
          <label>liq_low_q</label>
          <input id=\"dr_liq\" value=\"0.10\" />
        </div>
        <div>
          <label>trend_strength_q</label>
          <input id=\"dr_trend\" value=\"0.70\" />
        </div>
      </div>
      <button onclick=\"runDetectRegime()\">Run detect-regime</button>
    </div>

    <div class=\"card\">
      <h2>run-strategy-sim</h2>
      <div class=\"row\">
        <div>
          <label>input_path</label>
          <input id=\"ss_input\" placeholder=\"ai_data/my_datasets/sample_regime.parquet\" />
        </div>
        <div>
          <label>output_path</label>
          <input id=\"ss_output\" placeholder=\"ai_data/my_datasets/strategy_out.parquet\" />
        </div>
      </div>
      <label>report_path</label>
      <input id=\"ss_report\" placeholder=\"ai_data/my_datasets/strategy_report.json\" />
      <button onclick=\"runStrategySim()\">Run run-strategy-sim</button>
    </div>

    <div class=\"card\">
      <h2>Output</h2>
      <div class=\"tabs\" style=\"margin-bottom:10px\">
        <button id=\"tab_json\" class=\"tabbtn active\" onclick=\"showTab('json')\">JSON</button>
        <button id=\"tab_report\" class=\"tabbtn\" onclick=\"showTab('report')\">report.json</button>
        <button id=\"tab_equity\" class=\"tabbtn\" onclick=\"showTab('equity')\">equity chart</button>
      </div>
      <pre id=\"out\">Ready.</pre>
      <pre id=\"report\" style=\"display:none\"></pre>
      <iframe id=\"equity\" style=\"display:none\"></iframe>
    </div>
  </div>

<script>
  let activeInputId = null;
  let lastSim = null;
  let lastTrain = null;
  let selectedModelCard = null;

  function trackFocus(e) {
    const el = e.target;
    if (el && el.id) { activeInputId = el.id; }
  }

  async function loadModelCards() {
    const res = await fetch('/api/model-cards');
    const data = await res.json();
    const box = document.getElementById('model_cards');
    box.innerHTML = '';
    for (const mid of data.model_ids) {
      const div = document.createElement('div');
      div.className = 'fileitem';
      div.textContent = mid;
      div.onclick = async () => {
        selectedModelCard = mid;
        const url = '/api/model-card?model_id=' + encodeURIComponent(mid);
        const r = await fetch(url);
        const txt = await r.text();
        document.getElementById('out').textContent = txt;
        showTab('json');
      };
      box.appendChild(div);
    }
  }
  document.addEventListener('focusin', trackFocus);

  function showTab(which) {
    const out = document.getElementById('out');
    const rep = document.getElementById('report');
    const eq = document.getElementById('equity');
    document.getElementById('tab_json').classList.remove('active');
    document.getElementById('tab_report').classList.remove('active');
    document.getElementById('tab_equity').classList.remove('active');
    if (which === 'json') {
      document.getElementById('tab_json').classList.add('active');
      out.style.display = 'block'; rep.style.display = 'none'; eq.style.display = 'none';
    }
    if (which === 'report') {
      document.getElementById('tab_report').classList.add('active');
      out.style.display = 'none'; rep.style.display = 'block'; eq.style.display = 'none';
      loadReport();
    }
    if (which === 'equity') {
      document.getElementById('tab_equity').classList.add('active');
      out.style.display = 'none'; rep.style.display = 'none'; eq.style.display = 'block';
      loadEquity();
    }
  }

  function cfg() { return document.getElementById('config_path').value; }
  async function post(url, payload) {
    const res = await fetch(url, {method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(payload)});
    const txt = await res.text();
    let data;
    try { data = JSON.parse(txt); } catch { data = {raw: txt}; }
    if (!res.ok) { throw new Error(JSON.stringify(data)); }
    return data;
  }
  function show(x) { document.getElementById('out').textContent = JSON.stringify(x, null, 2); }

  async function loadHealth() {
    const res = await fetch('/api/health');
    show(await res.json());
  }
  async function loadMetrics() {
    const res = await fetch('/api/metrics');
    show(await res.json());
  }
  async function loadAlerts() {
    const res = await fetch('/api/alerts');
    show(await res.json());
  }
  async function loadEvents() {
    const res = await fetch('/api/events');
    show(await res.json());
  }

  async function loadFiles() {
    const res = await fetch('/api/files');
    const data = await res.json();
    const box = document.getElementById('files');
    box.innerHTML = '';
    for (const p of data.files) {
      const div = document.createElement('div');
      div.className = 'fileitem';
      div.textContent = p;
      div.onclick = () => {
        if (!activeInputId) { return; }
        const el = document.getElementById(activeInputId);
        if (!el) { return; }
        el.value = p;
      };
      box.appendChild(div);
    }
  }

  async function loadReport() {
    const rep = document.getElementById('report');
    if (!lastSim || !lastSim.report_path) {
      rep.textContent = 'Run run-strategy-sim first.';
      return;
    }
    const url = '/api/file-text?path=' + encodeURIComponent(lastSim.report_path);
    const res = await fetch(url);
    rep.textContent = await res.text();
  }

  async function loadEquity() {
    const eq = document.getElementById('equity');
    if (!lastSim || !lastSim.output_path) {
      eq.srcdoc = '<div style="font-family:system-ui;padding:12px">Run run-strategy-sim first.</div>';
      return;
    }
    const url = '/api/equity-svg?path=' + encodeURIComponent(lastSim.output_path);
    const res = await fetch(url);
    const svg = await res.text();
    eq.srcdoc = svg;
  }

  async function runValidate() {
    try {
      const data = await post('/api/validate-data', {
        config_path: cfg(),
        inputs: document.getElementById('vd_inputs').value,
        write_registry: document.getElementById('vd_registry').value === 'true'
      });
      show(data);
    } catch (e) { show({error: String(e)}); }
  }
  async function runBuildFeatures() {
    try {
      const data = await post('/api/build-features', {
        config_path: cfg(),
        inputs: document.getElementById('bf_inputs').value,
        output_path: document.getElementById('bf_output').value
      });
      show(data);
    } catch (e) { show({error: String(e)}); }
  }
  async function runBuildTargets() {
    try {
      const data = await post('/api/build-targets', {
        config_path: cfg(),
        inputs: document.getElementById('bt_inputs').value,
        output_path: document.getElementById('bt_output').value,
        horizon: Number(document.getElementById('bt_horizon').value),
        lower_q: Number(document.getElementById('bt_lower').value),
        upper_q: Number(document.getElementById('bt_upper').value)
      });
      show(data);
    } catch (e) { show({error: String(e)}); }
  }
  async function runDetectRegime() {
    try {
      const data = await post('/api/detect-regime', {
        config_path: cfg(),
        inputs: document.getElementById('dr_inputs').value,
        output_path: document.getElementById('dr_output').value,
        vol_high_q: Number(document.getElementById('dr_vol').value),
        bb_width_high_q: Number(document.getElementById('dr_bb').value),
        liq_low_q: Number(document.getElementById('dr_liq').value),
        trend_strength_q: Number(document.getElementById('dr_trend').value)
      });
      show(data);
    } catch (e) { show({error: String(e)}); }
  }
  async function runStrategySim() {
    try {
      const data = await post('/api/run-strategy-sim', {
        config_path: cfg(),
        input_path: document.getElementById('ss_input').value,
        output_path: document.getElementById('ss_output').value,
        report_path: document.getElementById('ss_report').value
      });
      lastSim = data;
      show(data);
    } catch (e) { show({error: String(e)}); }
  }

  async function runTrainOffline() {
    try {
      const data = await post('/api/train-offline', {
        config_path: cfg(),
        inputs: document.getElementById('to_inputs').value,
        target_col: document.getElementById('to_target').value,
        train_frac: Number(document.getElementById('to_train_frac').value),
        val_frac: Number(document.getElementById('to_val_frac').value),
        alpha: Number(document.getElementById('to_alpha').value)
      });
      lastTrain = data;
      show(data);
    } catch (e) { show({error: String(e)}); }
  }

  async function runPaperTradeOnce() {
    try {
      const data = await post('/api/paper-trade-once', {
        config_path: cfg(),
        inputs: document.getElementById('pt_inputs').value,
        model_id: document.getElementById('pt_model_id').value,
        fee_bps: Number(document.getElementById('pt_fee').value),
        slippage_bps: Number(document.getElementById('pt_slip').value),
        lookback: Number(document.getElementById('pt_lookback').value),
        require_eligible_row: document.getElementById('pt_require').value === 'true',
        enforce_trade_validity: document.getElementById('pt_enforce_tv').value === 'true',
        position_mode: document.getElementById('pt_pos_mode').value,
        max_leverage: Number(document.getElementById('pt_max_lev').value)
      });
      show(data);
    } catch (e) { show({error: String(e)}); }
  }

  async function runCopyTradeOnce() {
    try {
      const data = await post('/api/copy-trade-once', {
        config_path: cfg(),
        signal_path: document.getElementById('ct_signal').value,
        allocation: Number(document.getElementById('ct_alloc').value),
        max_leverage: Number(document.getElementById('ct_max_lev').value),
        fee_bps: Number(document.getElementById('ct_fee').value),
        slippage_bps: Number(document.getElementById('ct_slip').value)
      });
      show(data);
    } catch (e) { show({error: String(e)}); }
  }
</script>
</body>
</html>"""


@app.get("/api/files")
def api_files() -> dict:
    root = _ai_data_root()
    if not root.exists():
        return {"files": []}

    allowed = {".parquet", ".json"}
    files: list[str] = []
    for p in root.rglob("*"):
        if p.is_file() and p.suffix.lower() in allowed:
            files.append(str(p.relative_to(Path.cwd())))
        if len(files) >= 300:
            break

    files.sort()
    return {"files": files}


@app.get("/api/health")
def api_health() -> dict:
    return {"ok": True}


@app.get("/api/metrics")
def api_metrics() -> dict:
    m = read_metrics()
    return {"metrics": m}


@app.get("/api/alerts")
def api_alerts() -> dict:
    a = read_last_alert()
    return {"last_alert": a}


@app.get("/api/events")
def api_events() -> dict:
    ev = read_recent_events(limit=200)
    return {"events": ev}


@app.get("/api/model-cards")
def api_model_cards() -> dict:
    root = _model_cards_root()
    if not root.exists():
        return {"model_ids": []}

    ids: list[str] = []
    for p in root.glob("m_*.json"):
        ids.append(p.stem)
        if len(ids) >= 200:
            break
    ids.sort()
    return {"model_ids": ids}


@app.get("/api/model-card", response_class=PlainTextResponse)
def api_model_card(model_id: str) -> str:
    root = _model_cards_root()
    p = (root / f"{model_id}.json").resolve()
    if root not in p.parents and p != root:
        raise HTTPException(status_code=400, detail="Invalid model_id")
    if not p.exists() or not p.is_file():
        raise HTTPException(status_code=404, detail="Model card not found")
    txt = p.read_text(encoding="utf-8")
    if len(txt) > 400_000:
        raise HTTPException(status_code=400, detail="File too large")
    return txt


@app.get("/api/file-text", response_class=PlainTextResponse)
def api_file_text(path: str) -> str:
    p = _safe_ai_data_path(path)
    if not p.exists() or not p.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    if p.suffix.lower() != ".json":
        raise HTTPException(status_code=400, detail="Only .json files are supported")

    txt = p.read_text(encoding="utf-8")
    if len(txt) > 400_000:
        raise HTTPException(status_code=400, detail="File too large")
    return txt


@app.get("/api/equity-svg")
def api_equity_svg(path: str) -> Response:
    p = _safe_ai_data_path(path)
    if not p.exists() or not p.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    if p.suffix.lower() != ".parquet":
        raise HTTPException(status_code=400, detail="Only .parquet files are supported")

    df = pd.read_parquet(p)
    if "equity" not in df.columns:
        raise HTTPException(status_code=400, detail="Missing equity column")

    y = pd.to_numeric(df["equity"], errors="coerce").dropna()
    if y.empty:
        raise HTTPException(status_code=400, detail="No equity data")

    y = y.tail(600).reset_index(drop=True)
    w, h = 900, 240
    pad = 20
    ymin, ymax = float(y.min()), float(y.max())
    if ymax - ymin <= 1e-12:
        ymax = ymin + 1e-12

    def sx(i: int) -> float:
        return pad + (w - 2 * pad) * (i / max(1, len(y) - 1))

    def sy(v: float) -> float:
        return pad + (h - 2 * pad) * (1.0 - (v - ymin) / (ymax - ymin))

    pts = " ".join(f"{sx(i):.2f},{sy(float(v)):.2f}" for i, v in enumerate(y))
    svg = f"""<!doctype html>
<html><head><meta charset='utf-8'/></head>
<body style='margin:0;font-family:system-ui'>
<div style='padding:10px'>
  <div style='font-weight:600'>Equity (last {len(y)} points)</div>
  <div style='color:#6b7280;font-size:12px'>min={ymin:.6f} max={ymax:.6f}</div>
</div>
<svg width='{w}' height='{h}' viewBox='0 0 {w} {h}' style='display:block;margin:0 10px 10px 10px'>
  <rect x='0' y='0' width='{w}' height='{h}' fill='#ffffff' stroke='#e5e7eb'/>
  <polyline fill='none' stroke='#111827' stroke-width='2' points='{pts}' />
</svg>
</body></html>"""
    return Response(content=svg, media_type="text/html")


@app.post("/api/validate-data")
def api_validate_data(payload: dict) -> dict:
    config_path = payload.get("config_path", "config/config.yaml")
    inputs = _parse_paths(str(payload.get("inputs", "")))
    write_registry = bool(payload.get("write_registry", True))

    if not inputs:
        raise HTTPException(status_code=400, detail="inputs is required")

    _, logger = _load_and_setup_logger(config_path)
    res = validate_data(inputs, write_registry=write_registry)

    return {
        "ok": bool(res.report.ok),
        "rows": int(res.report.rows),
        "start_ts": res.report.start_ts,
        "end_ts": res.report.end_ts,
        "missing_cols": list(res.report.missing_cols),
        "duplicates": int(res.report.duplicates),
        "card": None if res.card is None else res.card.__dict__,
    }


@app.post("/api/build-features")
def api_build_features(payload: dict) -> dict:
    config_path = payload.get("config_path", "config/config.yaml")
    inputs = _parse_paths(str(payload.get("inputs", "")))
    output_path = payload.get("output_path")

    if not inputs:
        raise HTTPException(status_code=400, detail="inputs is required")
    if not output_path:
        raise HTTPException(status_code=400, detail="output_path is required")

    _, logger = _load_and_setup_logger(config_path)
    res = build_features(inputs, output_path=output_path)
    if not res.ok:
        logger.error("build-features: FAILED")

    return {
        "ok": bool(res.ok),
        "rows_in": int(res.rows_in),
        "rows_out": int(res.rows_out),
        "features_added": list(res.features_added),
        "output_path": str(res.output_path),
    }


@app.post("/api/build-targets")
def api_build_targets(payload: dict) -> dict:
    config_path = payload.get("config_path", "config/config.yaml")
    inputs = _parse_paths(str(payload.get("inputs", "")))
    output_path = payload.get("output_path")
    horizon = int(payload.get("horizon", 1))
    lower_q = float(payload.get("lower_q", 0.33))
    upper_q = float(payload.get("upper_q", 0.66))

    if not inputs:
        raise HTTPException(status_code=400, detail="inputs is required")
    if not output_path:
        raise HTTPException(status_code=400, detail="output_path is required")

    _, logger = _load_and_setup_logger(config_path)
    res = build_targets(
        inputs,
        output_path=output_path,
        horizon=horizon,
        lower_q=lower_q,
        upper_q=upper_q,
    )
    if not res.ok:
        logger.error("build-targets: FAILED")

    return {
        "ok": bool(res.ok),
        "rows_in": int(res.rows_in),
        "rows_out": int(res.rows_out),
        "output_path": str(res.output_path),
        "horizon": horizon,
        "lower_q": lower_q,
        "upper_q": upper_q,
    }


@app.post("/api/detect-regime")
def api_detect_regime(payload: dict) -> dict:
    config_path = payload.get("config_path", "config/config.yaml")
    inputs = _parse_paths(str(payload.get("inputs", "")))
    output_path = payload.get("output_path")
    vol_high_q = float(payload.get("vol_high_q", 0.80))
    bb_width_high_q = float(payload.get("bb_width_high_q", 0.80))
    liq_low_q = float(payload.get("liq_low_q", 0.10))
    trend_strength_q = float(payload.get("trend_strength_q", 0.70))

    if not inputs:
        raise HTTPException(status_code=400, detail="inputs is required")
    if not output_path:
        raise HTTPException(status_code=400, detail="output_path is required")

    _, logger = _load_and_setup_logger(config_path)
    res = detect_regime_pipeline(
        inputs,
        output_path=output_path,
        vol_high_q=vol_high_q,
        bb_width_high_q=bb_width_high_q,
        liq_low_q=liq_low_q,
        trend_strength_q=trend_strength_q,
    )
    if not res.ok:
        logger.error("detect-regime: FAILED")

    return {
        "ok": bool(res.ok),
        "rows_in": int(res.rows_in),
        "rows_out": int(res.rows_out),
        "output_path": str(res.output_path),
        "counts": dict(res.counts),
        "vol_high_q": vol_high_q,
        "bb_width_high_q": bb_width_high_q,
        "liq_low_q": liq_low_q,
        "trend_strength_q": trend_strength_q,
    }


@app.post("/api/run-strategy-sim")
def api_run_strategy_sim(payload: dict) -> dict:
    config_path = payload.get("config_path", "config/config.yaml")
    input_path = payload.get("input_path")
    output_path = payload.get("output_path")
    report_path = payload.get("report_path")

    if not input_path:
        raise HTTPException(status_code=400, detail="input_path is required")
    if not output_path:
        raise HTTPException(status_code=400, detail="output_path is required")
    if not report_path:
        raise HTTPException(status_code=400, detail="report_path is required")

    _, logger = _load_and_setup_logger(config_path)

    res_df = validate_data([input_path], write_registry=False)
    df = res_df.merge.df

    sim = run_strategy_sim(df, output_path=output_path, report_path=report_path)
    if not sim.ok:
        logger.error("run-strategy-sim: FAILED")

    return {
        "ok": bool(sim.ok),
        "rows": int(sim.rows),
        "total_return": float(sim.total_return),
        "sharpe": float(sim.sharpe),
        "max_drawdown": float(sim.max_drawdown),
        "trades": int(sim.trades),
        "output_path": str(sim.output_path),
        "report_path": str(sim.report_path),
    }


@app.post("/api/train-offline")
def api_train_offline(payload: dict) -> dict:
    config_path = payload.get("config_path", "config/config.yaml")
    inputs = _parse_paths(str(payload.get("inputs", "")))
    target_col = str(payload.get("target_col", "future_log_return"))
    train_frac = float(payload.get("train_frac", 0.70))
    val_frac = float(payload.get("val_frac", 0.15))
    alpha = float(payload.get("alpha", 1.0))

    if not inputs:
        raise HTTPException(status_code=400, detail="inputs is required")

    _, logger = _load_and_setup_logger(config_path)
    res = train_offline(
        inputs,
        target_col=target_col,
        train_frac=train_frac,
        val_frac=val_frac,
        alpha=alpha,
    )
    if not res.ok:
        logger.error("train-offline: FAILED")

    return {
        "ok": bool(res.ok),
        "rows_in": int(res.rows_in),
        "rows_train": int(res.rows_train),
        "rows_val": int(res.rows_val),
        "rows_test": int(res.rows_test),
        "model_id": res.model_id,
        "artifact_path": res.artifact_path,
        "model_card_path": res.model_card_path,
        "metrics": dict(res.metrics),
    }


@app.post("/api/paper-trade-once")
def api_paper_trade_once(payload: dict) -> dict:
    config_path = payload.get("config_path", "config/config.yaml")
    inputs = _parse_paths(str(payload.get("inputs", "")))
    model_id = str(payload.get("model_id", ""))
    fee_bps = float(payload.get("fee_bps", 1.0))
    slippage_bps = float(payload.get("slippage_bps", 1.0))
    lookback = int(payload.get("lookback", 200))
    require_eligible_row = bool(payload.get("require_eligible_row", True))
    enforce_trade_validity = bool(payload.get("enforce_trade_validity", True))
    position_mode = str(payload.get("position_mode", "risk_scaled"))
    max_leverage = float(payload.get("max_leverage", 1.0))

    if not inputs:
        raise HTTPException(status_code=400, detail="inputs is required")
    if not model_id:
        raise HTTPException(status_code=400, detail="model_id is required")

    _, logger = _load_and_setup_logger(config_path)
    res = paper_trade_once(
        inputs,
        model_id=model_id,
        fee_bps=fee_bps,
        slippage_bps=slippage_bps,
        lookback=lookback,
        require_eligible_row=require_eligible_row,
        enforce_trade_validity=enforce_trade_validity,
        position_mode=position_mode,
        max_leverage=max_leverage,
    )
    if not res.ok:
        logger.error("paper-trade-once: FAILED")

    payload_out = res.__dict__.copy()
    if res.fill is not None:
        payload_out["fill"] = res.fill.__dict__
    return payload_out


@app.post("/api/copy-trade-once")
def api_copy_trade_once(payload: dict) -> dict:
    config_path = payload.get("config_path", "config/config.yaml")
    signal_path_raw = str(payload.get("signal_path", ""))
    allocation = float(payload.get("allocation", 1.0))
    max_leverage = float(payload.get("max_leverage", 1.0))
    fee_bps = float(payload.get("fee_bps", 1.0))
    slippage_bps = float(payload.get("slippage_bps", 1.0))

    if not signal_path_raw:
        raise HTTPException(status_code=400, detail="signal_path is required")
    p = _safe_ai_data_path(signal_path_raw)
    if not p.exists() or not p.is_file() or p.suffix.lower() != ".json":
        raise HTTPException(status_code=400, detail="signal_path must be an existing .json within ai_data/")

    _, logger = _load_and_setup_logger(config_path)
    res = copy_trade_once(
        signal_path=p,
        allocation=allocation,
        max_leverage=max_leverage,
        fee_bps=fee_bps,
        slippage_bps=slippage_bps,
    )
    if not res.ok:
        logger.error("copy-trade-once: FAILED")

    payload_out = res.__dict__.copy()
    if res.fill is not None:
        payload_out["fill"] = res.fill.__dict__
    return payload_out


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="binance_ai_trader_web")
    p.add_argument(
        "--config",
        default=str(Path("config") / "config.yaml"),
        help="Path to config.yaml",
    )
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8000)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        _load_and_setup_logger(args.config)

        try:
            import uvicorn  # type: ignore
        except ModuleNotFoundError as e:
            raise BinanceAITraderError(
                "uvicorn is not installed. Install it (e.g. `pip install uvicorn`) to run web server."
            ) from e

        uvicorn.run("interfaces.web.main:app", host=args.host, port=args.port, reload=False)
        return 0
    except BinanceAITraderError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
