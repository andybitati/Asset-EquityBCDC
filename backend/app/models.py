from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, field_validator
from typing import Optional

class EquipmentType(str, Enum):
    desktop = "Desktop"
    laptop = "Laptop"
    screen = "Ecran"
    other = "Other"

class MovementType(str, Enum):
    entry = "Entrée"
    exit = "Sortie"

class AuthRequest(BaseModel):
    username: str
    password: str

class EquipmentBase(BaseModel):
    equipment_type: EquipmentType = Field(..., alias="type")
    quantity: int = Field(..., gt=0)
    destination: Optional[str] = None
    notes: Optional[str] = None

    @field_validator("destination", mode="before", check_fields=False)
    def default_destination(cls, v):
        return v or "Stock"

class EquipmentItem(EquipmentBase):
    serial_number: Optional[str] = None
    model: Optional[str] = None

    @field_validator("serial_number", "model", mode="before", check_fields=False)
    def require_serial_model_for_core(cls, v, info):
        equipment_type = info.data.get("equipment_type")
        if equipment_type in {EquipmentType.desktop, EquipmentType.laptop, EquipmentType.screen}:
            if not v:
                field_name = info.field_name
                raise ValueError(f"{field_name} est obligatoire pour les équipements {equipment_type}")
        return v

class MovementRecord(BaseModel):
    id: int
    timestamp: datetime
    movement_type: MovementType
    equipment_type: EquipmentType
    quantity: int
    serial_number: Optional[str] = None
    model: Optional[str] = None
    destination: Optional[str] = None
    notes: Optional[str] = None

class ForecastResponse(BaseModel):
    current_stock: int
    average_daily_exit: float
    reorder_threshold: int
    estimated_days_to_empty: Optional[float]
    recommendation: str
