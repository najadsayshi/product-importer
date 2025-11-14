from sqlalchemy.orm import Session
from . import models
from sqlalchemy import func, text

def get_products(db: Session, skip: int = 0, limit: int = 50, sku: str=None, name: str=None, active: bool=None):
    q = db.query(models.Product)
    if sku:
        q = q.filter(func.lower(models.Product.sku) == sku.lower())
    if name:
        q = q.filter(models.Product.name.ilike(f"%{name}%"))
    if active is not None:
        q = q.filter(models.Product.active==active)
    return q.offset(skip).limit(limit).all()

def create_or_update_product(db: Session, sku: str, **data):
    stmt = text("""
    INSERT INTO products (sku, name, description, price, active, created_at, updated_at)
    VALUES (:sku, :name, :description, :price, :active, now(), now())
    ON CONFLICT ON CONSTRAINT products_sku_lower_idx
    DO UPDATE SET name = EXCLUDED.name, description = EXCLUDED.description, price = EXCLUDED.price, active = EXCLUDED.active, updated_at = now()
    RETURNING *;
    """)
    res = db.execute(stmt, {"sku": sku, **data})
    db.commit()
    return res.fetchone()

def delete_all_products(db: Session):
    db.execute(text("TRUNCATE products CASCADE;"))
    db.commit()
