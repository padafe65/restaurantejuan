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
    # RESTRICCIÓN: El cliente no puede crear reservas por el sistema (según tu requerimiento de que solo consulte)
    # Si quieres que el cliente sí pueda crear, elimina estas dos líneas:
    if current_user.role == "cliente":
        raise HTTPException(status_code=403, detail="Los clientes solo pueden consultar reservas. Contacte al personal.")

    # 1. Validar mesa
    table = db.query(Table).filter(Table.id == res_data.table_id).first()
    if not table or table.status == "ocupada":
        raise HTTPException(status_code=400, detail="Mesa no disponible")

    # 2. Crear reserva
    new_res = Reservation(**res_data.model_dump(), created_by_user_id=current_user.id)
    db.add(new_res)
    db.commit()
    db.refresh(new_res)

    # 3. Log de Auditoría (Registra quién del staff hizo la reserva)
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

# --- ENDPOINT PARA VER LAS RESERVAS ---
@router.get("/", response_model=List[ReservationOut])
def get_reservations(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    query = db.query(Reservation)
    
    # 1. Si es CLIENTE: Solo ve lo que le pertenece (seguridad de datos)
    if current_user.role == "cliente":
        if current_user.profile:
            return query.filter(Reservation.customer_id == current_user.profile.id).all()
        else:
            return []

    # 2. Si es MESERO o ADMIN: Ven todo el listado de XAMPP
    return query.all()

# --- ENDPOINT PARA LA AUDITORÍA (SOLO ADMIN) ---
@router.get("/logs")
def get_audit_logs(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Solo el administrador puede ver la auditoría")
    
    logs = db.query(AuditLog).all()
    return [
        {
            "id": log.id,
            "res_id": log.reservation_id,
            "usuario": log.user_id,
            "accion": log.action,
            "detalle": log.details,
            "fecha": log.change_date.strftime("%Y-%m-%d %H:%M:%S") if log.change_date else "N/A"
        }
        for log in logs
    ]

@router.put("/{res_id}", response_model=ReservationOut)
def update_reservation(res_id: int, updated_data: ReservationUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # RESTRICCIÓN: El cliente NO puede modificar nada
    if current_user.role == "cliente":
        raise HTTPException(status_code=403, detail="No tienes permisos para modificar reservas")

    res_query = db.query(Reservation).filter(Reservation.id == res_id)
    res = res_query.first()
    
    if not res:
        raise HTTPException(status_code=404, detail="Reserva no encontrada")
    
    # Aplicar cambios
    res_query.update(updated_data.model_dump(exclude_unset=True), synchronize_session=False)
    
    # Audit log (Registra qué miembro del staff hizo el cambio)
    log = AuditLog(
        reservation_id=res.id, 
        user_id=current_user.id, 
        action="UPDATE", 
        details=f"Reserva actualizada por {current_user.role}"
    )
    db.add(log)
    
    db.commit()
    return res_query.first()

@router.delete("/{res_id}", status_code=204)
def cancel_reservation(res_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # RESTRICCIÓN MÁXIMA: Solo el administrador puede borrar de la DB
    if current_user.role != "admin":
        raise HTTPException(
            status_code=403, 
            detail="Acceso denegado. Solo el administrador jefe puede eliminar registros físicos."
        )
    
    res_query = db.query(Reservation).filter(Reservation.id == res_id)
    if not res_query.first():
        raise HTTPException(status_code=404, detail="Reserva no encontrada")

    res_query.delete()
    db.commit()
    return None