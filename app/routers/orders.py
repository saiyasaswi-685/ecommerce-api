from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
# --- CRITICAL FIX: Docker package structure kosam 'app.' prefix add chesam ---
from app.database import get_db
from app.models import Product, Order, OrderItem, CartItem
from app.routers.auth import get_current_user

router = APIRouter()

# Asynchronous Task for Email
def send_email(email: str, order_id: int):
    print(f"📧 Confirmation email sent for Order {order_id} to {email}")

@router.post("/")
def place_order(background: BackgroundTasks, user=Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        # 1. Cart retrieval and validation
        cart_items = db.query(CartItem).filter(CartItem.user_email == user["email"]).all()
        if not cart_items: 
            raise HTTPException(status_code=400, detail="Cart is empty")

        # Create the Order object first
        new_order = Order(user_email=user["email"], total=0)
        db.add(new_order)
        db.flush() # Order ID generate avvadaniki

        order_total = 0
        for item in cart_items:
            # 2. Optimistic Locking - Query with version check
            product = db.query(Product).filter(Product.id == item.product_id).first()
            
            if not product or product.stock_quantity < item.quantity:
                raise HTTPException(status_code=400, detail=f"Insufficient stock for {product.name if product else 'Product'}")

            # 3. Versioned Update for Concurrency
            updated_rows = db.query(Product).filter(
                Product.id == product.id, 
                Product.version == product.version
            ).update({
                "stock_quantity": Product.stock_quantity - item.quantity,
                "version": Product.version + 1
            })

            # Check if someone else updated it in the middle
            if updated_rows == 0:
                raise HTTPException(status_code=409, detail="Concurrency conflict: please retry your order")

            # 4. Snapshotted price record
            order_item = OrderItem(
                order_id=new_order.id, 
                product_id=product.id, 
                quantity=item.quantity, 
                price=product.price
            )
            db.add(order_item)
            order_total += (product.price * item.quantity)

        # Update final total and clear cart
        new_order.total = order_total
        db.query(CartItem).filter(CartItem.user_email == user["email"]).delete()
        
        db.commit() # Atomic commit for all changes
        
        # 5. Background Task for Post-order process
        background.add_task(send_email, user["email"], new_order.id)
        
        return {"order_id": new_order.id, "total": order_total, "status": "Success"}

    except Exception as e:
        db.rollback() # ACID property: rollback on any failure
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))