# app/routers/books.py
from fastapi import APIRouter, Depends, HTTPException, status, Query, Form
from sqlalchemy.orm import Session
from app.database import get_database
from app.models.models import Book, User, Reservation, BookCreate, BookResponse, ReservationResponse
from app.routers.auth import get_current_user, require_role
from typing import List, Optional
from datetime import datetime, timedelta

router = APIRouter()

# Funciones de utilidad
def get_book_by_id(db: Session, book_id: int):
    return db.query(Book).filter(Book.id == book_id).first()

def get_books(db: Session, skip: int = 0, limit: int = 100):
    return db.query(Book).offset(skip).limit(limit).all()

def create_book(db: Session, book: BookCreate):
    db_book = Book(**book.dict(), available_copies=book.total_copies)
    db.add(db_book)
    db.commit()
    db.refresh(db_book)
    return db_book

# Endpoints públicos (solo lectura)
@router.get("/", response_model=List[BookResponse])
def list_books(
    skip: int = 0, 
    limit: int = 100,
    search: Optional[str] = Query(None, description="Buscar por título o autor"),
    db: Session = Depends(get_database)
):
    """
    Listar todos los libros disponibles (público)
    """
    query = db.query(Book)
    
    if search:
        query = query.filter(
            (Book.title.contains(search)) | 
            (Book.author.contains(search))
        )
    
    books = query.offset(skip).limit(limit).all()
    return books

@router.get("/{book_id}", response_model=BookResponse)
def get_book(book_id: int, db: Session = Depends(get_database)):
    """
    Obtener detalles de un libro específico
    """
    book = get_book_by_id(db, book_id)
    if book is None:
        raise HTTPException(status_code=404, detail="Libro no encontrado")
    return book

# Endpoints que requieren autenticación
@router.post("/{book_id}/reserve")
def reserve_book(
    book_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_database)
):
    """
    Reservar un libro (requiere autenticación)
    """
    book = get_book_by_id(db, book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Libro no encontrado")
    
    if book.available_copies <= 0:
        raise HTTPException(status_code=400, detail="No hay copias disponibles")
    
    # Verificar si el usuario ya tiene este libro reservado
    existing_reservation = db.query(Reservation).filter(
        Reservation.user_id == current_user.id,
        Reservation.book_id == book_id,
        Reservation.status == "activa"
    ).first()
    
    if existing_reservation:
        raise HTTPException(status_code=400, detail="Ya tienes este libro reservado")
    
    # Crear reserva
    due_date = datetime.utcnow() + timedelta(days=14)  # 2 semanas
    reservation = Reservation(
        user_id=current_user.id,
        book_id=book_id,
        due_date=due_date
    )
    
    # Reducir copias disponibles
    book.available_copies -= 1
    
    db.add(reservation)
    db.commit()
    db.refresh(reservation)
    
    return {
        "message": "Libro reservado exitosamente",
        "reservation_id": reservation.id,
        "due_date": due_date
    }

@router.get("/my/reservations", response_model=List[ReservationResponse])
def my_reservations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_database)
):
    """
    Ver mis reservas actuales
    """
    reservations = db.query(Reservation).filter(
        Reservation.user_id == current_user.id
    ).all()
    return reservations

@router.put("/{book_id}/return")
def return_book(
    book_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_database)
):
    """
    Devolver un libro reservado
    """
    reservation = db.query(Reservation).filter(
        Reservation.user_id == current_user.id,
        Reservation.book_id == book_id,
        Reservation.status == "activa"
    ).first()
    
    if not reservation:
        raise HTTPException(status_code=404, detail="No tienes este libro reservado")
    
    # Marcar como devuelto
    reservation.status = "devuelto"
    reservation.return_date = datetime.utcnow()
    
    # Aumentar copias disponibles
    book = get_book_by_id(db, book_id)
    book.available_copies += 1
    
    db.commit()
    
    return {"message": "Libro devuelto exitosamente"}

# Endpoints para bibliotecarios
@router.get("/admin/reservations", response_model=List[ReservationResponse])
def list_all_reservations(
    bibliotecario: User = Depends(require_role("bibliotecario")),
    db: Session = Depends(get_database)
):
    """
    Ver todas las reservas (solo bibliotecarios)
    """
    reservations = db.query(Reservation).all()
    return reservations

@router.put("/admin/reservations/{reservation_id}/status")
def update_reservation_status(
    reservation_id: int,
    new_status: str = Form(...),
    bibliotecario: User = Depends(require_role("bibliotecario")),
    db: Session = Depends(get_database)
):
    """
    Actualizar estado de una reserva (solo bibliotecarios)
    """
    valid_statuses = ["activa", "devuelto", "vencido"]
    if new_status not in valid_statuses:
        raise HTTPException(status_code=400, detail="Estado inválido")
    
    reservation = db.query(Reservation).filter(Reservation.id == reservation_id).first()
    if not reservation:
        raise HTTPException(status_code=404, detail="Reserva no encontrada")
    
    old_status = reservation.status
    reservation.status = new_status
    
    # Ajustar copias disponibles si es necesario
    if old_status == "activa" and new_status in ["devuelto", "vencido"]:
        book = get_book_by_id(db, reservation.book_id)
        book.available_copies += 1
    
    db.commit()
    
    return {"message": f"Estado actualizado de {old_status} a {new_status}"}

# Endpoints para administradores
@router.post("/admin/create", response_model=BookResponse)
def create_new_book(
    book: BookCreate,
    admin: User = Depends(require_role("admin")),
    db: Session = Depends(get_database)
):
    """
    Crear un nuevo libro (solo administradores)
    """
    # Verificar ISBN único
    existing_book = db.query(Book).filter(Book.isbn == book.isbn).first()
    if existing_book:
        raise HTTPException(status_code=400, detail="ISBN ya existe")
    
    return create_book(db, book)

@router.put("/admin/{book_id}", response_model=BookResponse)
def update_book(
    book_id: int,
    book_update: BookCreate,
    admin: User = Depends(require_role("admin")),
    db: Session = Depends(get_database)
):
    """
    Actualizar información de un libro (solo administradores)
    """
    book = get_book_by_id(db, book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Libro no encontrado")
    
    for field, value in book_update.dict().items():
        setattr(book, field, value)
    
    # Ajustar copias disponibles si cambió el total
    if book_update.total_copies != book.total_copies:
        difference = book_update.total_copies - book.total_copies
        book.available_copies += difference
        book.total_copies = book_update.total_copies
    
    db.commit()
    db.refresh(book)
    return book

@router.delete("/admin/{book_id}")
def delete_book(
    book_id: int,
    admin: User = Depends(require_role("admin")),
    db: Session = Depends(get_database)
):
    """
    Eliminar un libro (solo administradores)
    """
    book = get_book_by_id(db, book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Libro no encontrado")
    
    # Verificar que no tenga reservas activas
    active_reservations = db.query(Reservation).filter(
        Reservation.book_id == book_id,
        Reservation.status == "activa"
    ).first()
    
    if active_reservations:
        raise HTTPException(
            status_code=400, 
            detail="No se puede eliminar un libro con reservas activas"
        )
    
    db.delete(book)
    db.commit()
    
    return {"message": "Libro eliminado exitosamente"}

# Endpoint especial: comunicación encriptada
@router.post("/secure/data")
def secure_data_exchange(
    data: dict,
    current_user: User = Depends(get_current_user)
):
    """
    Endpoint que simula comunicación encriptada (HTTPS + JWT)
    Demuestra el punto de "Invocar servicio de A hacia B con trama encriptada"
    """
    import json
    import base64
    
    # Simular encriptación (en producción usarías cryptography library)
    data_str = json.dumps(data)
    encoded_data = base64.b64encode(data_str.encode()).decode()
    
    # Simular respuesta encriptada
    response = {
        "message": "Datos procesados de forma segura",
        "user": current_user.username,
        "encrypted_response": encoded_data,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    return response