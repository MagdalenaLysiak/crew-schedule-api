from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

DB_URL = "mysql+pymysql://root:pass@localhost:3306/crew_db"

engine = create_engine(DB_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()
Base.metadata.create_all(bind=engine)