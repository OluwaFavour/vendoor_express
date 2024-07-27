from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from .db.init_db import init_db
from .api import users, auth
from .core.config import settings
from .middleware import auto_refresh_token_middleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Vendoor Express API",
    version="0.0.1",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# ADD MIDDLEWARES
app.middleware("http")(auto_refresh_token_middleware)

# ADD CORS MIDDLEWARE
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=settings.allow_credentials,
    allow_methods=settings.allowed_methods,
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)


@app.head("/", include_in_schema=False)
@app.get("/", include_in_schema=False)
def read_root():
    return {"Hello": "World"}
