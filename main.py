from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi

# ---------------------------------------------------------
# IMPORT MODELS SO SQLALCHEMY CAN CREATE TABLES
# ---------------------------------------------------------
from database import Base, engine

from auth.models import User
from pools.models import (
    Pool,
    PoolMember,
    BuyIn,
    PoolSettings,
    NewsEvent,
    Pick,
    Game,
)
from teams.models import Team

# ---------------------------------------------------------
# ROUTERS
# ---------------------------------------------------------
from auth.router import router as auth_router
from pools.router import router as pools_router

# ⭐ Only pool‑scoped picks router (correct one)
from pools.picks_router import router as pool_picks_router

# ❌ Global picks router removed (you deleted routes/picks.py)
# from routes.picks import router as picks_router

from teams.router import router as fantasy_teams_router

# ---------------------------------------------------------
# FASTAPI APP
# ---------------------------------------------------------
app = FastAPI(
    title="NHL Backend API",
    version="1.0.0",
    description="Fantasy NHL API",
)

# ---------------------------------------------------------
# DATABASE TABLE CREATION
# ---------------------------------------------------------
@app.on_event("startup")
def startup_event():
    Base.metadata.create_all(bind=engine)

# ---------------------------------------------------------
# CORS
# ---------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------
# ROUTERS (ORDER MATTERS!)
# ---------------------------------------------------------

# 1️⃣ Auth first
app.include_router(auth_router)

# 2️⃣ Pools router (must come BEFORE picks)
app.include_router(pools_router)

# 3️⃣ Pool‑scoped picks router (now correct prefix="/pools")
app.include_router(pool_picks_router)

# 4️⃣ Fantasy teams router
app.include_router(fantasy_teams_router)

# ---------------------------------------------------------
# CUSTOM OPENAPI
# ---------------------------------------------------------
def custom_openapi():
    openapi_schema = get_openapi(
        title="NHL Backend API",
        version="1.0.0",
        description="Fantasy NHL API",
        routes=app.routes,
    )

    openapi_schema["components"]["securitySchemes"] = {
        "OAuth2PasswordBearer": {
            "type": "oauth2",
            "flows": {
                "password": {
                    "tokenUrl": "/auth/login",
                    "scopes": {},
                }
            }
        }
    }

    for path, methods in openapi_schema["paths"].items():
        for method_name, method in methods.items():
            if path.startswith("/auth"):
                continue
            method["security"] = [{"OAuth2PasswordBearer": []}]

    return openapi_schema

app.openapi = custom_openapi

# ---------------------------------------------------------
# HEALTH CHECK
# ---------------------------------------------------------
@app.get("/health")
def health_check():
    return {"status": "ok"}

# ---------------------------------------------------------
# DEBUG HEADERS
# ---------------------------------------------------------
@app.post("/debug/headers")
async def debug_headers(request: Request):
    return {"headers": dict(request.headers)}
