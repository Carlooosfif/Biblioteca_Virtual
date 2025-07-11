# init_data.py
from sqlalchemy.orm import Session
from app.database import SessionLocal, engine
from app.models.models import User, Book, Reservation, Base
from app.routers.auth import get_password_hash
from datetime import datetime, timedelta

def init_database():
    """
    Inicializar base de datos con datos de ejemplo
    """
    # Crear todas las tablas
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    
    try:
        # Verificar si ya hay datos
        if db.query(User).first():
            print("Base de datos ya inicializada")
            return
        
        print("Inicializando base de datos con datos de ejemplo...")
        
        # Crear usuarios de ejemplo
        users_data = [
            {
                "email": "admin@biblioteca.com",
                "username": "admin",
                "full_name": "Administrador Sistema",
                "password": "admin123",
                "role": "admin"
            },
            {
                "email": "bibliotecario@biblioteca.com", 
                "username": "bibliotecario",
                "full_name": "Juan Pérez",
                "password": "biblio123",
                "role": "bibliotecario"
            },
            {
                "email": "estudiante1@universidad.com",
                "username": "estudiante1", 
                "full_name": "María García",
                "password": "est123",
                "role": "estudiante"
            },
            {
                "email": "estudiante2@universidad.com",
                "username": "estudiante2",
                "full_name": "Carlos López", 
                "password": "est123",
                "role": "estudiante"
            }
        ]
        
        for user_data in users_data:
            hashed_password = get_password_hash(user_data["password"])
            user = User(
                email=user_data["email"],
                username=user_data["username"],
                full_name=user_data["full_name"],
                hashed_password=hashed_password,
                role=user_data["role"]
            )
            db.add(user)
            print(f"Usuario creado: {user_data['username']} ({user_data['role']})")
        
        db.commit()
        
        # Crear libros de ejemplo
        books_data = [
            {
                "title": "Cien años de soledad",
                "author": "Gabriel García Márquez",
                "isbn": "978-0307474728",
                "description": "Una obra maestra del realismo mágico",
                "total_copies": 3
            },
            {
                "title": "1984",
                "author": "George Orwell", 
                "isbn": "978-0451524935",
                "description": "Distopía clásica sobre el totalitarismo",
                "total_copies": 2
            },
            {
                "title": "El Quijote",
                "author": "Miguel de Cervantes",
                "isbn": "978-8424116408", 
                "description": "La primera novela moderna",
                "total_copies": 4
            },
            {
                "title": "Clean Code",
                "author": "Robert C. Martin",
                "isbn": "978-0132350884",
                "description": "Manual de programación profesional",
                "total_copies": 2
            },
            {
                "title": "Design Patterns",
                "author": "Gang of Four",
                "isbn": "978-0201633612",
                "description": "Patrones de diseño en programación",
                "total_copies": 1
            }
        ]
        
        for book_data in books_data:
            book = Book(
                title=book_data["title"],
                author=book_data["author"],
                isbn=book_data["isbn"],
                description=book_data["description"],
                total_copies=book_data["total_copies"],
                available_copies=book_data["total_copies"]
            )
            db.add(book)
            print(f"Libro creado: {book_data['title']}")
        
        db.commit()
        
        # Crear algunas reservas de ejemplo
        estudiante1 = db.query(User).filter(User.username == "estudiante1").first()
        estudiante2 = db.query(User).filter(User.username == "estudiante2").first()
        libro1 = db.query(Book).filter(Book.isbn == "978-0307474728").first()
        libro2 = db.query(Book).filter(Book.isbn == "978-0451524935").first()
        
        if estudiante1 and libro1:
            reservation1 = Reservation(
                user_id=estudiante1.id,
                book_id=libro1.id,
                due_date=datetime.utcnow() + timedelta(days=14)
            )
            libro1.available_copies -= 1
            db.add(reservation1)
            print("Reserva de ejemplo creada: Estudiante1 -> Cien años de soledad")
        
        if estudiante2 and libro2:
            reservation2 = Reservation(
                user_id=estudiante2.id,
                book_id=libro2.id,
                due_date=datetime.utcnow() + timedelta(days=14)
            )
            libro2.available_copies -= 1
            db.add(reservation2)
            print("Reserva de ejemplo creada: Estudiante2 -> 1984")
        
        db.commit()
        
        print("\n✅ Base de datos inicializada correctamente!")
        print("\n👥 Usuarios de prueba creados:")
        print("- admin / admin123 (Administrador)")
        print("- bibliotecario / biblio123 (Bibliotecario)")
        print("- estudiante1 / est123 (Estudiante)")
        print("- estudiante2 / est123 (Estudiante)")
        print("\n📚 Libros de ejemplo agregados")
        print("📋 Reservas de ejemplo creadas")
        
    except Exception as e:
        print(f"Error inicializando base de datos: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    init_database()