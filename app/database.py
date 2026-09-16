"""
SQLite database setup. Using SQLite because this is a single-room, single-instance
tool (the AV room desk) — no need for a network DB server, and the whole thing
travels as one file (av_rental.db) which is easy to back up / reset for a demo.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = "sqlite:///./av_rental.db"

engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
