from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
SQLALCHEMY_DATABASE_URL = "mysql+pymysql://root:123456@localhost:3306/ai_edu?charset=utf8mb4"

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()