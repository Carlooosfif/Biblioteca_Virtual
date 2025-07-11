# app/routers/auth.py
from fastapi import APIRouter, Depends, HTTPException, status, Form
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from app.database import get_database
from app.models.models import User, UserCreate, UserResponse, Token
import requests
from typing import Optional
import os

router = APIRouter()

# Configuración de seguridad
SECRET_KEY = "tu-clave-secreta-super-segura-aqui"  # En producción usar variable de entorno
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Configuración Keycloak
KEYCLOAK_URL = "http://localhost:8080"  # Cambiar por tu instancia
KEYCLOAK_REALM = "biblioteca"
KEYCLOAK_CLIENT_ID = "biblioteca-app"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

# Funciones de utilidad
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()

def get_user_by_username(db: Session, username: str):
    return db.query(User).filter(User.username == username).first()

def authenticate_user(db: Session, username: str, password: str):
    user = get_user_by_username(db, username)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_database)
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudieron validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = get_user_by_username(db, username=username)
    if user is None:
        raise credentials_exception
    return user

def require_role(required_role: str):
    def role_checker(current_user: User = Depends(get_current_user)):
        if current_user.role != required_role and current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Se requiere rol {required_role} o admin"
            )
        return current_user
    return role_checker

# Endpoints
@router.post("/register", response_model=UserResponse)
def register_user(user: UserCreate, db: Session = Depends(get_database)):
    # Verificar si el usuario ya existe
    db_user = get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(
            status_code=400,
            detail="El email ya está registrado"
        )
    
    db_user = get_user_by_username(db, username=user.username)
    if db_user:
        raise HTTPException(
            status_code=400,
            detail="El username ya está en uso"
        )
    
    # Crear usuario
    hashed_password = get_password_hash(user.password)
    db_user = User(
        email=user.email,
        username=user.username,
        full_name=user.full_name,
        hashed_password=hashed_password,
        role=user.role
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@router.post("/login", response_model=Token)
def login_user(
    username: str = Form(...), 
    password: str = Form(...), 
    db: Session = Depends(get_database)
):
    user = authenticate_user(db, username, password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Username o password incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "role": user.role}, 
        expires_delta=access_token_expires
    )
    return {
        "access_token": access_token, 
        "token_type": "bearer",
        "role": user.role
    }

@router.get("/me", response_model=UserResponse)
def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user

@router.post("/keycloak/login")
def keycloak_login(
    username: str = Form(...), 
    password: str = Form(...), 
    db: Session = Depends(get_database)
):
    """
    Login usando Keycloak SSO
    En un entorno real, esto sería un redirect a Keycloak
    """
    try:
        # Simulación de login con Keycloak
        # En producción usarías la librería python-keycloak
        keycloak_response = {
            "access_token": "keycloak-token-simulation",
            "username": username,
            "email": f"{username}@biblioteca.com",
            "roles": ["estudiante"]
        }
        
        # Buscar o crear usuario basado en datos de Keycloak
        user = get_user_by_username(db, username)
        if not user:
            # Crear usuario automáticamente desde Keycloak
            hashed_password = get_password_hash("keycloak-managed")
            user = User(
                email=keycloak_response["email"],
                username=username,
                full_name=username.title(),
                hashed_password=hashed_password,
                role="estudiante",
                keycloak_id=keycloak_response["access_token"]
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        
        # Crear nuestro JWT
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.username, "role": user.role}, 
            expires_delta=access_token_expires
        )
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "role": user.role,
            "sso": True,
            "two_factor_enabled": user.two_factor_enabled
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Error en autenticación SSO"
        )

@router.post("/2fa/enable")
def enable_2fa(current_user: User = Depends(get_current_user), db: Session = Depends(get_database)):
    """
    Habilitar 2FA (simulado)
    En producción integrarías con SMS/Email/TOTP
    """
    current_user.two_factor_enabled = True
    db.commit()
    return {"message": "2FA habilitado correctamente", "qr_code": "data:image/png;base64,fake-qr"}

@router.post("/2fa/verify")
def verify_2fa(code: str = Form(...), current_user: User = Depends(get_current_user)):
    """
    Verificar código 2FA (simulado)
    """
    if code == "123456":  # Código dummy para demo
        return {"message": "2FA verificado correctamente"}
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Código 2FA inválido"
        )