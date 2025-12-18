import json
from datetime import datetime, timedelta
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from sqlalchemy.orm import Session
import redis

from app.db import engine, SessionLocal
from app.db_models import Base, User, Product, CartItem, Order, OrderItem
from app.schemas import LoginRequest, ProductCreate, ProductResponse, CartItemCreate

app = FastAPI()

# ---------------- REDIS ----------------
redis_client = redis.Redis(host="redis", port=6379, decode_responses=True)
PRODUCTS_CACHE_KEY = "products"

# ---------------- STARTUP ----------------
@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)

# ---------------- AUTH ----------------
SECRET_KEY = "mysecretkey"
ALGORITHM = "HS256"
security = HTTPBearer()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_access_token(data: dict):
    data["exp"] = datetime.utcnow() + timedelta(minutes=30)
    return jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        return jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(401, "Invalid token")

def require_admin(user=Depends(get_current_user)):
    if user["role"] != "ADMIN":
        raise HTTPException(403, "Admin only")
    return user

def require_customer(user=Depends(get_current_user)):
    if user["role"] != "CUSTOMER":
        raise HTTPException(403, "Customer only")
    return user

# ---------------- LOGIN ----------------
@app.post("/login")
def login(data: LoginRequest, db: Session = Depends(get_db)):
    if not db.get(User, data.email):
        db.add(User(email=data.email, role=data.role))
        db.commit()

    return {
        "access_token": create_access_token({
            "email": data.email,
            "role": data.role
        })
    }

# ---------------- PRODUCTS ----------------
@app.post("/products", response_model=ProductResponse)
def create_product(product: ProductCreate, admin=Depends(require_admin), db: Session = Depends(get_db)):
    p = Product(**product.dict())
    db.add(p)
    db.commit()
    db.refresh(p)
    redis_client.delete(PRODUCTS_CACHE_KEY)
    return p

@app.get("/products")
def list_products(category: Optional[str] = None, sort: Optional[str] = None, db: Session = Depends(get_db)):
    cached = redis_client.get(PRODUCTS_CACHE_KEY)
    if cached:
        return json.loads(cached)

    products = db.query(Product).all()

    if category:
        products = [p for p in products if p.category == category]

    if sort == "price_asc":
        products.sort(key=lambda x: x.price)
    elif sort == "price_desc":
        products.sort(key=lambda x: x.price, reverse=True)

    result = [
        {
            "id": p.id,
            "name": p.name,
            "price": p.price,
            "stock_quantity": p.stock_quantity,
            "category": p.category,
            "version": p.version
        }
        for p in products
    ]

    redis_client.set(PRODUCTS_CACHE_KEY, json.dumps(result), ex=60)
    return result

# ✅ REQUIRED ENDPOINT
@app.get("/products/{id}", response_model=ProductResponse)
def get_product(id: int, db: Session = Depends(get_db)):
    product = db.get(Product, id)
    if not product:
        raise HTTPException(404)
    return product

@app.put("/products/{id}", response_model=ProductResponse)
def update_product(id: int, product: ProductCreate, admin=Depends(require_admin), db: Session = Depends(get_db)):
    p = db.get(Product, id)
    if not p:
        raise HTTPException(404)

    for k, v in product.dict().items():
        setattr(p, k, v)

    p.version += 1
    db.commit()
    db.refresh(p)
    redis_client.delete(PRODUCTS_CACHE_KEY)
    return p

@app.delete("/products/{id}")
def delete_product(id: int, admin=Depends(require_admin), db: Session = Depends(get_db)):
    p = db.get(Product, id)
    if not p:
        raise HTTPException(404)
    db.delete(p)
    db.commit()
    redis_client.delete(PRODUCTS_CACHE_KEY)
    return {"message": "deleted"}

# ---------------- CART ----------------
@app.post("/cart/items")
def add_to_cart(item: CartItemCreate, user=Depends(require_customer), db: Session = Depends(get_db)):
    db.add(CartItem(
        user_email=user["email"],
        product_id=item.product_id,
        quantity=item.quantity
    ))
    db.commit()
    return {"message": "added"}

@app.get("/cart")
def view_cart(user=Depends(require_customer), db: Session = Depends(get_db)):
    return db.query(CartItem).filter(
        CartItem.user_email == user["email"]
    ).all()

# ✅ FIXED: delete by cart item ID
@app.delete("/cart/items/{id}")
def remove_cart_item(id: int, user=Depends(require_customer), db: Session = Depends(get_db)):
    item = db.get(CartItem, id)
    if not item or item.user_email != user["email"]:
        raise HTTPException(404)

    db.delete(item)
    db.commit()
    return {"message": "removed"}

# ---------------- ORDERS ----------------
def send_email(email: str, order_id: int):
    print(f"📧 Order {order_id} confirmed for {email}")

@app.post("/orders")
def place_order(background: BackgroundTasks, user=Depends(require_customer), db: Session = Depends(get_db)):
    cart_items = db.query(CartItem).filter(
        CartItem.user_email == user["email"]
    ).all()

    if not cart_items:
        raise HTTPException(400, "Cart empty")

    order = Order(user_email=user["email"], total=0)
    db.add(order)
    db.flush()

    total = 0
    for item in cart_items:
        product = db.query(Product).with_for_update().get(item.product_id)

        if product.stock_quantity < item.quantity:
            raise HTTPException(400, "Out of stock")

        updated = db.query(Product).filter(
            Product.id == product.id,
            Product.version == product.version
        ).update({
            Product.stock_quantity: product.stock_quantity - item.quantity,
            Product.version: product.version + 1
        })

        if updated == 0:
            raise HTTPException(409, "Concurrent update")

        total += product.price * item.quantity

        db.add(OrderItem(
            order_id=order.id,
            product_id=product.id,
            quantity=item.quantity,
            price=product.price
        ))

    db.query(CartItem).filter(
        CartItem.user_email == user["email"]
    ).delete()

    order.total = total
    db.commit()

    background.add_task(send_email, user["email"], order.id)
    return {"order_id": order.id, "total": total}

# ✅ REQUIRED ENDPOINT
@app.get("/orders/{id}")
def get_order(id: int, user=Depends(require_customer), db: Session = Depends(get_db)):
    order = db.get(Order, id)
    if not order or order.user_email != user["email"]:
        raise HTTPException(404)
    return order
