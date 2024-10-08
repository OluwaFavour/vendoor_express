from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from fastapi_pagination import add_pagination

from .db.init_db import init_db
from .api import users, auth, shop, admin, products, cart, address, checkout
from .core.config import settings
from .middleware import RemoveSessionCookieMiddleware


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
    debug=settings.debug,
)

# Add pagination
add_pagination(app)

# ADD MIDDLEWARES
## ADD SESSION MIDDLEWARE
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.secret_key,
    same_site=settings.same_site,
    https_only=settings.https_only,
)

## ADD REMOVE SESSION COOKIE MIDDLEWARE
app.add_middleware(RemoveSessionCookieMiddleware)

## ADD CORS MIDDLEWARE
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=settings.allow_credentials,
    allow_methods=settings.allowed_methods,
    allow_headers=["*"],
)


app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(users.router)
app.include_router(shop.router)
app.include_router(products.router)
app.include_router(cart.router)
app.include_router(address.router)
app.include_router(checkout.router)


@app.head("/", include_in_schema=False)
@app.get("/", include_in_schema=False)
def read_root():
    return {"Hello": "World"}
