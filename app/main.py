from fastapi import FastAPI
from contextlib import asynccontextmanager

from .db.init_db import init_db
from .api import users, auth


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Vendoor Express API",
    version="0.0.1",
    lifespan=lifespan,
    docs_url="/api/docs",
)

app.include_router(auth.router)
app.include_router(users.router)


@app.get("/")
def read_root():
    return {"Hello": "World"}
