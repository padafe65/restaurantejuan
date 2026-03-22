from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserOut, UserUpdate, Token
from app.auth import create_access_token, get_current_user
from passlib.context import CryptContext
from app.models.customer import Customer # Asegúrate de importar el modelo Customer

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
router = APIRouter(prefix="/users", tags=["Usuarios"])

# --- LOGIN (Para obtener el Token) ---
@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # Nota: OAuth2PasswordRequestForm usa 'username', nosotros le pasamos el email ahí
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user.is_active: # <--- Bloqueo de seguridad
        raise HTTPException(status_code=400, detail="Usuario desactivado. Contacte al admin.")
    if not user or not pwd_context.verify(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Credenciales incorrectas"
        )
    
    token = create_access_token(data={"sub": user.email})
    return {"access_token": token, "token_type": "bearer", "user_id": user.id, "role": user.role}

# --- CREAR USUARIO CON CLIENTE AUTOMÁTICO ---
@router.post("/", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(user_data: UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="El email ya está registrado")
    
    hashed_password = pwd_context.hash(user_data.password)
    
    # 1. Crear el Usuario
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        password_hash=hashed_password,
        role=user_data.role,
        is_active=True
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # 2. CREAR FICHA DE CLIENTE AUTOMÁTICAMENTE
    # Esto asegura que aparezca en la pestaña "Clientes" y en "Reservas"
    if new_user.role == "cliente":
        new_customer = Customer(
            user_id=new_user.id,
            full_name=new_user.username, # Nombre inicial igual al username
            phone="S/N",
            whatsapp="S/N",
            address="Pendiente"
        )
        db.add(new_customer)
        db.commit()
    
    return new_user

# --- LISTAR TODOS (Solo Admin y Mesero) ---
@router.get("/", response_model=List[UserOut])
def get_users(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role not in ["admin", "mesero"]:
        raise HTTPException(status_code=403, detail="No tienes permiso para ver esta lista")
    return db.query(User).all()

# --- BUSCAR UNO POR ID ---
@router.get("/{user_id}", response_model=UserOut)
def get_user(user_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return user

# --- ACTUALIZAR (Admin o el propio Usuario) ---
@router.put("/{user_id}", response_model=UserOut)
def update_user(
    user_id: int, 
    updated_data: UserUpdate, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    user_query = db.query(User).filter(User.id == user_id)
    user = user_query.first()
    
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    # Seguridad: Solo el Admin o el mismo dueño de la cuenta pueden editar
    if current_user.role != "admin" and current_user.id != user_id:
        raise HTTPException(status_code=403, detail="No tienes permiso para editar este perfil")
    
    # Procesar datos
    data_to_update = updated_data.model_dump(exclude_unset=True)
    
    # Si cambia contraseña, se encripta
    if "password" in data_to_update:
        data_to_update["password_hash"] = pwd_context.hash(data_to_update.pop("password"))
    
    user_query.update(data_to_update, synchronize_session=False)
    db.commit()
    return user_query.first()

# --- ELIMINAR (SOLO ADMIN) ---
@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Solo el admin (dueño) puede eliminar usuarios")
    
    user_query = db.query(User).filter(User.id == user_id)
    if not user_query.first():
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    user_query.delete(synchronize_session=False)
    db.commit()
    return None