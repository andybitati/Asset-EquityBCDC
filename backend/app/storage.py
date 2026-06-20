import os
from datetime import datetime
from typing import List

from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text
from sqlalchemy.orm import declarative_base, sessionmaker

from .models import MovementRecord, MovementType, EquipmentType

load_dotenv()

STORAGE_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
os.makedirs(STORAGE_DIR, exist_ok=True)

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    sqlite_file = os.path.join(STORAGE_DIR, "asset_equity.db")
    DATABASE_URL = f"sqlite:///{sqlite_file}"

engine = create_engine(DATABASE_URL, future=True, echo=False)
SessionLocal = sessionmaker(bind=engine, future=True, expire_on_commit=False)
Base = declarative_base()


class Movement(Base):
    __tablename__ = "movements"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, nullable=False)
    movement_type = Column(String(20), nullable=False)
    equipment_type = Column(String(20), nullable=False)
    quantity = Column(Integer, nullable=False)
    serial_number = Column(String(255), nullable=True)
    model = Column(String(255), nullable=True)
    destination = Column(String(255), nullable=True)
    notes = Column(Text, nullable=True)


def init_db() -> None:
    Base.metadata.create_all(engine)


def get_session():
    return SessionLocal()


def append_movement(record: MovementRecord) -> MovementRecord:
    session = get_session()
    try:
        stored = Movement(
            timestamp=record.timestamp,
            movement_type=(record.movement_type.value if isinstance(record.movement_type, MovementType) else str(record.movement_type)),
            equipment_type=(record.equipment_type.value if isinstance(record.equipment_type, EquipmentType) else str(record.equipment_type)),
            quantity=record.quantity,
            serial_number=record.serial_number,
            model=record.model,
            destination=record.destination,
            notes=record.notes,
        )
        session.add(stored)
        session.commit()
        session.refresh(stored)
        return MovementRecord(
            id=stored.id,
            timestamp=stored.timestamp,
            movement_type=MovementType(stored.movement_type),
            equipment_type=EquipmentType(stored.equipment_type),
            quantity=stored.quantity,
            serial_number=stored.serial_number,
            model=stored.model,
            destination=stored.destination,
            notes=stored.notes,
        )
    finally:
        session.close()


def load_movements() -> List[MovementRecord]:
    session = get_session()
    try:
        rows = session.query(Movement).order_by(Movement.id).all()
        return [
            MovementRecord(
                id=row.id,
                timestamp=row.timestamp,
                movement_type=MovementType(row.movement_type),
                equipment_type=EquipmentType(row.equipment_type),
                quantity=row.quantity,
                serial_number=row.serial_number,
                model=row.model,
                destination=row.destination,
                notes=row.notes,
            )
            for row in rows
        ]
    finally:
        session.close()
