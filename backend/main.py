"""
DidiGov Backend — FastAPI Application Entry Point
"""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from routers import health, voice, auth, chat, admin

# ── Logging setup ──────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("didi")

# ── FastAPI App ────────────────────────────────────────────────────────────────
app = FastAPI(
    title="DidiGov API",
    description=(
        "Multilingual Voice AI Assistant for Government Schemes. "
        "Helps citizens discover schemes, check eligibility, and apply using voice."
    ),
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS Middleware ────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ────────────────────────────────────────────────────────────────────
app.include_router(health.router, tags=["Health"])
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Auth"])
app.include_router(voice.router, prefix="/api/v1/voice", tags=["Voice"])
app.include_router(chat.router, prefix="/api/v1/chat", tags=["Chat"])
app.include_router(admin.router, prefix="/api/v1/admin", tags=["Admin"])

@app.get("/", include_in_schema=False)
async def root():
    return {
        "message": "DidiGov Backend API is running.",
        "docs": "http://127.0.0.1:8000/docs",
        "frontend": "Open http://localhost:5173 in your browser to view the React App."
    }

# Future routers (added in later phases):
# app.include_router(auth.router,         prefix="/api/v1/auth",         tags=["Auth"])
# app.include_router(session.router,      prefix="/api/v1/session",      tags=["Session"])
# app.include_router(schemes.router,      prefix="/api/v1/schemes",      tags=["Schemes"])
# app.include_router(applications.router, prefix="/api/v1/applications", tags=["Applications"])
# app.include_router(admin.router,        prefix="/api/v1/admin",        tags=["Admin"])

# ── Startup / Shutdown Events ──────────────────────────────────────────────────
@app.on_event("startup")
async def on_startup():
    logger.info("🚀 DidiGov API starting up...")
    logger.info(f"   Region  : {settings.aws_region}")
    logger.info(f"   Model   : {settings.bedrock_model_id}")
    logger.info(f"   KB ID   : {settings.bedrock_knowledge_base_id or 'NOT SET'}")
    logger.info(f"   CORS    : {settings.cors_origins_list}")
    logger.info("✅ DidiGov API ready.")


@app.on_event("shutdown")
async def on_shutdown():
    logger.info("🛑 DidiGov API shutting down.")
