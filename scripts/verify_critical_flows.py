import os
import sys
import tempfile
from datetime import datetime

from fastapi import HTTPException


def main() -> None:
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    if root_dir not in sys.path:
        sys.path.insert(0, root_dir)

    db_path = os.path.join(tempfile.gettempdir(), f"asset-equity-verify-{os.getpid()}.db")
    if os.path.exists(db_path):
        os.remove(db_path)
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path.replace(os.sep, '/')}"
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

    from backend.app.main import assess_manager_review, build_forecast, build_stock_items, get_inventory_data, parse_csv_serials, require_serials_for_entry
    from backend.app.models import EquipmentItem, EquipmentType, MovementRecord, MovementType
    from backend.app.storage import (
        append_movement,
        get_available_entry_serial_number_id,
        init_db,
        list_entry_serial_numbers,
        load_stock_policies,
        mark_serial_number_exited,
        register_entry_serial_numbers,
        update_stock_policy,
    )

    init_db()
    policies = load_stock_policies()
    assert "Desktop" in policies, "Stock policy should exist for each equipment type"
    updated_policy = update_stock_policy(EquipmentType.desktop, {
        "lead_time_days": 60,
        "emergency_days": 14,
        "minimum_stock": 3,
        "target_days": 90,
        "service_factor": 2.05,
    })
    assert updated_policy["lead_time_days"] == 60, updated_policy
    desktop_risk = next(item for item in build_forecast().risks if item.equipment_type == EquipmentType.desktop)
    assert desktop_risk.lead_time_days == 60, desktop_risk
    assert desktop_risk.emergency_reserve_threshold >= 3, desktop_risk

    item = EquipmentItem(type="Desktop", quantity=2, serial_numbers=["SN-A"])
    refused = False
    try:
        require_serials_for_entry(item, ["SN-A"])
    except HTTPException:
        refused = True
    assert refused, "Serialized equipment must require one serial per unit"

    parsed = parse_csv_serials("Numéro de série;Autre\nSN-100;A\n".encode("utf-8"))
    assert parsed == ["SN-100"], parsed

    entry = append_movement(MovementRecord(
        id=0,
        timestamp=datetime.utcnow(),
        movement_type=MovementType.entry,
        equipment_type=EquipmentType.desktop,
        quantity=1,
        initiated_by="admin",
    ))
    report = register_entry_serial_numbers(entry, ["SN-FINAL-001"])
    assert report["imported"] == 1, report
    assert get_inventory_data()["Desktop"] == 1
    assert any(item.serial_number == "SN-FINAL-001" and item.quantity == 1 for item in build_stock_items())
    review = assess_manager_review(EquipmentItem(type="Desktop", quantity=1, serial_number="SN-FINAL-001", model="Model"))
    assert review["manager_review_required"], review

    serial_id = get_available_entry_serial_number_id("SN-FINAL-001", EquipmentType.desktop)
    assert serial_id, "Serial should be available after entry"
    exit_record = append_movement(MovementRecord(
        id=0,
        entry_serial_number_id=serial_id,
        timestamp=datetime.utcnow(),
        movement_type=MovementType.exit,
        equipment_type=EquipmentType.desktop,
        quantity=1,
        serial_number="SN-FINAL-001",
        model="Model",
        destination="IT",
        taken_by="User",
        initiated_by="admin",
    ))
    mark_serial_number_exited("SN-FINAL-001", exit_record.id)
    registry = list_entry_serial_numbers()
    assert registry[0]["status"] == "exited", registry[0]
    assert get_inventory_data()["Desktop"] == 0

    consumable_entry = append_movement(MovementRecord(
        id=0,
        timestamp=datetime.utcnow(),
        movement_type=MovementType.entry,
        equipment_type=EquipmentType.adapter,
        quantity=5,
        initiated_by="admin",
    ))
    consumable_exit = append_movement(MovementRecord(
        id=0,
        material_id=consumable_entry.material_id,
        timestamp=datetime.utcnow(),
        movement_type=MovementType.exit,
        equipment_type=EquipmentType.adapter,
        quantity=2,
        destination="IT",
        taken_by="User",
        initiated_by="admin",
    ))
    assert consumable_exit.entry_serial_number_id is None, consumable_exit
    assert get_inventory_data()["Adaptateur"] == 3

    print("Critical flows OK")


if __name__ == "__main__":
    main()
