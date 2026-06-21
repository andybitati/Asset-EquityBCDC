import os
from datetime import datetime
from typing import List

from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, ForeignKey, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker

from .config import load_backend_env, writable_runtime_dir
from .models import MovementRecord, MovementType, EquipmentType

load_backend_env()

STORAGE_DIR = os.getenv("STORAGE_DIR", os.path.join(writable_runtime_dir(), "data"))
os.makedirs(STORAGE_DIR, exist_ok=True)

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    sqlite_file = os.path.join(STORAGE_DIR, "asset_equity.db")
    DATABASE_URL = f"sqlite:///{sqlite_file.replace(os.sep, '/')}"

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
    equipment_type = Column(String(40), ForeignKey("equipment_types.name", onupdate="CASCADE", ondelete="RESTRICT"), nullable=False)
    serial_number = Column(String(255), nullable=True)
    model = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class Movement(Base):
    __tablename__ = "movements"

    id = Column(Integer, primary_key=True, autoincrement=True)
    material_id = Column(Integer, ForeignKey("materials.id", onupdate="CASCADE", ondelete="RESTRICT"), nullable=True)
    timestamp = Column(DateTime, nullable=False)
    movement_type = Column(String(20), nullable=False)
    equipment_type = Column(String(40), ForeignKey("equipment_types.name", onupdate="CASCADE", ondelete="RESTRICT"), nullable=False)
    quantity = Column(Integer, nullable=False)
    serial_number = Column(String(255), nullable=True)
    model = Column(String(255), nullable=True)
    destination = Column(String(255), nullable=True)
    taken_by = Column(String(255), nullable=True)
    initiated_by = Column(String(80), ForeignKey("users.username", onupdate="CASCADE", ondelete="SET NULL"), nullable=True)
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
    actor_username = Column(String(80), ForeignKey("users.username", onupdate="CASCADE", ondelete="SET NULL"), nullable=True)
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
    username = Column(String(80), ForeignKey("users.username", onupdate="CASCADE", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    revoked_at = Column(DateTime, nullable=True)


def init_db() -> None:
    Base.metadata.create_all(engine)
    seed_equipment_types()
    ensure_movement_columns()
    ensure_user_columns()
    migrate_existing_movements_to_materials()
    ensure_mysql_foreign_keys()


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


def mysql_constraint_exists(connection, constraint_name: str) -> bool:
    return bool(connection.execute(text(
        "SELECT COUNT(*) FROM information_schema.TABLE_CONSTRAINTS "
        "WHERE CONSTRAINT_SCHEMA = DATABASE() AND CONSTRAINT_NAME = :constraint_name"
    ), {"constraint_name": constraint_name}).scalar())


def add_mysql_constraint(connection, constraint_name: str, statement: str) -> None:
    if not mysql_constraint_exists(connection, constraint_name):
        connection.execute(text(statement))


def ensure_mysql_foreign_keys() -> None:
    if engine.dialect.name not in {"mysql", "mariadb"}:
        return

    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE materials MODIFY equipment_type VARCHAR(40) NOT NULL"))
        connection.execute(text("ALTER TABLE movements MODIFY equipment_type VARCHAR(40) NOT NULL"))
        connection.execute(text("ALTER TABLE movements MODIFY initiated_by VARCHAR(80) NULL"))

        connection.execute(text(
            "UPDATE materials m LEFT JOIN equipment_types et ON et.name = m.equipment_type "
            "SET m.equipment_type = 'Other' WHERE et.name IS NULL"
        ))
        connection.execute(text(
            "UPDATE movements m LEFT JOIN equipment_types et ON et.name = m.equipment_type "
            "SET m.equipment_type = 'Other' WHERE et.name IS NULL"
        ))
        connection.execute(text(
            "UPDATE movements m LEFT JOIN materials mat ON mat.id = m.material_id "
            "SET m.material_id = NULL WHERE m.material_id IS NOT NULL AND mat.id IS NULL"
        ))
        connection.execute(text(
            "UPDATE movements m LEFT JOIN users u ON u.username = m.initiated_by "
            "SET m.initiated_by = NULL WHERE m.initiated_by IS NOT NULL AND u.username IS NULL"
        ))
        connection.execute(text(
            "UPDATE audit_logs a LEFT JOIN users u ON u.username = a.actor_username "
            "SET a.actor_username = NULL WHERE a.actor_username IS NOT NULL AND u.username IS NULL"
        ))
        connection.execute(text(
            "DELETE s FROM sessions s LEFT JOIN users u ON u.username = s.username WHERE u.username IS NULL"
        ))

        add_mysql_constraint(
            connection,
            "fk_materials_equipment_type",
            "ALTER TABLE materials ADD CONSTRAINT fk_materials_equipment_type "
            "FOREIGN KEY (equipment_type) REFERENCES equipment_types(name) "
            "ON UPDATE CASCADE ON DELETE RESTRICT",
        )
        add_mysql_constraint(
            connection,
            "fk_movements_material",
            "ALTER TABLE movements ADD CONSTRAINT fk_movements_material "
            "FOREIGN KEY (material_id) REFERENCES materials(id) "
            "ON UPDATE CASCADE ON DELETE RESTRICT",
        )
        add_mysql_constraint(
            connection,
            "fk_movements_equipment_type",
            "ALTER TABLE movements ADD CONSTRAINT fk_movements_equipment_type "
            "FOREIGN KEY (equipment_type) REFERENCES equipment_types(name) "
            "ON UPDATE CASCADE ON DELETE RESTRICT",
        )
        add_mysql_constraint(
            connection,
            "fk_movements_initiated_by",
            "ALTER TABLE movements ADD CONSTRAINT fk_movements_initiated_by "
            "FOREIGN KEY (initiated_by) REFERENCES users(username) "
            "ON UPDATE CASCADE ON DELETE SET NULL",
        )
        add_mysql_constraint(
            connection,
            "fk_audit_logs_actor",
            "ALTER TABLE audit_logs ADD CONSTRAINT fk_audit_logs_actor "
            "FOREIGN KEY (actor_username) REFERENCES users(username) "
            "ON UPDATE CASCADE ON DELETE SET NULL",
        )
        add_mysql_constraint(
            connection,
            "fk_sessions_user",
            "ALTER TABLE sessions ADD CONSTRAINT fk_sessions_user "
            "FOREIGN KEY (username) REFERENCES users(username) "
            "ON UPDATE CASCADE ON DELETE CASCADE",
        )


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
            serial_number=record.serial_number if record.serial_number is not None else material.serial_number,
            model=record.model if record.model is not None else material.model,
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
