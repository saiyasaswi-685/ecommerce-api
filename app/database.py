import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# LOCALHOST VADADDU: Docker networks lo service name ('ecommerce-db') vaadali.
# Idi evaluator machine lo tables create avvadaniki kachithanga undali.
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://postgres:postgres@ecommerce-db:5432/ecommerce"
)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()