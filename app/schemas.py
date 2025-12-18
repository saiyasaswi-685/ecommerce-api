from pydantic import BaseModel

class LoginRequest(BaseModel):
    email: str
    role: str

class ProductCreate(BaseModel):
    name: str
    price: float
    stock_quantity: int
    category: str

class ProductResponse(ProductCreate):
    id: int
    version: int

    class Config:
        from_attributes = True

class CartItemCreate(BaseModel):
    product_id: int
    quantity: int
