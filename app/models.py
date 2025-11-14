from sqlalchemy import Column, Integer, String, Text, Boolean, Numeric, DateTime, func
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String, nullable=False)
    name = Column(String)
    description = Column(Text)
    price = Column(Numeric(12,2))
    active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class Webhook(Base):
    __tablename__ = "webhooks"
    id = Column(Integer, primary_key=True, index=True)
    url = Column(String, nullable=False)
    event = Column(String, nullable=False)
    enabled = Column(Boolean, default=True, nullable=False)
    secret = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
