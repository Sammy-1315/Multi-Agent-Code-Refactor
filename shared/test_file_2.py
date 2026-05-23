from fastapi import FastAPI, HTTPException, Depends, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from datetime import datetime
from typing import List, Optional

# --- Database Setup ---
SQLALCHEMY_DATABASE_URL = "sqlite:///./ecommerce.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- Models ---
class DBUser(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String) 

class DBProduct(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(String)
    price = Column(Float)
    stock_count = Column(Integer)

class DBOrder(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    total_price = Column(Float)
    status = Column(String, default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)
    items = relationship("DBOrderItem", back_populates="order")

class DBOrderItem(Base):
    __tablename__ = "order_items"
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    quantity = Column(Integer)
    order = relationship("DBOrder", back_populates="items")

Base.metadata.create_all(bind=engine)

# --- Schemas (Pydantic) ---
class ProductCreate(BaseModel):
    name: str
    description: str
    price: float
    stock_count: int

class ProductResponse(ProductCreate):
    id: int
    class Config:
        from_attributes = True

class OrderItemCreate(BaseModel):
    product_id: int
    quantity: int

class OrderCreate(BaseModel):
    user_id: int
    items: List[OrderItemCreate]

# --- Dependencies ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- App Init ---
app = FastAPI(title="QuickShop API", version="0.1.0")

# --- Routes ---

@app.get("/")
def health_check():
    return {"status": "online", "message": "QuickShop is running"}

# Product Endpoints
@app.get("/products", response_model=List[ProductResponse])
def get_products(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    products = db.query(DBProduct).offset(skip).limit(limit).all()
    return products

@app.post("/products", response_model=ProductResponse)
def create_product(product: ProductCreate, db: Session = Depends(get_db)):
    new_product = DBProduct(**product.dict())
    db.add(new_product)
    db.commit()
    db.refresh(new_product)
    return new_product

@app.post("/orders", status_code=status.HTTP_201_CREATED)
def place_order(order_data: OrderCreate, db: Session = Depends(get_db)):
    """
    Realistic human code: A bit of a 'God Function'. 
    Logic for stock checking, total calculation, and saving are all here.
    """
    user = db.query(DBUser).filter(DBUser.id == order_data.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    total_price = 0
    order_items = []

    # 2. Process items and check stock
    for item in order_data.items:
        product = db.query(DBProduct).filter(DBProduct.id == item.product_id).first()
        
        if not product:
            raise HTTPException(status_code=404, detail=f"Product {item.product_id} not found")
        
        if product.stock_count < item.quantity:
            raise HTTPException(
                status_code=400, 
                detail=f"Not enough stock for {product.name}. Requested: {item.quantity}, Available: {product.stock_count}"
            )

        product.stock_count -= item.quantity
        total_price += product.price * item.quantity
        
        order_items.append(DBOrderItem(product_id=product.id, quantity=item.quantity))

    # 3. Create the Order
    new_order = DBOrder(user_id=order_data.user_id, total_price=total_price, status="completed")
    db.add(new_order)
    db.flush() # Get the order ID

    for oi in order_items:
        oi.order_id = new_order.id
        db.add(oi)

    db.commit()
    db.refresh(new_order)
    
    return {"order_id": new_order.id, "total": total_price, "status": "success"}

@app.get("/orders/{order_id}")
def get_order(order_id: int, db: Session = Depends(get_db)):
    order = db.query(DBOrder).filter(DBOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    items = db.query(DBOrderItem).filter(DBOrderItem.order_id == order_id).all()
    return {
        "id": order.id,
        "total": order.total_price,
        "created_at": order.created_at,
        "items": [{"product_id": i.product_id, "qty": i.quantity} for i in items]
    }

@app.on_event("startup")
def startup_populate():
    db = SessionLocal()
    if db.query(DBUser).count() == 0:
        test_user = DBUser(email="customer@example.com", hashed_password="not_really_hashed")
        db.add(test_user)
        db.commit()
    db.close()