from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models.customer import Customer
from app.models.user import User
from app.schemas.customer import CustomerCreate, CustomerOut, CustomerUpdate
from app.auth import get_current_user

router = APIRouter(prefix="/customers", tags=["Clientes"])

@router.get("/", response_model=List[CustomerOut])
def get_customers(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # if current_user.role not in ["admin", "mesero"]:
    #     raise HTTPException(status_code=403, detail="Acceso denegado")
    
    # Si es cliente, solo le devolvemos su propia ficha por seguridad
    if current_user.role == "cliente":
        return db.query(Customer).filter(Customer.user_id == current_user.id).all()
    
    return db.query(Customer).all()

@router.post("/", response_model=CustomerOut)
def create_customer(customer_data: CustomerCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # Un cliente no puede crear otros perfiles de cliente
    if current_user.role == "cliente":
        raise HTTPException(status_code=403, detail="Operación no permitida")
    
    new_customer = Customer(**customer_data.model_dump())
    db.add(new_customer)
    db.commit()
    db.refresh(new_customer)
    return new_customer

@router.put("/{customer_id}", response_model=CustomerOut)
def update_customer(customer_id: int, updated_data: CustomerUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    customer_query = db.query(Customer).filter(Customer.id == customer_id)
    customer = customer_query.first()
    
    if not customer:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    
    # Solo el admin, el mesero o el propio usuario dueño del perfil pueden editar
    if current_user.role not in ["admin", "mesero"] and current_user.id != customer.user_id:
        raise HTTPException(status_code=403, detail="No tienes permiso para editar este perfil")
    
    customer_query.update(updated_data.model_dump(exclude_unset=True), synchronize_session=False)
    db.commit()
    return customer_query.first()

@router.delete("/{customer_id}", status_code=204)
def delete_customer(customer_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Solo el dueño (admin) puede eliminar perfiles de clientes")
    
    db.query(Customer).filter(Customer.id == customer_id).delete()
    db.commit()
    return None