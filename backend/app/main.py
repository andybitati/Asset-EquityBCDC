import os
import csv
import io
import logging
import base64
import json
import re
import uuid
from datetime import datetime, timedelta
from math import ceil, sqrt
from fastapi import BackgroundTasks, Depends, FastAPI, File, Form, HTTPException, Query, Request, Response, UploadFile, WebSocket, WebSocketDisconnect
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
    PhotoUpload,
    SERIALIZED_EQUIPMENT_TYPES,
    StockItem,
    StockPolicyUpdate,
    UserProfileUpdate,
)
from .storage import append_movement, load_movements, init_db, engine, STORAGE_DIR, classify_entry_serial_numbers, get_available_entry_serial_number_id, list_entry_serial_numbers, load_stock_policies, mark_serial_number_exited, register_entry_serial_numbers, update_stock_policy
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
    for origin in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:48621,http://127.0.0.1:48621,https://localhost:48620,https://127.0.0.1:48620",
    ).split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
data_dir = STORAGE_DIR
os.makedirs(data_dir, exist_ok=True)
app.mount(
    "/data",
    StaticFiles(directory=data_dir),
    name="data",
)

init_db()

CREDENTIAL_CHANGE_INTERVAL_DAYS = 90
UPLOAD_DIR = os.path.join(STORAGE_DIR, "uploads")
ALLOWED_PHOTO_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
ALLOWED_PHOTO_MIME_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
MAX_PHOTO_BYTES = 2 * 1024 * 1024
MAX_SERIAL_IMPORT_BYTES = 2 * 1024 * 1024
DEMAND_WINDOW_DAYS = 90



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


def normalize_business_text(value):
    if value is None:
        return ""
    return str(value).replace("Depot IT", "Dépôt IT")


def parse_serial_numbers(values: list[str] | None) -> list[str]:
    cleaned = []
    seen = set()
    for value in values or []:
        serial = " ".join(str(value or "").strip().split())
        key = serial.casefold()
        if serial and key not in seen:
            cleaned.append(serial)
            seen.add(key)
    return cleaned


def is_serialized_type(equipment_type: EquipmentType) -> bool:
    return equipment_type in SERIALIZED_EQUIPMENT_TYPES


def require_serials_for_entry(item: EquipmentItem, serial_numbers: list[str]) -> None:
    if is_serialized_type(item.equipment_type) and len(serial_numbers) != item.quantity:
        raise HTTPException(
            status_code=400,
            detail=(
                "Ce type de matériel exige un numéro de série par unité. "
                f"Quantité: {item.quantity}, séries fournies: {len(serial_numbers)}."
            ),
        )


def normalize_header(value: str) -> str:
    normalized = str(value or "").strip().lower()
    normalized = normalized.replace("é", "e").replace("è", "e").replace("ê", "e")
    normalized = normalized.replace("°", "").replace("'", " ")
    normalized = re.sub(r"[^a-z0-9]+", "_", normalized).strip("_")
    return normalized


def extract_serials_from_rows(rows: list[list[object]]) -> list[str]:
    rows = [[str(cell or "").strip() for cell in row] for row in rows]
    rows = [row for row in rows if any(row)]
    if not rows:
        return []

    serial_headers = {
        "serial_number",
        "numero_serie",
        "numero_de_serie",
        "n_serie",
        "no_serie",
        "serie",
        "serial",
        "s_n",
        "sn",
    }
    first_row = [normalize_header(cell) for cell in rows[0]]
    serial_index = next((index for index, header in enumerate(first_row) if header in serial_headers), None)
    data_rows = rows[1:] if serial_index is not None else rows
    if serial_index is None:
        serial_index = 0

    serials = []
    for row in data_rows:
        if len(row) <= serial_index:
            continue
        serial = row[serial_index].strip()
        if serial:
            serials.append(serial)
    return parse_serial_numbers(serials)


def decode_text_file(content: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise HTTPException(status_code=400, detail="Le fichier est illisible. Utilisez un CSV encodé en UTF-8 ou ANSI.")


def parse_csv_serials(content: bytes) -> list[str]:
    text_content = decode_text_file(content)
    sample = text_content[:2048]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=";,	,")
    except csv.Error:
        dialect = csv.excel
        dialect.delimiter = ";"
    reader = csv.reader(io.StringIO(text_content), dialect)
    return extract_serials_from_rows(list(reader))


def parse_xls_serials(content: bytes) -> list[str]:
    try:
        import xlrd
    except ImportError:
        try:
            return parse_csv_serials(content)
        except HTTPException:
            raise HTTPException(
                status_code=400,
                detail="L'import XLS nécessite la dépendance xlrd. Installez les dépendances backend ou utilisez un CSV.",
            )

    workbook = xlrd.open_workbook(file_contents=content)
    sheet = workbook.sheet_by_index(0)
    rows = [
        [sheet.cell_value(row_index, column_index) for column_index in range(sheet.ncols)]
        for row_index in range(sheet.nrows)
    ]
    return extract_serials_from_rows(rows)


async def parse_serial_import_file(file: UploadFile) -> list[str]:
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Le fichier importé est vide.")
    if len(content) > MAX_SERIAL_IMPORT_BYTES:
        raise HTTPException(status_code=400, detail="Le fichier ne doit pas dépasser 2 Mo.")

    extension = os.path.splitext(file.filename or "")[1].lower()
    if extension in {".csv", ".txt"}:
        return parse_csv_serials(content)
    if extension == ".xls":
        return parse_xls_serials(content)
    raise HTTPException(status_code=400, detail="Format accepté : CSV ou XLS.")


def save_uploaded_photo(payload: PhotoUpload, username: str) -> str:
    match = re.match(r"^data:(?P<mime>[-\w.]+/[-\w.+]+);base64,(?P<data>.+)$", payload.data_url)
    if not match:
        raise HTTPException(status_code=400, detail="Format de photo invalide.")

    mime_type = match.group("mime").lower()
    if mime_type not in ALLOWED_PHOTO_MIME_TYPES:
        raise HTTPException(status_code=400, detail="Format accepté : JPG, PNG, WEBP ou GIF.")

    extension = os.path.splitext(payload.filename or "")[1].lower()
    if extension not in ALLOWED_PHOTO_EXTENSIONS:
        extension = {
            "image/jpeg": ".jpg",
            "image/png": ".png",
            "image/webp": ".webp",
            "image/gif": ".gif",
        }[mime_type]

    try:
        content = base64.b64decode(match.group("data"), validate=True)
    except Exception:
        raise HTTPException(status_code=400, detail="Photo illisible.")

    if len(content) > MAX_PHOTO_BYTES:
        raise HTTPException(status_code=400, detail="La photo ne doit pas dépasser 2 Mo.")

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    safe_username = re.sub(r"[^a-zA-Z0-9_-]+", "-", username).strip("-") or "user"
    filename = f"{safe_username}-{uuid.uuid4().hex}{extension}"
    path = os.path.join(UPLOAD_DIR, filename)
    with open(path, "wb") as photo_file:
        photo_file.write(content)
    return f"/data/uploads/{filename}"


def compute_inventory(movements_list):
    inventory = {equipment_type: 0 for equipment_type in EquipmentType}
    for record in movements_list:
        if is_serialized_type(record.equipment_type):
            continue
        if record.movement_type == MovementType.entry:
            inventory[record.equipment_type] += record.quantity
        else:
            inventory[record.equipment_type] -= record.quantity
    for serial in list_entry_serial_numbers():
        if serial["status"] == "in_stock":
            inventory[EquipmentType(serial["equipment_type"])] += 1
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
    for serial in list_entry_serial_numbers(status="in_stock"):
        equipment_type = EquipmentType(serial["equipment_type"])
        if not is_serialized_type(equipment_type):
            continue
        stock[("serial", serial["id"])] = {
            "material_id": serial["material_id"] or serial["id"],
            "equipment_type": equipment_type,
            "quantity": 1,
            "serial_number": serial["serial_number"],
            "model": None,
        }

    for record in load_movements():
        if is_serialized_type(record.equipment_type):
            continue
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


def serial_registry_payload(status: str | None = None, q: str | None = None) -> dict:
    items = list_entry_serial_numbers(status=status, q=q)
    counts = {
        "in_stock": sum(1 for item in items if item["status"] == "in_stock"),
        "exited": sum(1 for item in items if item["status"] == "exited"),
        "total": len(items),
    }
    return {"items": items, "counts": counts}


def policy_for_type(equipment_type: EquipmentType | None) -> dict:
    if not equipment_type:
        return {
            "lead_time_days": 14,
            "emergency_days": 5,
            "minimum_stock": 2,
            "target_days": 30,
            "service_factor": 1.28,
        }
    return load_stock_policies()[equipment_type.value]


def daily_exit_series(movements_list: list[MovementRecord], equipment_type: EquipmentType | None, window_days: int) -> list[int]:
    today = datetime.utcnow().date()
    day_totals = {
        today - timedelta(days=offset): 0
        for offset in range(window_days)
    }
    cutoff = datetime.utcnow() - timedelta(days=window_days)
    for movement in movements_list:
        if movement.movement_type != MovementType.exit or movement.timestamp < cutoff:
            continue
        if equipment_type and movement.equipment_type != equipment_type:
            continue
        day = movement.timestamp.date()
        if day in day_totals:
            day_totals[day] += movement.quantity
    return [day_totals[day] for day in sorted(day_totals)]


def demand_stats(movements_list: list[MovementRecord], equipment_type: EquipmentType | None, window_days: int = DEMAND_WINDOW_DAYS) -> dict:
    series = daily_exit_series(movements_list, equipment_type, window_days)
    average = sum(series) / window_days if window_days else 0.0
    variance = sum((value - average) ** 2 for value in series) / window_days if window_days else 0.0
    return {
        "average_daily_exit": average,
        "demand_std_dev": sqrt(variance),
        "window_days": window_days,
    }


def compute_stock_policy(current_stock: int, average_daily_exit: float, demand_std_dev: float, equipment_type: EquipmentType | None = None) -> dict:
    policy = policy_for_type(equipment_type)
    lead_time_days = policy["lead_time_days"]
    emergency_days = policy["emergency_days"]
    minimum_stock = policy["minimum_stock"]
    service_factor = policy["service_factor"]

    lead_time_demand = average_daily_exit * lead_time_days
    emergency_demand = average_daily_exit * emergency_days
    safety_stock = ceil(service_factor * demand_std_dev * sqrt(lead_time_days))
    emergency_safety_stock = ceil(service_factor * demand_std_dev * sqrt(emergency_days))

    reorder_threshold = max(minimum_stock, ceil(lead_time_demand + safety_stock))
    emergency_reserve_threshold = max(minimum_stock, ceil(emergency_demand + emergency_safety_stock))
    target_stock = max(reorder_threshold, ceil(average_daily_exit * policy["target_days"] + safety_stock))
    manager_review_required = current_stock <= emergency_reserve_threshold

    if current_stock <= 0:
        recommendation = "Rupture - réapprovisionnement prioritaire"
    elif manager_review_required:
        recommendation = "Réserve d'urgence atteinte - avis responsable requis"
    elif current_stock <= reorder_threshold:
        recommendation = "Point de commande atteint"
    else:
        recommendation = "Stock maîtrisé"
    return {
        "lead_time_days": lead_time_days,
        "safety_stock": safety_stock,
        "reorder_threshold": reorder_threshold,
        "emergency_reserve_threshold": emergency_reserve_threshold,
        "target_stock": target_stock,
        "exits_locked": False,
        "manager_review_required": manager_review_required,
        "recommendation": recommendation,
    }


def get_type_stock(equipment_type: EquipmentType) -> int:
    inventory = compute_inventory(load_movements())
    return inventory[equipment_type]


def assess_manager_review(item: EquipmentItem) -> dict:
    forecast = build_forecast()
    risk = next(
        risk_item
        for risk_item in forecast.risks
        if risk_item.equipment_type == item.equipment_type
    )
    remaining_stock = risk.current_stock - item.quantity
    review_required = risk.manager_review_required or remaining_stock < risk.emergency_reserve_threshold
    return {
        "manager_review_required": review_required,
        "current_stock": risk.current_stock,
        "remaining_stock": remaining_stock,
        "emergency_reserve_threshold": risk.emergency_reserve_threshold,
        "reorder_threshold": risk.reorder_threshold,
        "recommendation": risk.recommendation,
    }


def build_forecast() -> ForecastResponse:
    movements_list = load_movements()
    global_stats = demand_stats(movements_list, None)
    avg_daily = global_stats["average_daily_exit"]
    inventory = compute_inventory(movements_list)
    current_stock = sum(inventory.values())
    global_policy = compute_stock_policy(current_stock, avg_daily, global_stats["demand_std_dev"], None)
    reorder_threshold = max(10, global_policy["reorder_threshold"])
    estimated_days = current_stock / avg_daily if avg_daily > 0 else None
    recommendation = (
        "Passer commande rapidement" if current_stock <= reorder_threshold else "Stock suffisant pour le moment"
    )
    risks = []
    for equipment_type in EquipmentType:
        type_stats = demand_stats(movements_list, equipment_type)
        type_avg_daily = type_stats["average_daily_exit"]
        type_std_dev = type_stats["demand_std_dev"]
        type_stock = inventory[equipment_type]
        type_policy = compute_stock_policy(type_stock, type_avg_daily, type_std_dev, equipment_type)
        type_days = type_stock / type_avg_daily if type_avg_daily > 0 else None
        risks.append(ForecastRisk(
            equipment_type=equipment_type,
            current_stock=type_stock,
            average_daily_exit=round(type_avg_daily, 2),
            demand_std_dev=round(type_std_dev, 2),
            demand_window_days=type_stats["window_days"],
            lead_time_days=type_policy["lead_time_days"],
            safety_stock=type_policy["safety_stock"],
            reorder_threshold=type_policy["reorder_threshold"],
            emergency_reserve_threshold=type_policy["emergency_reserve_threshold"],
            target_stock=type_policy["target_stock"],
            estimated_days_to_empty=round(type_days, 1) if type_days else None,
            exits_locked=type_policy["exits_locked"],
            manager_review_required=type_policy["manager_review_required"],
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
    if profile.get("role") == "auditor":
        raise HTTPException(status_code=403, detail="Accès en lecture seule pour le rôle auditeur.")
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


@app.post("/users/photo")
def upload_user_photo(payload: PhotoUpload, request: Request, current_user: str = Depends(get_current_user)):
    profile = get_user_profile(current_user)
    if profile.get("role") == "auditor":
        raise HTTPException(status_code=403, detail="Accès en lecture seule pour le rôle auditeur.")
    target_username = (payload.target_username or current_user).strip()
    if target_username != current_user:
        require_admin(current_user)
    photo_url = save_uploaded_photo(payload, target_username)
    if payload.persist:
        try:
            with engine.begin() as conn:
                result = conn.execute(
                    text("UPDATE users SET photo_url = :photo_url, updated_at = :updated_at WHERE username = :username"),
                    {
                        "photo_url": photo_url,
                        "updated_at": datetime.utcnow(),
                        "username": target_username,
                    },
                )
        except Exception:
            raise HTTPException(status_code=400, detail="Impossible d'enregistrer la photo dans le profil.")
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Utilisateur introuvable.")
    audit_log(current_user, "upload_user_photo", "user", target_username, new_value=photo_url, request=request)
    return {"photo_url": photo_url, "user": get_user_profile(target_username) if payload.persist else None}


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


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "frontend_mounted": os.path.isdir(frontend_dist) if "frontend_dist" in globals() else False,
        "storage_dir": STORAGE_DIR,
        "time": datetime.utcnow().isoformat(),
    }


@app.get("/stock-policies")
def get_stock_policies(current_user: str = Depends(get_current_user)):
    require_roles(current_user, {"admin", "user", "manager", "auditor"})
    return {"policies": list(load_stock_policies().values())}


@app.put("/stock-policies")
def put_stock_policy(
    payload: StockPolicyUpdate,
    request: Request,
    equipment_type: EquipmentType = Query(..., alias="type"),
    current_user: str = Depends(get_current_user),
):
    require_roles(current_user, {"admin", "manager"})
    updated = update_stock_policy(equipment_type, payload.dict())
    audit_log(
        current_user,
        "update_stock_policy",
        "stock_policy",
        equipment_type.value,
        new_value=json.dumps(updated, ensure_ascii=False),
        request=request,
    )
    return {"policy": updated, "forecast": build_forecast().dict()}


@app.get("/stock-items")
def get_stock_items(current_user: str = Depends(get_current_user)):
    require_roles(current_user, {"admin", "user", "manager", "auditor"})
    return {"items": [item.dict() for item in build_stock_items()]}


@app.post("/entries")
def add_entry(item: EquipmentItem, background_tasks: BackgroundTasks, request: Request, current_user: str = Depends(get_current_user)):
    require_roles(current_user, {"admin", "user", "manager"})
    serial_numbers = parse_serial_numbers(item.serial_numbers)
    require_serials_for_entry(item, serial_numbers)
    if serial_numbers and not is_serialized_type(item.equipment_type):
        raise HTTPException(
            status_code=400,
            detail="Les numéros de série ne sont acceptés que pour les matériels traçables individuellement.",
        )
    if len(serial_numbers) > item.quantity:
        raise HTTPException(
            status_code=400,
            detail="Le nombre de numéros de série ne peut pas dépasser la quantité entrée.",
        )
    serial_classification = classify_entry_serial_numbers(serial_numbers)
    if serial_numbers and serial_classification["duplicates"]:
        raise HTTPException(
            status_code=400,
            detail=f"Numéro(s) déjà en stock: {', '.join(serial_classification['duplicates'][:5])}",
        )
    if serial_numbers and serial_classification["already_exited"]:
        raise HTTPException(
            status_code=400,
            detail=(
                "Numéro(s) déjà sortis. Une réactivation doit être traitée par contrôle séparé: "
                f"{', '.join(serial_classification['already_exited'][:5])}"
            ),
        )
    record = MovementRecord(
        id=0,
        timestamp=datetime.utcnow(),
        movement_type=MovementType.entry,
        material_id=item.material_id,
        equipment_type=item.equipment_type,
        quantity=item.quantity,
        serial_number=None,
        model=None,
        destination=None,
        taken_by=None,
        initiated_by=current_user,
        notes=item.notes,
    )
    persisted = append_movement(record)
    serial_report = register_entry_serial_numbers(persisted, serial_numbers)
    background_tasks.add_task(manager.broadcast, {
        "inventory": get_inventory_data(),
        "forecast": build_forecast().dict(),
        "stock_items": [stock_item.dict() for stock_item in build_stock_items()],
        "serial_registry": serial_registry_payload(),
        "movements": [movement.dict() for movement in load_movements()],
    })
    audit_log(
        current_user,
        "create_entry",
        "movement",
        str(persisted.id),
        new_value=json.dumps({
            "movement": persisted.dict(),
            "serial_numbers": serial_numbers,
            "serial_report": serial_report,
        }, default=str, ensure_ascii=False),
        request=request,
    )
    return {"status": "ok", "movement": persisted.dict(), "serial_report": serial_report}


@app.post("/entries/serial-import")
async def import_entry_serial_numbers(
    background_tasks: BackgroundTasks,
    request: Request,
    equipment_type: EquipmentType = Form(..., alias="type"),
    notes: str | None = Form(default=None),
    file: UploadFile = File(...),
    current_user: str = Depends(get_current_user),
):
    require_roles(current_user, {"admin", "user", "manager"})
    if not is_serialized_type(equipment_type):
        raise HTTPException(
            status_code=400,
            detail="L'import de numéros de série est réservé aux matériels traçables individuellement.",
        )
    serial_numbers = await parse_serial_import_file(file)
    if not serial_numbers:
        raise HTTPException(status_code=400, detail="Aucun numéro de série valide n'a été trouvé dans le fichier.")
    serial_classification = classify_entry_serial_numbers(serial_numbers)
    new_serial_numbers = serial_classification["new"]
    if not new_serial_numbers:
        raise HTTPException(
            status_code=400,
            detail="Aucune nouvelle série à importer. Le fichier contient uniquement des doublons ou des séries déjà sorties.",
        )

    record = MovementRecord(
        id=0,
        timestamp=datetime.utcnow(),
        movement_type=MovementType.entry,
        material_id=None,
        equipment_type=equipment_type,
        quantity=len(new_serial_numbers),
        serial_number=None,
        model=None,
        destination=None,
        taken_by=None,
        initiated_by=current_user,
        notes=notes or f"Import de {len(new_serial_numbers)} numéro(s) de série depuis {file.filename}",
    )
    persisted = append_movement(record)
    serial_report = register_entry_serial_numbers(persisted, new_serial_numbers)
    serial_report["duplicates"] = serial_classification["duplicates"]
    serial_report["already_exited"] = serial_classification["already_exited"]
    background_tasks.add_task(manager.broadcast, {
        "inventory": get_inventory_data(),
        "forecast": build_forecast().dict(),
        "stock_items": [stock_item.dict() for stock_item in build_stock_items()],
        "serial_registry": serial_registry_payload(),
        "movements": [movement.dict() for movement in load_movements()],
    })
    audit_log(
        current_user,
        "import_entry_serial_numbers",
        "serial_number",
        str(persisted.id),
        new_value=json.dumps({
            "movement": persisted.dict(),
            "filename": file.filename,
            "serial_count": len(new_serial_numbers),
            "serial_numbers": new_serial_numbers,
            "serial_report": serial_report,
        }, default=str, ensure_ascii=False),
        request=request,
    )
    return {
        "status": "ok",
        "movement": persisted.dict(),
        **serial_report,
        "read": len(serial_numbers),
    }


@app.post("/exits")
def add_exit(item: EquipmentItem, background_tasks: BackgroundTasks, request: Request, current_user: str = Depends(get_current_user)):
    require_roles(current_user, {"admin", "user", "manager"})
    if not item.destination or not item.destination.strip():
        raise HTTPException(status_code=400, detail="La destination est obligatoire pour une sortie.")
    if not item.taken_by or not item.taken_by.strip():
        raise HTTPException(status_code=400, detail="La personne qui prend le matériel est obligatoire.")
    serialized_exit = is_serialized_type(item.equipment_type)
    entry_serial_number_id = None
    if serialized_exit:
        if not item.serial_number or not item.serial_number.strip():
            raise HTTPException(status_code=400, detail="Le numéro de série est obligatoire pour une sortie de matériel traçable.")
        if not item.model or not item.model.strip():
            raise HTTPException(status_code=400, detail="Le modèle est obligatoire pour une sortie de matériel traçable.")
        if item.quantity != 1:
            raise HTTPException(status_code=400, detail="Une sortie identifiée par numéro de série doit concerner une seule unité.")
        entry_serial_number_id = get_available_entry_serial_number_id(item.serial_number, item.equipment_type)
        if not entry_serial_number_id:
            audit_log(
                current_user,
                "unknown_serial_exit_attempt",
                "serial_number",
                item.serial_number.strip(),
                new_value=json.dumps({
                    "type": item.equipment_type.value,
                    "serial_number": item.serial_number.strip(),
                    "model": item.model,
                    "destination": item.destination,
                    "taken_by": item.taken_by,
                    "quantity": item.quantity,
                }, ensure_ascii=False),
                request=request,
            )
            raise HTTPException(
                status_code=400,
                detail="Sortie bloquée: ce numéro de série n'a pas été enregistré dans les entrées.",
            )
    available_quantity = 1 if serialized_exit else get_type_stock(item.equipment_type)
    if available_quantity <= 0:
        raise HTTPException(status_code=400, detail="Ce matériel n'existe pas dans le stock disponible.")
    if available_quantity < item.quantity:
        raise HTTPException(status_code=400, detail="Quantité insuffisante pour ce matériel en stock.")
    review = assess_manager_review(item)
    record = MovementRecord(
        id=0,
        entry_serial_number_id=entry_serial_number_id,
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
    if serialized_exit:
        mark_serial_number_exited(item.serial_number, persisted.id)
    if review["manager_review_required"]:
        audit_log(
            current_user,
            "manager_review_required_exit",
            "movement",
            str(persisted.id),
            new_value=json.dumps({
                "movement": persisted.dict(),
                "review": review,
            }, default=str, ensure_ascii=False),
            request=request,
        )
    background_tasks.add_task(manager.broadcast, {
        "inventory": get_inventory_data(),
        "forecast": build_forecast().dict(),
        "stock_items": [stock_item.dict() for stock_item in build_stock_items()],
        "serial_registry": serial_registry_payload(),
        "movements": [movement.dict() for movement in load_movements()],
    })
    audit_log(current_user, "create_exit", "movement", str(persisted.id), new_value=persisted.json(), request=request)
    return {"status": "ok", "movement": persisted.dict(), "manager_review": review}


@app.get("/serial-registry")
def get_serial_registry(
    status: str | None = Query(default=None, pattern="^(in_stock|exited)$"),
    q: str | None = Query(default=None),
    current_user: str = Depends(get_current_user),
):
    require_roles(current_user, {"admin", "user", "manager", "auditor"})
    return serial_registry_payload(status=status, q=q)


@app.get("/exports/movements.csv")
def export_movements_csv(request: Request, current_user: str = Depends(get_current_user)):
    require_roles(current_user, {"admin", "manager"})
    output = io.StringIO()
    output.write("\ufeff")
    writer = csv.writer(output, delimiter=";")
    writer.writerow([
        "id", "material_id", "entry_serial_number_id", "timestamp", "movement_type", "equipment_type",
        "quantity", "serial_number", "model", "destination", "taken_by",
        "initiated_by", "notes",
    ])
    for movement in load_movements():
        writer.writerow([
            movement.id,
            movement.material_id,
            movement.entry_serial_number_id,
            movement.timestamp.isoformat(),
            movement.movement_type.value,
            movement.equipment_type.value,
            movement.quantity,
            normalize_business_text(movement.serial_number),
            normalize_business_text(movement.model),
            normalize_business_text(movement.destination),
            normalize_business_text(movement.taken_by),
            normalize_business_text(movement.initiated_by),
            normalize_business_text(movement.notes),
        ])
    audit_log(current_user, "export_movements_csv", "export", request=request)
    return Response(
        content=output.getvalue(),
        media_type="text/csv; charset=utf-8",
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
def notify_update(background_tasks: BackgroundTasks, current_user: str = Depends(get_current_user)):
    require_roles(current_user, {"admin", "manager"})
    payload = {
        "inventory": get_inventory_data(),
        "forecast": build_forecast().dict(),
        "stock_items": [stock_item.dict() for stock_item in build_stock_items()],
        "serial_registry": serial_registry_payload(),
    }
    background_tasks.add_task(manager.broadcast, payload)
    return {"status": "broadcast_sent"}


@app.get("/audit-logs")
def get_audit_logs(current_user: str = Depends(get_current_user)):
    require_roles(current_user, {"admin", "auditor"})
    with engine.connect() as conn:
        rows = conn.execute(text(
            "SELECT actor_username, action, entity_type, entity_id, new_value, ip_address, user_agent, created_at "
            "FROM audit_logs ORDER BY id DESC LIMIT 200"
        )).mappings().all()
    return {"audit_logs": [dict(row) for row in rows]}


frontend_dist = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist"))
if os.path.isdir(frontend_dist):
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")
