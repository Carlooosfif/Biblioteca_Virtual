# app/models/models.py
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    full_name = Column(String)
    role = Column(String, default="estudiante")  # estudiante, bibliotecario, admin
    is_active = Column(Boolean, default=True)
    keycloak_id = Column(String, nullable=True)  # Para SSO
    two_factor_enabled = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relaciones
    reservations = relationship("Reservation", back_populates="user")

class Book(Base):
    __tablename__ = "books"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    author = Column(String)
    isbn = Column(String, unique=True)
    description = Column(Text)
    available_copies = Column(Integer, default=1)
    total_copies = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relaciones
    reservations = relationship("Reservation", back_populates="book")

class Reservation(Base):
    __tablename__ = "reservations"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    book_id = Column(Integer, ForeignKey("books.id"))
    status = Column(String, default="activa")  # activa, devuelto, vencido
    reservation_date = Column(DateTime, default=datetime.utcnow)
    due_date = Column(DateTime)
    return_date = Column(DateTime, nullable=True)
    
    # Relaciones
    user = relationship("User", back_populates="reservations")
    book = relationship("Book", back_populates="reservations")

# Schemas para Pydantic (validación de datos)
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime

class UserBase(BaseModel):
    email: EmailStr
    username: str
    full_name: str
    role: str = "estudiante"

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: int
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

class BookBase(BaseModel):
    title: str
    author: str
    isbn: str
    description: Optional[str] = None
    total_copies: int = 1

class BookCreate(BookBase):
    pass

class BookResponse(BookBase):
    id: int
    available_copies: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class ReservationResponse(BaseModel):
    id: int
    status: str
    reservation_date: datetime
    due_date: Optional[datetime]
    book: BookResponse
    
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str
    role: str

class TokenData(BaseModel):
    username: Optional[str] = None