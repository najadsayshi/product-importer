import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

raw_url = os.getenv("DATABASE_URL")

if raw_url and raw_url.startswith("postgresql://"):
    raw_url = raw_url.replace("postgresql://", "postgresql+psycopg2://")

DATABASE_URL = raw_url or "postgresql+psycopg2://postgres:example@localhost:5432/app"

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
