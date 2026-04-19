from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, computed_field


class ProductCreate(BaseModel):
    sku: str = Field(..., max_length=100)
    name: str = Field(..., max_length=255)
    description: str | None = None
    price: Decimal = Field(..., ge=0, decimal_places=2)
    current_stock: Decimal = Field(default=Decimal("0"), ge=0, decimal_places=3)
    minimum_stock: Decimal = Field(default=Decimal("0"), ge=0, decimal_places=3)


class ProductUpdate(BaseModel):
    sku: str | None = Field(default=None, max_length=100)
    name: str | None = Field(default=None, max_length=255)
    description: str | None = None
    price: Decimal | None = Field(default=None, ge=0, decimal_places=2)
    current_stock: Decimal | None = Field(default=None, ge=0, decimal_places=3)
    minimum_stock: Decimal | None = Field(default=None, ge=0, decimal_places=3)
    is_active: bool | None = None


class ProductResponse(BaseModel):
    id: int
    sku: str
    name: str
    description: str | None
    price: Decimal
    current_stock: Decimal
    minimum_stock: Decimal
    is_active: bool
    created_at: datetime

    @computed_field
    @property
    def low_stock(self) -> bool:
        return self.current_stock < self.minimum_stock

    model_config = {"from_attributes": True}
