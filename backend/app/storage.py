import csv
import os
from datetime import datetime
from typing import List
from .models import MovementRecord, MovementType, EquipmentType

STORAGE_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
CSV_FILE = os.path.join(STORAGE_DIR, "stock_log.csv")

os.makedirs(STORAGE_DIR, exist_ok=True)

CSV_FIELDS = [
    "id",
    "timestamp",
    "movement_type",
    "equipment_type",
    "quantity",
    "serial_number",
    "model",
    "destination",
    "notes",
]


def append_movement(record: MovementRecord) -> None:
    write_header = not os.path.exists(CSV_FILE)
    with open(CSV_FILE, mode="a", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=CSV_FIELDS)
        if write_header:
            writer.writeheader()
        writer.writerow({
            "id": record.id,
            "timestamp": record.timestamp.isoformat(),
            "movement_type": record.movement_type,
            "equipment_type": record.equipment_type,
            "quantity": record.quantity,
            "serial_number": record.serial_number or "",
            "model": record.model or "",
            "destination": record.destination or "",
            "notes": record.notes or "",
        })


def load_movements() -> List[MovementRecord]:
    if not os.path.exists(CSV_FILE):
        return []
    movements = []
    with open(CSV_FILE, mode="r", newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            movements.append(MovementRecord(
                id=int(row["id"]),
                timestamp=datetime.fromisoformat(row["timestamp"]),
                movement_type=MovementType(row["movement_type"]),
                equipment_type=EquipmentType(row["equipment_type"]),
                quantity=int(row["quantity"]),
                serial_number=row.get("serial_number") or None,
                model=row.get("model") or None,
                destination=row.get("destination") or None,
                notes=row.get("notes") or None,
            ))
    return movements
