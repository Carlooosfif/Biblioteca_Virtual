# app/main.py
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBearer
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from app.database import SessionLocal, engine
from app.models import models
from app.routers import auth, books
import uvicorn

# Crear tablas
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Sistema Biblioteca Virtual",
    description="Proyecto Integrador - Autenticación y Autorización",
    version="1.0.0"
)

# CORS para frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency para BD
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Incluir routers
app.include_router(auth.router, prefix="/auth", tags=["Autenticación"])
app.include_router(books.router, prefix="/books", tags=["Libros"])

@app.get("/")
async def root():
    return {
        "message": "Sistema Biblioteca Virtual API",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": {
            "auth": "/auth",
            "books": "/books"
        }
    }

@app.get("/health")
async def health_check():
    return {"status": "OK", "message": "Servidor funcionando correctamente"}

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)