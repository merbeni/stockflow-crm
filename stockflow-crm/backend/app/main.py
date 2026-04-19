from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import app.models  # noqa: F401 — registers all models with Base.metadata
from app.routers import auth, customers, invoices, orders, products, stock_movements, suppliers

app = FastAPI(title="StockFlow CRM", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(products.router)
app.include_router(suppliers.router)
app.include_router(invoices.router)
app.include_router(stock_movements.router)
app.include_router(customers.router)
app.include_router(orders.router)


@app.get("/health")
def health():
    return {"status": "ok"}
