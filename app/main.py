from fastapi import FastAPI
from app.core.db import init_db
from app.api.routers.copytrades import router as copytrades_router
from app.api.routers.jobs import router as jobs_router

app = FastAPI(title="Copytrade Analyzer API")

@app.on_event("startup")
def on_startup():
    init_db()

app.include_router(copytrades_router)
app.include_router(jobs_router)
