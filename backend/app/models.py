from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)

    github_username = Column(String(255), nullable=True)
    github_repo = Column(String(255), nullable=True)
    github_token = Column(String(255), nullable=True)
    openai_token = Column(String(255), nullable=True)

    refresh_token = Column(String(255), nullable=True, unique=True)
    refresh_token_expiry = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
