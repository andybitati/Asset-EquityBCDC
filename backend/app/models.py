from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, field_validator
from typing import Optional

class EquipmentType(str, Enum):
    desktop = "Desktop"
    laptop = "Laptop"
    screen = "Ecran"
    mouse = "Souris"
    switch = "Switch"
    router = "Routeur"
    keyboard = "Clavier"
    other = "Other"

class MovementType(str, Enum):
    entry = "Entrée"
    exit = "Sortie"

class AuthRequest(BaseModel):
    username: str
    password: str

class UserProfileUpdate(BaseModel):
    username: Optional[str] = None
    display_name: Optional[str] = None
    photo_url: Optional[str] = None
    current_password: Optional[str] = None
    new_password: Optional[str] = None

class AdminUserUpdate(BaseModel):
    username: Optional[str] = None
    display_name: Optional[str] = None
    role: Optional[str] = None
    photo_url: Optional[str] = None
    is_active: Optional[bool] = None

class AdminUserCreate(BaseModel):
    username: str
    display_name: str
    password: str
    role: str = "user"
    photo_url: Optional[str] = None

class PhotoUpload(BaseModel):
    filename: str
    data_url: str

class EquipmentBase(BaseModel):
    material_id: Optional[int] = None
    equipment_type: EquipmentType = Field(..., alias="type")
    quantity: int = Field(..., gt=0)
    destination: Optional[str] = None
    taken_by: Optional[str] = None
    initiated_by: Optional[str] = None
    notes: Optional[str] = None

    @field_validator("destination", mode="before", check_fields=False)
    def default_destination(cls, v):
        return v or "Stock"

class EquipmentItem(EquipmentBase):
    serial_number: Optional[str] = None
    model: Optional[str] = None

class ForecastRisk(BaseModel):
    equipment_type: EquipmentType
    current_stock: int
    average_daily_exit: float
    reorder_threshold: int
    emergency_reserve_threshold: int
    estimated_days_to_empty: Optional[float]
    exits_locked: bool
    recommendation: str

class MovementRecord(BaseModel):
    id: int
    material_id: Optional[int] = None
    timestamp: datetime
    movement_type: MovementType
    equipment_type: EquipmentType
    quantity: int
    serial_number: Optional[str] = None
    model: Optional[str] = None
    destination: Optional[str] = None
    taken_by: Optional[str] = None
    initiated_by: Optional[str] = None
    notes: Optional[str] = None

class StockItem(BaseModel):
    material_id: int
    equipment_type: EquipmentType
    quantity: int
    serial_number: Optional[str] = None
    model: Optional[str] = None

class ForecastResponse(BaseModel):
    current_stock: int
    average_daily_exit: float
    reorder_threshold: int
    estimated_days_to_empty: Optional[float]
    recommendation: str
    risks: list[ForecastRisk] = Field(default_factory=list)
