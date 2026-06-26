from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, field_validator
from typing import Literal, Optional

class EquipmentType(str, Enum):
    adapter = "Adaptateur"
    power_cable = "Cable d'alimentation"
    hdmi_cable_15m = "Cable HDMI (15m)"
    hdmi_cable_30m = "Cable HDMI (30m)"
    hdmi_cable_3m = "Cable HDMI (3m)"
    hdmi_cable_5m = "Cable HDMI (5m)"
    cable_locker = "Cable locker"
    black_cable_locker = "Cable locker (noir)"
    headset = "Casque"
    laptop_charger_pin = "Chargeur Laptop Tige"
    laptop_charger_type_c = "Chargeur Laptop Type C"
    desktop = "Desktop"
    complete_desktop_west_region = "Desktop complet (Region Ouest)"
    complete_desktop_edrms = "Desktop complet EDRMS"
    dvd_cd_r = "DVD/CD-R"
    extratime = "Extratime"
    finger = "Finger"
    flash_disk_16gb = "Flash Disk 16GB"
    bixolon_printer = "Imprimante Bixolon"
    evolis_printer = "Imprimante Evolis"
    evolis_printer_libanga = "Imprimante Evolis (Libanga)"
    starlink_kit = "Kit Starlink"
    omnibook_laptop = "Laptop OmniBook"
    omnibook_laptop_west_region = "Laptop OmniBook (Region Ouest)"
    pavilion_laptop = "Laptop Pavillon"
    probook_laptop = "Laptop ProBook"
    probook_laptop_libanga = "Laptop ProBook (Libanga)"
    probook_laptop_edrms = "Laptop ProBook (EDRMS)"
    probook_laptop_west_region = "Laptop ProBook (Region Ouest)"
    external_dvd_cd_reader_tecsa = "Lecteur DVD/CD externe Tecsa"
    monitor = "Moniteur"
    monitor_24_inches = "Moniteur Diagonal 24 pouces"
    pen_bk = "Pen BK"
    extratime_roll = "Rouleau Extratime"
    router = "Routeur"
    bixolon_ribbon = "Ruban Bixolon"
    monochrome_ribbon_black_1 = "Ruban monochrome (black 1)"
    monochrome_ribbon_black_2 = "Ruban monochrome (black 2)"
    monochrome_ribbon_color = "Ruban monochrome (couleur)"
    monochrome_ribbon_white = "Ruban monochrome (white)"
    laptop_bag = "Sac Laptop"
    biometric_scanner_kojak = "Scanner biometrique (Kojak)"
    ricoh_scanner = "Scanner Ricoh"
    wired_mouse = "Souris avec fil"
    wireless_mouse_with_battery = "Souris sans fil (avec pile)"
    wireless_mouse_without_battery = "Souris sans fil (sans pile)"
    laptop_stand = "Support Laptop"
    switch_24_ports = "Switch 24 ports"
    switch_48_ports = "Switch 48 ports"
    central_unit = "Unité Centrale"
    webcam = "Webcam"
    laptop = "Laptop"
    screen = "Ecran"
    mouse = "Souris"
    switch = "Switch"
    keyboard = "Clavier"
    other = "Other"


SERIALIZED_EQUIPMENT_TYPES = {
    EquipmentType.desktop,
    EquipmentType.complete_desktop_west_region,
    EquipmentType.complete_desktop_edrms,
    EquipmentType.finger,
    EquipmentType.bixolon_printer,
    EquipmentType.evolis_printer,
    EquipmentType.evolis_printer_libanga,
    EquipmentType.omnibook_laptop,
    EquipmentType.omnibook_laptop_west_region,
    EquipmentType.pavilion_laptop,
    EquipmentType.probook_laptop,
    EquipmentType.probook_laptop_libanga,
    EquipmentType.probook_laptop_edrms,
    EquipmentType.probook_laptop_west_region,
    EquipmentType.monitor,
    EquipmentType.monitor_24_inches,
    EquipmentType.router,
    EquipmentType.biometric_scanner_kojak,
    EquipmentType.ricoh_scanner,
    EquipmentType.switch_24_ports,
    EquipmentType.switch_48_ports,
    EquipmentType.central_unit,
    EquipmentType.webcam,
    EquipmentType.laptop,
    EquipmentType.screen,
    EquipmentType.switch,
}

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
    role: Optional[Literal["admin", "user", "manager", "auditor"]] = None
    photo_url: Optional[str] = None
    is_active: Optional[bool] = None

class AdminUserCreate(BaseModel):
    username: str
    display_name: str
    password: str
    role: Literal["admin", "user", "manager", "auditor"] = "user"
    photo_url: Optional[str] = None

class PhotoUpload(BaseModel):
    filename: str
    data_url: str
    target_username: Optional[str] = None
    persist: bool = True


class StockPolicyUpdate(BaseModel):
    lead_time_days: int = Field(..., ge=1, le=365)
    emergency_days: int = Field(..., ge=1, le=90)
    minimum_stock: int = Field(..., ge=0, le=10000)
    target_days: int = Field(..., ge=1, le=365)
    service_factor: float = Field(..., ge=0.0, le=4.0)

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
    serial_numbers: Optional[list[str]] = None
    model: Optional[str] = None

class ForecastRisk(BaseModel):
    equipment_type: EquipmentType
    current_stock: int
    average_daily_exit: float
    demand_std_dev: float = 0.0
    demand_window_days: int = 90
    lead_time_days: int = 14
    safety_stock: int = 0
    reorder_threshold: int
    emergency_reserve_threshold: int
    target_stock: int = 0
    estimated_days_to_empty: Optional[float]
    exits_locked: bool
    manager_review_required: bool = False
    recommendation: str

class MovementRecord(BaseModel):
    id: int
    material_id: Optional[int] = None
    entry_serial_number_id: Optional[int] = None
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
