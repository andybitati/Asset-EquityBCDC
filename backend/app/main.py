import os
import asyncio
from datetime import datetime, timedelta
from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from .models import (
    AuthRequest,
    EquipmentItem,
    EquipmentType,
    MovementRecord,
    MovementType,
    ForecastResponse,
)
from .storage import append_movement, load_movements, init_db
from .auth import authenticate_user, get_current_user, get_user_profile, security, TOKENS
from fastapi import Security
from fastapi.security import HTTPAuthorizationCredentials
from .realtime import manager

load_dotenv()

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
app.mount(
    "/data",
    StaticFiles(directory=os.path.join(os.path.dirname(__file__), "..", "data")),
    name="data",
)

init_db()


def compute_inventory(movements_list):
    inventory = {
        EquipmentType.desktop: 0,
        EquipmentType.laptop: 0,
        EquipmentType.screen: 0,
        EquipmentType.other: 0,
    }
    for record in movements_list:
        if record.movement_type == MovementType.entry:
            inventory[record.equipment_type] += record.quantity
        else:
            inventory[record.equipment_type] -= record.quantity
    return inventory


def get_inventory_data():
    movements_list = load_movements()
    return {k.value: v for k, v in compute_inventory(movements_list).items()}


def build_forecast() -> ForecastResponse:
    movements_list = load_movements()
    last_30 = [
        m for m in movements_list
        if m.movement_type == MovementType.exit and m.timestamp >= datetime.utcnow() - timedelta(days=30)
    ]
    total_exit = sum(m.quantity for m in last_30)
    avg_daily = total_exit / 30 if total_exit else 0.0
    current_stock = sum(get_inventory_data().values())
    reorder_threshold = max(10, int(avg_daily * 5 + 5))
    estimated_days = current_stock / avg_daily if avg_daily > 0 else None
    recommendation = (
        "Passer commande rapidement" if current_stock <= reorder_threshold else "Stock suffisant pour le moment"
    )
    return ForecastResponse(
        current_stock=current_stock,
        average_daily_exit=round(avg_daily, 2),
        reorder_threshold=reorder_threshold,
        estimated_days_to_empty=round(estimated_days, 1) if estimated_days else None,
        recommendation=recommendation,
    )


@app.post("/login")
def login(payload: AuthRequest):
    token = authenticate_user(payload.username, payload.password)
    return {"access_token": token, "token_type": "bearer"}


@app.post("/logout")
def logout(credentials: HTTPAuthorizationCredentials = Security(security)):
    token = credentials.credentials
    TOKENS.pop(token, None)
    return {"status": "ok"}


@app.get("/inventory")
def get_inventory(current_user: str = get_current_user):
    return {"inventory": {k.value: v for k, v in inventory.items()}}


@app.get("/me")
def get_me(current_user: str = get_current_user):
    return {"user": get_user_profile(current_user)}


@app.get("/movements")
def get_movements(current_user: str = get_current_user):
    return {"movements": [m.dict() for m in load_movements()]}


@app.get("/forecast")
def get_forecast(current_user: str = get_current_user):
    return build_forecast().dict()


@app.post("/entries")
def add_entry(item: EquipmentItem, background_tasks: BackgroundTasks, current_user: str = get_current_user):
    record = MovementRecord(
        id=0,
        timestamp=datetime.utcnow(),
        movement_type=MovementType.entry,
        equipment_type=item.equipment_type,
        quantity=item.quantity,
        serial_number=item.serial_number,
        model=item.model,
        destination=item.destination,
        notes=item.notes,
    )
    persisted = append_movement(record)
    asyncio.create_task(manager.broadcast({
        "inventory": get_inventory_data(),
        "forecast": build_forecast().dict(),
    }))
    return {"status": "ok", "movement": persisted.dict()}


@app.post("/exits")
def add_exit(item: EquipmentItem, background_tasks: BackgroundTasks, current_user: str = get_current_user):
    inventory = compute_inventory(load_movements())
    if inventory[item.equipment_type] < item.quantity:
        return {"status": "error", "detail": "Stock insuffisant pour ce type de matériel."}
    record = MovementRecord(
        id=0,
        timestamp=datetime.utcnow(),
        movement_type=MovementType.exit,
        equipment_type=item.equipment_type,
        quantity=item.quantity,
        serial_number=item.serial_number,
        model=item.model,
        destination=item.destination,
        notes=item.notes,
    )
    persisted = append_movement(record)
    asyncio.create_task(manager.broadcast({
        "inventory": get_inventory_data(),
        "forecast": build_forecast().dict(),
    }))
    return {"status": "ok", "movement": persisted.dict()}


@app.websocket("/ws/updates")
async def websocket_updates(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@app.post("/notify")
def notify_update(current_user: str = get_current_user):
    payload = {
        "inventory": get_inventory_data(),
        "forecast": build_forecast().dict(),
    }
    asyncio.create_task(manager.broadcast(payload))
    return {"status": "broadcast_sent"}
