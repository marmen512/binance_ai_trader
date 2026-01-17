# binance_ai_trader

Phase-based system skeleton.

## Phase 0 commands

- `python -m interfaces.cli.main doctor`

## Web UI

- Install deps (once): `pip install -e .`
- Run web server:
  - `./run.sh web --config config/config.yaml --host 127.0.0.1 --port 8000`
  - or `python -m interfaces.web.main --config config/config.yaml --host 127.0.0.1 --port 8000`
- Open: `http://127.0.0.1:8000/`

