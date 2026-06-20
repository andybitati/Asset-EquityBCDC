import os
import asyncio
from datetime import datetime, timedelta
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
from .storage import append_movement, load_movements
from .auth import authenticate_user, get_current_user
from .realtime import manager

app = FastAPI(title="Assets EquityBCDC Backend")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount(
    "/data",
    StaticFiles(directory=os.path.join(os.path.dirname(__file__), "..", "data")),
    name="data",
)

movements = load_movements()
next_id = max((m.id for m in movements), default=0) + 1

inventory = {
    EquipmentType.desktop: 0,
    EquipmentType.laptop: 0,
    EquipmentType.screen: 0,
    EquipmentType.other: 0,
}
for record in movements:
    if record.movement_type == MovementType.entry:
        inventory[record.equipment_type] += record.quantity
    else:
        inventory[record.equipment_type] -= record.quantity


def persist_movement(record: MovementRecord) -> None:
    append_movement(record)


def update_inventory(record: MovementRecord) -> None:
    if record.movement_type == MovementType.entry:
        inventory[record.equipment_type] += record.quantity
    else:
        inventory[record.equipment_type] -= record.quantity


def build_forecast() -> ForecastResponse:
    last_30 = [m for m in movements if m.movement_type == MovementType.exit and m.timestamp >= datetime.utcnow() - timedelta(days=30)]
    total_exit = sum(m.quantity for m in last_30)
    avg_daily = total_exit / 30 if total_exit else 0.0
    current_stock = sum(inventory.values())
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


@app.get("/inventory")
def get_inventory(current_user: str = get_current_user):
    return {"inventory": {k.value: v for k, v in inventory.items()}}


@app.get("/movements")
def get_movements(current_user: str = get_current_user):
    return {"movements": [m.dict() for m in movements]}


@app.get("/forecast")
def get_forecast(current_user: str = get_current_user):
    return build_forecast().dict()


@app.post("/entries")
def add_entry(item: EquipmentItem, background_tasks: BackgroundTasks, current_user: str = get_current_user):
    global next_id
    record = MovementRecord(
        id=next_id,
        timestamp=datetime.utcnow(),
        movement_type=MovementType.entry,
        equipment_type=item.equipment_type,
        quantity=item.quantity,
        serial_number=item.serial_number,
        model=item.model,
        destination=item.destination,
        notes=item.notes,
    )
    next_id += 1
    movements.append(record)
    update_inventory(record)
    background_tasks.add_task(persist_movement, record)
    asyncio.create_task(manager.broadcast({
        "inventory": {k.value: v for k, v in inventory.items()},
        "forecast": build_forecast().dict(),
    }))
    return {"status": "ok", "movement": record.dict()}


@app.post("/exits")
def add_exit(item: EquipmentItem, background_tasks: BackgroundTasks, current_user: str = get_current_user):
    global next_id
    if inventory[item.equipment_type] < item.quantity:
        return {"status": "error", "detail": "Stock insuffisant pour ce type de matériel."}
    record = MovementRecord(
        id=next_id,
        timestamp=datetime.utcnow(),
        movement_type=MovementType.exit,
        equipment_type=item.equipment_type,
        quantity=item.quantity,
        serial_number=item.serial_number,
        model=item.model,
        destination=item.destination,
        notes=item.notes,
    )
    next_id += 1
    movements.append(record)
    update_inventory(record)
    background_tasks.add_task(persist_movement, record)
    asyncio.create_task(manager.broadcast({
        "inventory": {k.value: v for k, v in inventory.items()},
        "forecast": build_forecast().dict(),
    }))
    return {"status": "ok", "movement": record.dict()}


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
        "inventory": {k.value: v for k, v in inventory.items()},
        "forecast": build_forecast().dict(),
    }
    import asyncio

    asyncio.create_task(manager.broadcast(payload))
    return {"status": "broadcast_sent"}
