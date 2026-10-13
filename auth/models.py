from sqlalchemy import Column, Integer, String, Boolean
from database import Base
from pydantic import BaseModel, EmailStr

# USER TABLE (SQLAlchemy)
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)

# -----------------------------
# PYDANTIC SCHEMAS
# -----------------------------
class UserCreate(BaseModel):
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str
