from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models.reservation import Reservation, AuditLog
from app.models.table import Table
from app.models.user import User
from app.schemas.reservation import ReservationCreate, ReservationOut, ReservationUpdate
from app.auth import get_current_user

router = APIRouter(prefix="/reservations", tags=["Reservas"])

@router.post("/", response_model=ReservationOut)
def create_reservation(res_data: ReservationCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # 1. Validar mesa
    table = db.query(Table).filter(Table.id == res_data.table_id).first()
    if not table or table.status == "ocupada":
        raise HTTPException(status_code=400, detail="Mesa no disponible")

    # 2. Crear reserva (asignando automáticamente el ID del usuario logueado)
    new_res = Reservation(**res_data.model_dump(), created_by_user_id=current_user.id)
    db.add(new_res)
    db.commit()
    db.refresh(new_res)

    # 3. Log de Auditoría
    log = AuditLog(
        reservation_id=new_res.id,
        user_id=current_user.id,
        action="CREATE",
        details=f"Reserva creada por {current_user.role}: {current_user.username}"
    )
    db.add(log)
    
    # 4. Actualizar estado de mesa
    table.status = "reservada"
    db.commit()
    return new_res

@router.get("/", response_model=List[ReservationOut])
def get_reservations(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # El Admin y Mesero ven todo. El Cliente solo ve las suyas.
    if current_user.role in ["admin", "mesero"]:
        return db.query(Reservation).all()
    return db.query(Reservation).filter(Reservation.created_by_user_id == current_user.id).all()

@router.put("/{res_id}", response_model=ReservationOut)
def update_reservation(res_id: int, updated_data: ReservationUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    res_query = db.query(Reservation).filter(Reservation.id == res_id)
    res = res_query.first()
    
    if not res:
        raise HTTPException(status_code=404, detail="Reserva no encontrada")
    
    # Un cliente solo puede editar sus propias reservas
    if current_user.role == "cliente" and res.created_by_user_id != current_user.id:
        raise HTTPException(status_code=403, detail="No puedes editar reservas ajenas")

    res_query.update(updated_data.model_dump(exclude_unset=True), synchronize_session=False)
    
    # Audit log del cambio
    log = AuditLog(reservation_id=res.id, user_id=current_user.id, action="UPDATE", details="Datos de reserva actualizados")
    db.add(log)
    
    db.commit()
    return res_query.first()

@router.delete("/{res_id}", status_code=204)
def cancel_reservation(res_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # Solo Admin puede borrar físicamente. Los demás deberían solo cambiar el status a "cancelada" (Update).
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Solo el administrador puede eliminar registros de reservas")
    
    db.query(Reservation).filter(Reservation.id == res_id).delete()
    db.commit()
    return None