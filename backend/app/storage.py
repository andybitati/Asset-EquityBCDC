import os
from datetime import datetime
from typing import List

from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker

from .config import load_backend_env, runtime_dir
from .models import MovementRecord, MovementType, EquipmentType

load_backend_env()

STORAGE_DIR = os.getenv("STORAGE_DIR", os.path.join(runtime_dir(), "data"))
os.makedirs(STORAGE_DIR, exist_ok=True)

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    sqlite_file = os.path.join(STORAGE_DIR, "asset_equity.db")
    DATABASE_URL = f"sqlite:///{sqlite_file}"

engine = create_engine(DATABASE_URL, future=True, echo=False)
SessionLocal = sessionmaker(bind=engine, future=True, expire_on_commit=False)
Base = declarative_base()


class EquipmentTypeCatalog(Base):
    __tablename__ = "equipment_types"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(40), nullable=False, unique=True)
    requires_serial_model = Column(Integer, nullable=False, default=0)


class Material(Base):
    __tablename__ = "materials"

    id = Column(Integer, primary_key=True, autoincrement=True)
    equipment_type = Column(String(20), nullable=False)
    serial_number = Column(String(255), nullable=True)
    model = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class Movement(Base):
    __tablename__ = "movements"

    id = Column(Integer, primary_key=True, autoincrement=True)
    material_id = Column(Integer, nullable=True)
    timestamp = Column(DateTime, nullable=False)
    movement_type = Column(String(20), nullable=False)
    equipment_type = Column(String(20), nullable=False)
    quantity = Column(Integer, nullable=False)
    serial_number = Column(String(255), nullable=True)
    model = Column(String(255), nullable=True)
    destination = Column(String(255), nullable=True)
    taken_by = Column(String(255), nullable=True)
    initiated_by = Column(String(255), nullable=True)
    notes = Column(Text, nullable=True)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(80), nullable=False, unique=True)
    display_name = Column(String(120), nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(30), nullable=False, default="user")
    photo_url = Column(String(500), nullable=True)
    is_active = Column(Integer, nullable=False, default=1)
    last_credentials_changed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    actor_username = Column(String(80), nullable=True)
    action = Column(String(80), nullable=False)
    entity_type = Column(String(80), nullable=False)
    entity_id = Column(String(120), nullable=True)
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)
    ip_address = Column(String(80), nullable=True)
    user_agent = Column(String(500), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class SessionToken(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    token = Column(String(255), nullable=False, unique=True)
    username = Column(String(80), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    revoked_at = Column(DateTime, nullable=True)


def init_db() -> None:
    Base.metadata.create_all(engine)
    seed_equipment_types()
    ensure_movement_columns()
    ensure_user_columns()
    migrate_existing_movements_to_materials()


def seed_equipment_types() -> None:
    tracked_types = {
        EquipmentType.desktop.value,
        EquipmentType.laptop.value,
        EquipmentType.screen.value,
        EquipmentType.switch.value,
        EquipmentType.router.value,
    }
    session = get_session()
    try:
        existing = {
            row.name
            for row in session.query(EquipmentTypeCatalog).all()
        }
        for equipment_type in EquipmentType:
            if equipment_type.value not in existing:
                session.add(EquipmentTypeCatalog(
                    name=equipment_type.value,
                    requires_serial_model=1 if equipment_type.value in tracked_types else 0,
                ))
        session.commit()
    finally:
        session.close()


def ensure_movement_columns() -> None:
    inspector = inspect(engine)
    if "movements" not in inspector.get_table_names():
        return
    existing_columns = {column["name"] for column in inspector.get_columns("movements")}
    missing_columns = []
    if "material_id" not in existing_columns:
        missing_columns.append("ADD COLUMN material_id INT")
    if "taken_by" not in existing_columns:
        missing_columns.append("ADD COLUMN taken_by VARCHAR(255)")
    if "initiated_by" not in existing_columns:
        missing_columns.append("ADD COLUMN initiated_by VARCHAR(255)")
    if missing_columns:
        with engine.begin() as connection:
            for statement in missing_columns:
                connection.execute(text(f"ALTER TABLE movements {statement}"))


def ensure_user_columns() -> None:
    inspector = inspect(engine)
    if "users" not in inspector.get_table_names():
        return
    existing_columns = {column["name"] for column in inspector.get_columns("users")}
    missing_columns = []
    if "photo_url" not in existing_columns:
        missing_columns.append("ADD COLUMN photo_url VARCHAR(500)")
    if "last_credentials_changed_at" not in existing_columns:
        missing_columns.append("ADD COLUMN last_credentials_changed_at DATETIME")
    if missing_columns:
        with engine.begin() as connection:
            for statement in missing_columns:
                connection.execute(text(f"ALTER TABLE users {statement}"))


def get_session():
    return SessionLocal()


def get_or_create_material(session, record: MovementRecord) -> Material:
    if record.material_id:
        material = session.get(Material, record.material_id)
        if material:
            return material

    material = session.query(Material).filter(
        Material.equipment_type == (
            record.equipment_type.value
            if isinstance(record.equipment_type, EquipmentType)
            else str(record.equipment_type)
        ),
        Material.serial_number == record.serial_number,
        Material.model == record.model,
    ).first()
    if material:
        return material

    material = Material(
        equipment_type=(
            record.equipment_type.value
            if isinstance(record.equipment_type, EquipmentType)
            else str(record.equipment_type)
        ),
        serial_number=record.serial_number,
        model=record.model,
        description=record.notes,
    )
    session.add(material)
    session.flush()
    return material


def migrate_existing_movements_to_materials() -> None:
    session = get_session()
    try:
        rows = session.query(Movement).filter(Movement.material_id.is_(None)).all()
        for row in rows:
            record = MovementRecord(
                id=row.id,
                material_id=row.material_id,
                timestamp=row.timestamp,
                movement_type=MovementType(row.movement_type),
                equipment_type=EquipmentType(row.equipment_type),
                quantity=row.quantity,
                serial_number=row.serial_number,
                model=row.model,
                destination=row.destination,
                taken_by=row.taken_by,
                initiated_by=row.initiated_by,
                notes=row.notes,
            )
            row.material_id = get_or_create_material(session, record).id
        session.commit()
    finally:
        session.close()


def append_movement(record: MovementRecord) -> MovementRecord:
    session = get_session()
    try:
        material = get_or_create_material(session, record)
        stored = Movement(
            material_id=material.id,
            timestamp=record.timestamp,
            movement_type=(record.movement_type.value if isinstance(record.movement_type, MovementType) else str(record.movement_type)),
            equipment_type=material.equipment_type,
            quantity=record.quantity,
            serial_number=material.serial_number,
            model=material.model,
            destination=record.destination,
            taken_by=record.taken_by,
            initiated_by=record.initiated_by,
            notes=record.notes,
        )
        session.add(stored)
        session.commit()
        session.refresh(stored)
        return MovementRecord(
            id=stored.id,
            material_id=stored.material_id,
            timestamp=stored.timestamp,
            movement_type=MovementType(stored.movement_type),
            equipment_type=EquipmentType(stored.equipment_type),
            quantity=stored.quantity,
            serial_number=stored.serial_number,
            model=stored.model,
            destination=stored.destination,
            taken_by=stored.taken_by,
            initiated_by=stored.initiated_by,
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
                material_id=row.material_id,
                timestamp=row.timestamp,
                movement_type=MovementType(row.movement_type),
                equipment_type=EquipmentType(row.equipment_type),
                quantity=row.quantity,
                serial_number=row.serial_number,
                model=row.model,
                destination=row.destination,
                taken_by=row.taken_by,
                initiated_by=row.initiated_by,
                notes=row.notes,
            )
            for row in rows
        ]
    finally:
        session.close()
