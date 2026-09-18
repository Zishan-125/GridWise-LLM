import logging
from fastapi import FastAPI
from app.api.routes import router
from app.config import settings

logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO),
                    format="%(asctime)s %(levelname)s %(name)s %(message)s")

app=FastAPI(title="GridWise LLM", version="1.0.0", docs_url="/docs", redoc_url="/redoc")
app.include_router(router)
