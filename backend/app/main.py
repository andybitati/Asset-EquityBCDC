import os
import asyncio
import csv
import io
import logging
from datetime import datetime, timedelta
from math import ceil
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Query, Request, Response, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from .config import load_backend_env
from .logging_config import configure_logging
from .models import (
    AuthRequest,
    AdminUserCreate,
    AdminUserUpdate,
    EquipmentItem,
    EquipmentType,
    ForecastRisk,
    MovementRecord,
    MovementType,
    ForecastResponse,
    StockItem,
    UserProfileUpdate,
)
from .storage import append_movement, load_movements, init_db, engine
from .auth import authenticate_user, get_current_user, get_user_profile, hash_password, revoke_token, security, TOKENS, validate_password_policy, verify_password, password_policy_message
from fastapi import Security
from fastapi.security import HTTPAuthorizationCredentials
from .realtime import manager
from sqlalchemy import text

load_backend_env()
configure_logging()

logger = logging.getLogger("assets_equity.app")
security_logger = logging.getLogger("assets_equity.security")

app = FastAPI(title="Assets EquityBCDC Backend")
allow_origins = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
data_dir = os.path.join(os.path.dirname(__file__), "..", "data")
os.makedirs(data_dir, exist_ok=True)
app.mount(
    "/data",
    StaticFiles(directory=data_dir),
    name="data",
)

init_db()

CREDENTIAL_CHANGE_INTERVAL_DAYS = 90


def require_admin(username: str) -> dict:
    profile = get_user_profile(username)
    if profile.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Accès réservé à l'administrateur.")
    return profile


def require_roles(username: str, roles: set[str]) -> dict:
    profile = get_user_profile(username)
    if profile.get("role") not in roles:
        raise HTTPException(status_code=403, detail="Action non autorisée pour ce rôle.")
    return profile


def audit_log(actor: str, action: str, entity_type: str, entity_id: str | None = None, old_value: str | None = None, new_value: str | None = None, request: Request | None = None) -> None:
    ip_address = request.client.host if request and request.client else None
    user_agent = request.headers.get("user-agent") if request else None
    security_logger.info(
        "actor=%s action=%s entity_type=%s entity_id=%s ip=%s",
        actor,
        action,
        entity_type,
        entity_id,
        ip_address,
    )
    with engine.begin() as conn:
        conn.execute(text(
            "INSERT INTO audit_logs (actor_username, action, entity_type, entity_id, old_value, new_value, ip_address, user_agent, created_at) "
            "VALUES (:actor_username, :action, :entity_type, :entity_id, :old_value, :new_value, :ip_address, :user_agent, :created_at)"
        ), {
            "actor_username": actor,
            "action": action,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "old_value": old_value,
            "new_value": new_value,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "created_at": datetime.utcnow(),
        })


def can_change_credentials(profile: dict) -> bool:
    if profile.get("role") == "admin":
        return True
    last_change = profile.get("last_credentials_changed_at")
    if not last_change:
        return True
    if isinstance(last_change, str):
        last_change = datetime.fromisoformat(last_change)
    return datetime.utcnow() - last_change >= timedelta(days=CREDENTIAL_CHANGE_INTERVAL_DAYS)


def update_token_username(old_username: str, new_username: str) -> None:
    for token, session in list(TOKENS.items()):
        if session["username"] == old_username:
            TOKENS[token]["username"] = new_username


def serialize_user(row) -> dict:
    return {
        "username": row["username"],
        "display_name": row["display_name"],
        "role": row["role"],
        "photo_url": row["photo_url"],
        "is_active": bool(row["is_active"]),
        "last_credentials_changed_at": row["last_credentials_changed_at"],
    }


def compute_inventory(movements_list):
    inventory = {equipment_type: 0 for equipment_type in EquipmentType}
    for record in movements_list:
        if record.movement_type == MovementType.entry:
            inventory[record.equipment_type] += record.quantity
        else:
            inventory[record.equipment_type] -= record.quantity
    return inventory


def get_inventory_data():
    movements_list = load_movements()
    return {k.value: v for k, v in compute_inventory(movements_list).items()}


def stock_key(record):
    if getattr(record, "material_id", None):
        return (record.material_id,)
    return (
        record.equipment_type,
        record.serial_number or "",
        record.model or "",
    )


def build_stock_items() -> list[StockItem]:
    stock = {}
    for record in load_movements():
        key = stock_key(record)
        if key not in stock:
            stock[key] = {
                "material_id": record.material_id,
                "equipment_type": record.equipment_type,
                "quantity": 0,
                "serial_number": record.serial_number,
                "model": record.model,
            }
        if record.movement_type == MovementType.entry:
            stock[key]["quantity"] += record.quantity
        else:
            stock[key]["quantity"] -= record.quantity

    return [
        StockItem(**item)
        for item in stock.values()
        if item["quantity"] > 0
    ]


def get_available_quantity(item: EquipmentItem) -> int:
    if item.material_id:
        for stock_item in build_stock_items():
            if stock_item.material_id == item.material_id:
                return stock_item.quantity
        return 0
    key = (
        item.equipment_type,
        item.serial_number or "",
        item.model or "",
    )
    for stock_item in build_stock_items():
        if stock_key(stock_item) == key:
            return stock_item.quantity
    return 0


def compute_stock_policy(current_stock: int, average_daily_exit: float) -> dict:
    reorder_threshold = max(2, ceil(average_daily_exit * 5 + 2))
    emergency_reserve_threshold = max(1, ceil(average_daily_exit * 2 + 1))
    exits_locked = current_stock <= emergency_reserve_threshold
    if exits_locked:
        recommendation = "Réserve d'urgence atteinte - sorties bloquées"
    elif current_stock <= reorder_threshold:
        recommendation = "Risque de pénurie"
    else:
        recommendation = "Stock maîtrisé"
    return {
        "reorder_threshold": reorder_threshold,
        "emergency_reserve_threshold": emergency_reserve_threshold,
        "exits_locked": exits_locked,
        "recommendation": recommendation,
    }


def get_type_stock(equipment_type: EquipmentType) -> int:
    inventory = compute_inventory(load_movements())
    return inventory[equipment_type]


def validate_emergency_reserve(item: EquipmentItem) -> None:
    forecast = build_forecast()
    risk = next(
        risk_item
        for risk_item in forecast.risks
        if risk_item.equipment_type == item.equipment_type
    )
    remaining_stock = risk.current_stock - item.quantity
    if risk.exits_locked:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Sortie bloquée: la réserve d'urgence pour {item.equipment_type.value} "
                f"est atteinte ({risk.current_stock}/{risk.emergency_reserve_threshold})."
            ),
        )
    if remaining_stock < risk.emergency_reserve_threshold:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Sortie bloquée: cette opération ferait passer {item.equipment_type.value} "
                f"sous la réserve d'urgence ({risk.emergency_reserve_threshold})."
            ),
        )


def build_forecast() -> ForecastResponse:
    movements_list = load_movements()
    cutoff = datetime.utcnow() - timedelta(days=30)
    last_30 = [m for m in movements_list if m.movement_type == MovementType.exit and m.timestamp >= cutoff]
    total_exit = sum(m.quantity for m in last_30)
    avg_daily = total_exit / 30 if total_exit else 0.0
    inventory = compute_inventory(movements_list)
    current_stock = sum(inventory.values())
    global_policy = compute_stock_policy(current_stock, avg_daily)
    reorder_threshold = max(10, global_policy["reorder_threshold"])
    estimated_days = current_stock / avg_daily if avg_daily > 0 else None
    recommendation = (
        "Passer commande rapidement" if current_stock <= reorder_threshold else "Stock suffisant pour le moment"
    )
    risks = []
    for equipment_type in EquipmentType:
        type_exit = sum(
            m.quantity
            for m in last_30
            if m.equipment_type == equipment_type
        )
        type_avg_daily = type_exit / 30 if type_exit else 0.0
        type_stock = inventory[equipment_type]
        type_policy = compute_stock_policy(type_stock, type_avg_daily)
        type_days = type_stock / type_avg_daily if type_avg_daily > 0 else None
        risks.append(ForecastRisk(
            equipment_type=equipment_type,
            current_stock=type_stock,
            average_daily_exit=round(type_avg_daily, 2),
            reorder_threshold=type_policy["reorder_threshold"],
            emergency_reserve_threshold=type_policy["emergency_reserve_threshold"],
            estimated_days_to_empty=round(type_days, 1) if type_days else None,
            exits_locked=type_policy["exits_locked"],
            recommendation=type_policy["recommendation"],
        ))
    return ForecastResponse(
        current_stock=current_stock,
        average_daily_exit=round(avg_daily, 2),
        reorder_threshold=reorder_threshold,
        estimated_days_to_empty=round(estimated_days, 1) if estimated_days else None,
        recommendation=recommendation,
        risks=risks,
    )


@app.post("/login")
def login(payload: AuthRequest, request: Request):
    try:
        token = authenticate_user(payload.username, payload.password)
    except HTTPException:
        audit_log(payload.username, "login_failure", "session", request=request)
        raise
    audit_log(payload.username, "login_success", "session", request=request)
    return {"access_token": token, "token_type": "bearer"}


@app.post("/logout")
def logout(credentials: HTTPAuthorizationCredentials = Security(security)):
    token = credentials.credentials
    session = TOKENS.get(token)
    username = session["username"] if session else None
    revoke_token(token)
    if username:
        audit_log(username, "logout", "session")
    return {"status": "ok"}


@app.get("/inventory")
def get_inventory(current_user: str = Depends(get_current_user)):
    require_roles(current_user, {"admin", "user", "manager", "auditor"})
    return {"inventory": get_inventory_data()}


@app.get("/me")
def get_me(current_user: str = Depends(get_current_user)):
    return {"user": get_user_profile(current_user)}


@app.put("/users/me")
def update_me(payload: UserProfileUpdate, request: Request, current_user: str = Depends(get_current_user)):
    profile = get_user_profile(current_user)
    if not can_change_credentials(profile):
        raise HTTPException(
            status_code=400,
            detail="Les identifiants ne peuvent être modifiés qu'une fois tous les 3 mois.",
        )

    updates = {}
    new_username = payload.username.strip() if payload.username else current_user
    if payload.username:
        updates["username"] = new_username
    if payload.display_name:
        updates["display_name"] = payload.display_name.strip()
    if payload.photo_url is not None:
        updates["photo_url"] = payload.photo_url.strip()

    if payload.new_password:
        if not payload.current_password:
            raise HTTPException(status_code=400, detail="Le mot de passe actuel est obligatoire.")
        if not validate_password_policy(payload.new_password):
            raise HTTPException(status_code=400, detail=password_policy_message())
        with engine.connect() as conn:
            stored_hash = conn.execute(
                text("SELECT password_hash FROM users WHERE username = :username"),
                {"username": current_user},
            ).scalar()
        if not verify_password(payload.current_password, stored_hash):
            raise HTTPException(status_code=400, detail="Mot de passe actuel incorrect.")
        updates["password_hash"] = hash_password(payload.new_password)

    if not updates:
        return {"user": profile}

    updates["last_credentials_changed_at"] = datetime.utcnow()
    set_clause = ", ".join(f"{field} = :{field}" for field in updates)
    params = {**updates, "current_username": current_user}
    try:
        with engine.begin() as conn:
            conn.execute(text(f"UPDATE users SET {set_clause} WHERE username = :current_username"), params)
    except Exception:
        raise HTTPException(status_code=400, detail="Impossible de modifier ce profil.")

    if new_username != current_user:
        update_token_username(current_user, new_username)
    audit_log(new_username, "update_own_profile", "user", new_username, request=request)
    return {"user": get_user_profile(new_username)}


@app.get("/users")
def list_users(current_user: str = Depends(get_current_user)):
    require_admin(current_user)
    with engine.connect() as conn:
        rows = conn.execute(text(
            "SELECT username, display_name, role, photo_url, is_active, last_credentials_changed_at "
            "FROM users ORDER BY username"
        )).mappings().all()
    return {"users": [serialize_user(row) for row in rows]}


@app.post("/users")
def admin_create_user(payload: AdminUserCreate, request: Request, current_user: str = Depends(get_current_user)):
    require_admin(current_user)
    if not validate_password_policy(payload.password):
        raise HTTPException(status_code=400, detail=password_policy_message())
    try:
        with engine.begin() as conn:
            conn.execute(text(
                "INSERT INTO users (username, display_name, password_hash, role, photo_url, is_active, last_credentials_changed_at, created_at, updated_at) "
                "VALUES (:username, :display_name, :password_hash, :role, :photo_url, TRUE, :changed_at, :created_at, :updated_at)"
            ), {
                "username": payload.username.strip(),
                "display_name": payload.display_name.strip(),
                "password_hash": hash_password(payload.password),
                "role": payload.role.strip(),
                "photo_url": payload.photo_url,
                "changed_at": datetime.utcnow(),
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            })
    except Exception:
        raise HTTPException(status_code=400, detail="Impossible de créer cet utilisateur.")
    audit_log(current_user, "admin_create_user", "user", payload.username, request=request)
    return {"user": get_user_profile(payload.username)}


@app.put("/users/{username}")
def admin_update_user(username: str, payload: AdminUserUpdate, request: Request, current_user: str = Depends(get_current_user)):
    require_admin(current_user)
    updates = {}
    if payload.username:
        updates["username"] = payload.username.strip()
    if payload.display_name:
        updates["display_name"] = payload.display_name.strip()
    if payload.role:
        updates["role"] = payload.role.strip()
    if payload.photo_url is not None:
        updates["photo_url"] = payload.photo_url.strip()
    if payload.is_active is not None:
        updates["is_active"] = 1 if payload.is_active else 0
    if not updates:
        return {"user": get_user_profile(username)}

    updates["last_credentials_changed_at"] = datetime.utcnow()
    set_clause = ", ".join(f"{field} = :{field}" for field in updates)
    params = {**updates, "target_username": username}
    try:
        with engine.begin() as conn:
            conn.execute(text(f"UPDATE users SET {set_clause} WHERE username = :target_username"), params)
    except Exception:
        raise HTTPException(status_code=400, detail="Impossible de modifier cet utilisateur.")

    if payload.username and payload.username.strip() != username:
        update_token_username(username, payload.username.strip())
        username = payload.username.strip()
    audit_log(current_user, "admin_update_user", "user", username, request=request)
    return {"user": get_user_profile(username)}


@app.delete("/users/{username}")
def admin_delete_user(username: str, request: Request, current_user: str = Depends(get_current_user)):
    require_admin(current_user)
    if username == current_user:
        raise HTTPException(status_code=400, detail="L'administrateur connecté ne peut pas supprimer son propre compte.")
    with engine.begin() as conn:
        result = conn.execute(text("DELETE FROM users WHERE username = :username"), {"username": username})
    for token, session in list(TOKENS.items()):
        if session["username"] == username:
            TOKENS.pop(token, None)
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable.")
    audit_log(current_user, "admin_delete_user", "user", username, request=request)
    return {"status": "deleted"}


@app.get("/movements")
def get_movements(
    q: str | None = Query(default=None),
    limit: int = Query(default=500, ge=1, le=2000),
    offset: int = Query(default=0, ge=0),
    current_user: str = Depends(get_current_user),
):
    require_roles(current_user, {"admin", "user", "manager", "auditor"})
    movements = load_movements()
    if q:
        needle = q.lower()
        movements = [
            movement
            for movement in movements
            if any(
                needle in str(value or "").lower()
                for value in [
                    movement.equipment_type.value,
                    movement.serial_number,
                    movement.model,
                    movement.destination,
                    movement.taken_by,
                    movement.initiated_by,
                    movement.notes,
                ]
            )
        ]
    total = len(movements)
    page = movements[offset:offset + limit]
    return {"movements": [m.dict() for m in page], "total": total, "limit": limit, "offset": offset}


@app.get("/forecast")
def get_forecast(current_user: str = Depends(get_current_user)):
    require_roles(current_user, {"admin", "user", "manager", "auditor"})
    return build_forecast().dict()


@app.get("/stock-items")
def get_stock_items(current_user: str = Depends(get_current_user)):
    require_roles(current_user, {"admin", "user", "manager", "auditor"})
    return {"items": [item.dict() for item in build_stock_items()]}


@app.post("/entries")
def add_entry(item: EquipmentItem, background_tasks: BackgroundTasks, request: Request, current_user: str = Depends(get_current_user)):
    require_roles(current_user, {"admin", "user", "manager"})
    record = MovementRecord(
        id=0,
        timestamp=datetime.utcnow(),
        movement_type=MovementType.entry,
        material_id=item.material_id,
        equipment_type=item.equipment_type,
        quantity=item.quantity,
        serial_number=item.serial_number,
        model=item.model,
        destination=item.destination,
        taken_by=item.taken_by,
        initiated_by=current_user,
        notes=item.notes,
    )
    persisted = append_movement(record)
    asyncio.create_task(manager.broadcast({
        "inventory": get_inventory_data(),
        "forecast": build_forecast().dict(),
        "stock_items": [stock_item.dict() for stock_item in build_stock_items()],
    }))
    audit_log(current_user, "create_entry", "movement", str(persisted.id), new_value=persisted.json(), request=request)
    return {"status": "ok", "movement": persisted.dict()}


@app.post("/exits")
def add_exit(item: EquipmentItem, background_tasks: BackgroundTasks, request: Request, current_user: str = Depends(get_current_user)):
    require_roles(current_user, {"admin", "user", "manager"})
    if not item.destination or not item.destination.strip():
        raise HTTPException(status_code=400, detail="La destination est obligatoire pour une sortie.")
    if not item.taken_by or not item.taken_by.strip():
        raise HTTPException(status_code=400, detail="La personne qui prend le matériel est obligatoire.")
    available_quantity = get_available_quantity(item)
    if available_quantity <= 0:
        raise HTTPException(status_code=400, detail="Ce matériel n'existe pas dans le stock disponible.")
    if available_quantity < item.quantity:
        raise HTTPException(status_code=400, detail="Quantité insuffisante pour ce matériel en stock.")
    validate_emergency_reserve(item)
    record = MovementRecord(
        id=0,
        timestamp=datetime.utcnow(),
        movement_type=MovementType.exit,
        material_id=item.material_id,
        equipment_type=item.equipment_type,
        quantity=item.quantity,
        serial_number=item.serial_number,
        model=item.model,
        destination=item.destination,
        taken_by=item.taken_by,
        initiated_by=current_user,
        notes=item.notes,
    )
    persisted = append_movement(record)
    asyncio.create_task(manager.broadcast({
        "inventory": get_inventory_data(),
        "forecast": build_forecast().dict(),
        "stock_items": [stock_item.dict() for stock_item in build_stock_items()],
    }))
    audit_log(current_user, "create_exit", "movement", str(persisted.id), new_value=persisted.json(), request=request)
    return {"status": "ok", "movement": persisted.dict()}


@app.get("/exports/movements.csv")
def export_movements_csv(request: Request, current_user: str = Depends(get_current_user)):
    require_roles(current_user, {"admin", "manager", "auditor"})
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "id", "material_id", "timestamp", "movement_type", "equipment_type",
        "quantity", "serial_number", "model", "destination", "taken_by",
        "initiated_by", "notes",
    ])
    for movement in load_movements():
        writer.writerow([
            movement.id,
            movement.material_id,
            movement.timestamp.isoformat(),
            movement.movement_type.value,
            movement.equipment_type.value,
            movement.quantity,
            movement.serial_number or "",
            movement.model or "",
            movement.destination or "",
            movement.taken_by or "",
            movement.initiated_by or "",
            movement.notes or "",
        ])
    audit_log(current_user, "export_movements_csv", "export", request=request)
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=movements.csv"},
    )


@app.websocket("/ws/updates")
async def websocket_updates(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@app.post("/notify")
def notify_update(current_user: str = Depends(get_current_user)):
    require_roles(current_user, {"admin", "manager"})
    payload = {
        "inventory": get_inventory_data(),
        "forecast": build_forecast().dict(),
        "stock_items": [stock_item.dict() for stock_item in build_stock_items()],
    }
    asyncio.create_task(manager.broadcast(payload))
    return {"status": "broadcast_sent"}


@app.get("/audit-logs")
def get_audit_logs(current_user: str = Depends(get_current_user)):
    require_roles(current_user, {"admin", "auditor"})
    with engine.connect() as conn:
        rows = conn.execute(text(
            "SELECT actor_username, action, entity_type, entity_id, ip_address, user_agent, created_at "
            "FROM audit_logs ORDER BY id DESC LIMIT 200"
        )).mappings().all()
    return {"audit_logs": [dict(row) for row in rows]}


frontend_dist = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist"))
if os.path.isdir(frontend_dist):
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")
