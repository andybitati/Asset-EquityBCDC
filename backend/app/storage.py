import os
from datetime import datetime
from typing import List

from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, ForeignKey, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker

from .config import load_backend_env, writable_runtime_dir
from .models import MovementRecord, MovementType, EquipmentType, SERIALIZED_EQUIPMENT_TYPES

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
    name = Column(String(80), nullable=False, unique=True)
    requires_serial_model = Column(Integer, nullable=False, default=0)


class StockPolicy(Base):
    __tablename__ = "stock_policies"

    id = Column(Integer, primary_key=True, autoincrement=True)
    equipment_type = Column(String(80), ForeignKey("equipment_types.name", onupdate="CASCADE", ondelete="RESTRICT"), nullable=False, unique=True)
    lead_time_days = Column(Integer, nullable=False)
    emergency_days = Column(Integer, nullable=False)
    minimum_stock = Column(Integer, nullable=False)
    target_days = Column(Integer, nullable=False)
    service_factor = Column(String(20), nullable=False)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class Material(Base):
    __tablename__ = "materials"

    id = Column(Integer, primary_key=True, autoincrement=True)
    equipment_type = Column(String(80), ForeignKey("equipment_types.name", onupdate="CASCADE", ondelete="RESTRICT"), nullable=False)
    serial_number = Column(String(255), nullable=True)
    model = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class Movement(Base):
    __tablename__ = "movements"

    id = Column(Integer, primary_key=True, autoincrement=True)
    material_id = Column(Integer, ForeignKey("materials.id", onupdate="CASCADE", ondelete="RESTRICT"), nullable=True)
    entry_serial_number_id = Column(Integer, nullable=True)
    timestamp = Column(DateTime, nullable=False)
    movement_type = Column(String(20), nullable=False)
    equipment_type = Column(String(80), ForeignKey("equipment_types.name", onupdate="CASCADE", ondelete="RESTRICT"), nullable=False)
    quantity = Column(Integer, nullable=False)
    serial_number = Column(String(255), nullable=True)
    model = Column(String(255), nullable=True)
    destination = Column(String(255), nullable=True)
    taken_by = Column(String(255), nullable=True)
    initiated_by = Column(String(80), ForeignKey("users.username", onupdate="CASCADE", ondelete="SET NULL"), nullable=True)
    notes = Column(Text, nullable=True)


class EntrySerialNumber(Base):
    __tablename__ = "entry_serial_numbers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    material_id = Column(Integer, ForeignKey("materials.id", onupdate="CASCADE", ondelete="SET NULL"), nullable=True)
    entry_movement_id = Column(Integer, ForeignKey("movements.id", onupdate="CASCADE", ondelete="SET NULL"), nullable=True)
    exit_movement_id = Column(Integer, ForeignKey("movements.id", onupdate="CASCADE", ondelete="SET NULL"), nullable=True)
    equipment_type = Column(String(80), ForeignKey("equipment_types.name", onupdate="CASCADE", ondelete="RESTRICT"), nullable=False)
    serial_number = Column(String(255), nullable=False)
    normalized_serial_number = Column(String(255), nullable=False, unique=True)
    status = Column(String(20), nullable=False, default="in_stock")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


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
    seed_stock_policies()
    ensure_movement_columns()
    ensure_user_columns()
    ensure_entry_serial_columns()
    migrate_existing_movements_to_materials()
    seed_entry_serial_numbers_from_movements()
    ensure_mysql_foreign_keys()


def seed_equipment_types() -> None:
    tracked_keywords = (
        "Desktop",
        "Laptop",
        "Moniteur",
        "Scanner",
        "Switch",
        "Routeur",
        "Imprimante",
        "Finger",
        "Webcam",
        "Unité Centrale",
    )
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
                    requires_serial_model=1 if any(keyword in equipment_type.value for keyword in tracked_keywords) else 0,
                ))
        session.commit()
    finally:
        session.close()


def default_stock_policy(equipment_type: EquipmentType) -> dict:
    if equipment_type in SERIALIZED_EQUIPMENT_TYPES:
        return {
            "lead_time_days": 30,
            "emergency_days": 7,
            "minimum_stock": 1,
            "target_days": 45,
            "service_factor": 1.65,
        }
    return {
        "lead_time_days": 14,
        "emergency_days": 5,
        "minimum_stock": 2,
        "target_days": 30,
        "service_factor": 1.28,
    }


def seed_stock_policies() -> None:
    session = get_session()
    try:
        existing = {
            row.equipment_type
            for row in session.query(StockPolicy).all()
        }
        for equipment_type in EquipmentType:
            if equipment_type.value in existing:
                continue
            policy = default_stock_policy(equipment_type)
            session.add(StockPolicy(
                equipment_type=equipment_type.value,
                lead_time_days=policy["lead_time_days"],
                emergency_days=policy["emergency_days"],
                minimum_stock=policy["minimum_stock"],
                target_days=policy["target_days"],
                service_factor=str(policy["service_factor"]),
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
    if "entry_serial_number_id" not in existing_columns:
        missing_columns.append("ADD COLUMN entry_serial_number_id INT")
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


def ensure_entry_serial_columns() -> None:
    inspector = inspect(engine)
    if "entry_serial_numbers" not in inspector.get_table_names():
        return
    existing_columns = {column["name"] for column in inspector.get_columns("entry_serial_numbers")}
    missing_columns = []
    if "exit_movement_id" not in existing_columns:
        missing_columns.append("ADD COLUMN exit_movement_id INT")
    if missing_columns:
        with engine.begin() as connection:
            for statement in missing_columns:
                connection.execute(text(f"ALTER TABLE entry_serial_numbers {statement}"))


def mysql_constraint_exists(connection, constraint_name: str) -> bool:
    return bool(connection.execute(text(
        "SELECT COUNT(*) FROM information_schema.TABLE_CONSTRAINTS "
        "WHERE CONSTRAINT_SCHEMA = DATABASE() AND CONSTRAINT_NAME = :constraint_name"
    ), {"constraint_name": constraint_name}).scalar())


def add_mysql_constraint(connection, constraint_name: str, statement: str) -> None:
    if not mysql_constraint_exists(connection, constraint_name):
        connection.execute(text(statement))


def drop_mysql_constraint(connection, table_name: str, constraint_name: str) -> None:
    if mysql_constraint_exists(connection, constraint_name):
        connection.execute(text(f"ALTER TABLE {table_name} DROP FOREIGN KEY {constraint_name}"))


def ensure_mysql_foreign_keys() -> None:
    if engine.dialect.name not in {"mysql", "mariadb"}:
        return

    with engine.begin() as connection:
        drop_mysql_constraint(connection, "materials", "fk_materials_equipment_type")
        drop_mysql_constraint(connection, "movements", "fk_movements_equipment_type")
        drop_mysql_constraint(connection, "entry_serial_numbers", "fk_entry_serials_equipment_type")
        drop_mysql_constraint(connection, "stock_policies", "fk_stock_policies_equipment_type")

        connection.execute(text("ALTER TABLE equipment_types MODIFY name VARCHAR(80) NOT NULL"))
        connection.execute(text("ALTER TABLE materials MODIFY equipment_type VARCHAR(80) NOT NULL"))
        connection.execute(text("ALTER TABLE movements MODIFY equipment_type VARCHAR(80) NOT NULL"))
        connection.execute(text("ALTER TABLE entry_serial_numbers MODIFY equipment_type VARCHAR(80) NOT NULL"))
        connection.execute(text("ALTER TABLE stock_policies MODIFY equipment_type VARCHAR(80) NOT NULL"))
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
            "fk_movements_entry_serial_number",
            "ALTER TABLE movements ADD CONSTRAINT fk_movements_entry_serial_number "
            "FOREIGN KEY (entry_serial_number_id) REFERENCES entry_serial_numbers(id) "
            "ON UPDATE CASCADE ON DELETE SET NULL",
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
            "fk_stock_policies_equipment_type",
            "ALTER TABLE stock_policies ADD CONSTRAINT fk_stock_policies_equipment_type "
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
            "fk_entry_serials_material",
            "ALTER TABLE entry_serial_numbers ADD CONSTRAINT fk_entry_serials_material "
            "FOREIGN KEY (material_id) REFERENCES materials(id) "
            "ON UPDATE CASCADE ON DELETE SET NULL",
        )
        add_mysql_constraint(
            connection,
            "fk_entry_serials_entry_movement",
            "ALTER TABLE entry_serial_numbers ADD CONSTRAINT fk_entry_serials_entry_movement "
            "FOREIGN KEY (entry_movement_id) REFERENCES movements(id) "
            "ON UPDATE CASCADE ON DELETE SET NULL",
        )
        add_mysql_constraint(
            connection,
            "fk_entry_serials_exit_movement",
            "ALTER TABLE entry_serial_numbers ADD CONSTRAINT fk_entry_serials_exit_movement "
            "FOREIGN KEY (exit_movement_id) REFERENCES movements(id) "
            "ON UPDATE CASCADE ON DELETE SET NULL",
        )
        add_mysql_constraint(
            connection,
            "fk_entry_serials_equipment_type",
            "ALTER TABLE entry_serial_numbers ADD CONSTRAINT fk_entry_serials_equipment_type "
            "FOREIGN KEY (equipment_type) REFERENCES equipment_types(name) "
            "ON UPDATE CASCADE ON DELETE RESTRICT",
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


def serialize_stock_policy(row: StockPolicy) -> dict:
    return {
        "equipment_type": row.equipment_type,
        "lead_time_days": row.lead_time_days,
        "emergency_days": row.emergency_days,
        "minimum_stock": row.minimum_stock,
        "target_days": row.target_days,
        "service_factor": float(row.service_factor),
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def load_stock_policies() -> dict[str, dict]:
    session = get_session()
    try:
        rows = session.query(StockPolicy).all()
        policies = {row.equipment_type: serialize_stock_policy(row) for row in rows}
        for equipment_type in EquipmentType:
            policies.setdefault(equipment_type.value, {
                "equipment_type": equipment_type.value,
                **default_stock_policy(equipment_type),
                "updated_at": None,
            })
        return policies
    finally:
        session.close()


def update_stock_policy(equipment_type: EquipmentType, payload: dict) -> dict:
    session = get_session()
    try:
        row = session.query(StockPolicy).filter(StockPolicy.equipment_type == equipment_type.value).first()
        if not row:
            row = StockPolicy(equipment_type=equipment_type.value)
            session.add(row)
        row.lead_time_days = int(payload["lead_time_days"])
        row.emergency_days = int(payload["emergency_days"])
        row.minimum_stock = int(payload["minimum_stock"])
        row.target_days = int(payload["target_days"])
        row.service_factor = str(float(payload["service_factor"]))
        row.updated_at = datetime.utcnow()
        session.commit()
        session.refresh(row)
        return serialize_stock_policy(row)
    finally:
        session.close()


def normalize_serial_number(serial_number: str | None) -> str:
    return " ".join(str(serial_number or "").strip().split()).casefold()


def classify_entry_serial_numbers(serial_numbers: list[str]) -> dict:
    report = {
        "new": [],
        "duplicates": [],
        "already_exited": [],
    }
    if not serial_numbers:
        return report
    session = get_session()
    try:
        for serial_number in serial_numbers:
            normalized = normalize_serial_number(serial_number)
            existing = session.query(EntrySerialNumber).filter(
                EntrySerialNumber.normalized_serial_number == normalized
            ).first()
            if not existing:
                report["new"].append(serial_number)
            elif existing.status == "in_stock":
                report["duplicates"].append(serial_number)
            else:
                report["already_exited"].append(serial_number)
        return report
    finally:
        session.close()


def get_available_entry_serial_number_id(serial_number: str | None, equipment_type: EquipmentType | str | None = None) -> int | None:
    normalized = normalize_serial_number(serial_number)
    if not normalized:
        return None
    type_value = equipment_type.value if isinstance(equipment_type, EquipmentType) else equipment_type
    session = get_session()
    try:
        query = session.query(EntrySerialNumber).filter(
            EntrySerialNumber.normalized_serial_number == normalized,
            EntrySerialNumber.status == "in_stock",
        )
        if type_value:
            query = query.filter(EntrySerialNumber.equipment_type == str(type_value))
        row = query.first()
        return row.id if row else None
    finally:
        session.close()


def register_entry_serial_numbers(record: MovementRecord, serial_numbers: list[str]) -> dict:
    report = {
        "imported": 0,
        "reactivated": 0,
        "duplicates": [],
        "already_exited": [],
    }
    if not serial_numbers:
        return report
    session = get_session()
    try:
        stored = session.get(Movement, record.id)
        material_id = stored.material_id if stored else record.material_id
        equipment_type = record.equipment_type.value if isinstance(record.equipment_type, EquipmentType) else str(record.equipment_type)
        for serial_number in serial_numbers:
            normalized = normalize_serial_number(serial_number)
            existing = session.query(EntrySerialNumber).filter(
                EntrySerialNumber.normalized_serial_number == normalized
            ).first()
            if existing:
                if existing.status == "in_stock":
                    report["duplicates"].append(serial_number.strip())
                else:
                    report["already_exited"].append(serial_number.strip())
                continue
            session.add(EntrySerialNumber(
                material_id=material_id,
                entry_movement_id=record.id,
                equipment_type=equipment_type,
                serial_number=serial_number.strip(),
                normalized_serial_number=normalized,
                status="in_stock",
            ))
            report["imported"] += 1
        session.commit()
        return report
    finally:
        session.close()


def list_entry_serial_numbers(status: str | None = None, q: str | None = None, limit: int = 1000) -> list[dict]:
    session = get_session()
    try:
        query = session.query(EntrySerialNumber).order_by(EntrySerialNumber.updated_at.desc(), EntrySerialNumber.id.desc())
        if status:
            query = query.filter(EntrySerialNumber.status == status)
        if q:
            needle = f"%{q.strip()}%"
            query = query.filter(
                (EntrySerialNumber.serial_number.like(needle))
                | (EntrySerialNumber.equipment_type.like(needle))
            )
        rows = query.limit(limit).all()
        return [
            {
                "id": row.id,
                "material_id": row.material_id,
                "entry_movement_id": row.entry_movement_id,
                "exit_movement_id": row.exit_movement_id,
                "equipment_type": row.equipment_type,
                "serial_number": row.serial_number,
                "status": row.status,
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "updated_at": row.updated_at.isoformat() if row.updated_at else None,
            }
            for row in rows
        ]
    finally:
        session.close()


def mark_serial_number_exited(serial_number: str, exit_movement_id: int) -> None:
    normalized = normalize_serial_number(serial_number)
    session = get_session()
    try:
        row = session.query(EntrySerialNumber).filter(
            EntrySerialNumber.normalized_serial_number == normalized,
            EntrySerialNumber.status == "in_stock",
        ).first()
        if row:
            row.status = "exited"
            row.exit_movement_id = exit_movement_id
            row.updated_at = datetime.utcnow()
            movement = session.get(Movement, exit_movement_id)
            if movement:
                movement.entry_serial_number_id = row.id
            session.commit()
    finally:
        session.close()


def seed_entry_serial_numbers_from_movements() -> None:
    session = get_session()
    try:
        rows = session.query(Movement).filter(
            Movement.serial_number.is_not(None),
            Movement.serial_number != "",
        ).all()
        for row in rows:
            normalized = normalize_serial_number(row.serial_number)
            if not normalized:
                continue
            existing = session.query(EntrySerialNumber).filter(
                EntrySerialNumber.normalized_serial_number == normalized
            ).first()
            if existing:
                continue
            status = "exited" if row.movement_type == MovementType.exit.value else "in_stock"
            session.add(EntrySerialNumber(
                material_id=row.material_id,
                entry_movement_id=row.id if row.movement_type == MovementType.entry.value else None,
                exit_movement_id=row.id if row.movement_type == MovementType.exit.value else None,
                equipment_type=row.equipment_type,
                serial_number=row.serial_number,
                normalized_serial_number=normalized,
                status=status,
            ))
        session.commit()
    finally:
        session.close()


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
                entry_serial_number_id=row.entry_serial_number_id,
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
            entry_serial_number_id=record.entry_serial_number_id,
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
            entry_serial_number_id=stored.entry_serial_number_id,
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
                entry_serial_number_id=row.entry_serial_number_id,
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
