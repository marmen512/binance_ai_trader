Local dev quickstart

1. Create venv and install deps:
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt

2. Copy env:
   cp .env.example .env
   # edit .env if needed

3. Start Redis (dev):
   docker run -p 6379:6379 -d redis:6

4. Run API:
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

5. Run worker in separate terminal:
   python -m app.workers.worker

6. Example ingest (curl):
   curl -X POST "http://localhost:8000/api/v1/copytrades/ingest" -H "Content-Type: application/json" -d '{
     "trader_id":"trader_1",
     "source":"copy_service",
     "external_id":"ext-1",
     "timestamp":"2026-01-21T12:00:00Z",
     "symbol":"BTC/USDT",
     "side":"sell",
     "price":50000.0,
     "quantity":0.01,
     "pnl":120.5,
     "orders":[{"type":"market","price":50000.0,"qty":0.01,"side":"sell","fee":0.5,"timestamp":"2026-01-21T12:00:05Z"}],
     "raw":{}
   }'
