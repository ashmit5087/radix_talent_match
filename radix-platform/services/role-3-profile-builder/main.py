import logging
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.config import settings
from app.routers.profiles import router as profiles_router

logging.basicConfig(
    level=settings.LOG_LEVEL,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("profile_builder")

app = FastAPI(
    title="RADIX Talent Match — Role 3: Profile Builder API",
    description=(
        "Backend service for candidate profile creation, prefilling from parsed resumes, "
        "skills management, and profile completeness analytics. "
        "Consistently serves skills to Role 4 (Talent Check) and Role 5 (Skill Matching)."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS
origins = settings.CORS_ORIGINS
if isinstance(origins, str):
    origins = [o.strip() for o in origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if origins else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API v1 routes
app.include_router(profiles_router, prefix="/api/v1")


@app.get("/", tags=["System"])
async def root():
    return {
        "service": "RADIX Talent Match — Role 3: Profile Builder",
        "status": "online",
        "version": "1.0.0",
        "docs": "/docs",
        "api_v1": "/api/v1/profiles",
    }


@app.get("/health", tags=["System"])
async def health_check():
    from app.database import get_supabase_client

    client = get_supabase_client()
    db_mode = "supabase" if client is not None else "in_memory_fallback"

    return {
        "status": "healthy",
        "environment": settings.ENVIRONMENT,
        "persistence_mode": db_mode,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=(settings.ENVIRONMENT == "development"),
    )
