from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import app.models  # noqa: F401 — registers all models with Base.metadata
from app.core.config import settings
from app.core.errors import register_exception_handlers
from app.routers import auth, customers, invoices, orders, products, stock_movements, suppliers, users

app = FastAPI(title="StockFlow CRM", version="0.1.0")

_allowed_origins = settings.cors_origins_list

app.add_middleware(
    CORSMiddleware,
    # allow_credentials solo es válido con una lista concreta de orígenes:
    # el navegador rechaza la combinación "*" + credenciales.
    allow_origins=_allowed_origins,
    allow_credentials="*" not in _allowed_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(products.router)
app.include_router(suppliers.router)
app.include_router(invoices.router)
app.include_router(stock_movements.router)
app.include_router(customers.router)
app.include_router(orders.router)


@app.get("/health")
def health():
    return {"status": "ok"}
