from pydantic import BaseModel
from typing import List, Optional, Dict, Set
from datetime import datetime, timedelta
import random
from enum import Enum, auto

class Permission(Enum):
    MANAGE_USERS = "manage_users"
    MANAGE_EQUIPMENT = "manage_equipment"
    VIEW_LOGS = "view_logs"

class Role(Enum):
    ADMIN = {
        "name": "admin",
        "permissions": {p.value for p in Permission}
    }
    MANAGER = {
        "name": "manager",
        "permissions": {Permission.MANAGE_EQUIPMENT.value, Permission.VIEW_LOGS.value}
    }
    VIEWER = {
        "name": "viewer",
        "permissions": {Permission.VIEW_LOGS.value}
    }

class User(BaseModel):
    id: int
    email: Optional[str] = None
    name: str
    username: str
    password: Optional[str] = None
    role: str = Role.VIEWER.value["name"]
    permissions: Set[str] = set()
    domain: str
    auto_generated: bool = False
    created_at: datetime
    is_active: bool = True

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Automatically set permissions based on role
        for role in Role:
            if role.value["name"] == self.role:
                self.permissions.update(role.value["permissions"])
                break

    def has_permission(self, permission: str) -> bool:
        # First check if user has the specific permission
        if permission in self.permissions:
            return True
        # Then check if user's role has the permission
        for role in Role:
            if role.value["name"] == self.role and permission in role.value["permissions"]:
                return True
        return False

class Equipment(BaseModel):
    id: int
    name: str
    status: str = "online"
    last_checked: datetime
    data_rate: float = 0.0
    created_at: datetime = datetime.now()
    updated_at: datetime = datetime.now()
    ligne: str  # AVS or BBS
    atelier: str  # CMS1, CMS2, or intégration

# Define constants for dropdown menus
LIGNES = [
    {"value": "AVS", "label": "AVS"},
    {"value": "BBS", "label": "BBS"}
]

ATELIERS = {
    "AVS": [
        {"value": "CMS1", "label": "CMS1"},
        {"value": "CMS2", "label": "CMS2"},
        {"value": "intégration", "label": "Intégration"}
    ],
    "BBS": [
        {"value": "CMS1", "label": "CMS1"},
        {"value": "CMS2", "label": "CMS2"},
        {"value": "intégration", "label": "Intégration"}
    ]
}

class EquipmentData(BaseModel):
    timestamp: datetime
    data_rate: float
    status: str

class EquipmentHistory(BaseModel):
    equipment_id: int
    data: List[EquipmentData]

# Create some dummy data
dummy_users = {
    "admin@example.com": User(
        id=1,
        email="admin@example.com",
        name="John Doe",
        username="johndoe",
        password="admin123",
        role=Role.ADMIN.value["name"],
        permissions=set(),
        domain="DESKTOP-YEMNOX",
        created_at=datetime.now()
    ),
    "manager@example.com": User(
        id=2,
        email="manager@example.com",
        name="Jane Smith",
        username="janesmith",
        password="manager123",
        role=Role.MANAGER.value["name"],
        permissions=set(),
        domain="DESKTOP-YEMNOX",
        created_at=datetime.now()
    ),
    "hp": User(
        id=3,
        email="hp@example.com",
        name="HP User",
        username="hp",
        domain="DESKTOP-YEMNOX",
        password="",  # No password needed for Windows auth
        role=Role.ADMIN.value["name"],
        created_at=datetime.now(),
        auto_generated=True
    )

}

# Create dummy equipment
dummy_equipment = [
    # AVS - CMS1
    Equipment(
        id=1,
        name="Router-1",
        status="online",
        last_checked=datetime.now(),
        data_rate=0.0,
        ligne="AVS",
        atelier="CMS1",
        type="router",
        location="Server Room",
        description="Main network router"
    ),
    Equipment(
        id=2,
        name="Switch-1",
        status="online",
        last_checked=datetime.now(),
        data_rate=0.0,
        ligne="AVS",
        atelier="CMS1",
        type="switch",
        location="Server Room",
        description="Main switch"
    ),
    
    # AVS - CMS2
    Equipment(
        id=3,
        name="Server-1",
        status="online",
        last_checked=datetime.now(),
        data_rate=0.0,
        ligne="AVS",
        atelier="CMS2",
        type="server",
        location="Server Room",
        description="Main application server"
    ),
    Equipment(
        id=4,
        name="Storage-1",
        status="online",
        last_checked=datetime.now(),
        data_rate=0.0,
        ligne="AVS",
        atelier="CMS2",
        type="storage",
        location="Server Room",
        description="Primary storage array"
    ),
    
    # AVS - Intégration
    Equipment(
        id=5,
        name="Backup-1",
        status="online",
        last_checked=datetime.now(),
        data_rate=0.0,
        ligne="AVS",
        atelier="intégration",
        type="backup",
        location="Server Room",
        description="Backup server"
    ),
    
    # BBS - CMS1
    Equipment(
        id=6,
        name="Router-2",
        status="online",
        last_checked=datetime.now(),
        data_rate=0.0,
        ligne="BBS",
        atelier="CMS1",
        type="router",
        location="Server Room",
        description="Secondary network router"
    ),
    Equipment(
        id=7,
        name="Switch-2",
        status="online",
        last_checked=datetime.now(),
        data_rate=0.0,
        ligne="BBS",
        atelier="CMS1",
        type="switch",
        location="Server Room",
        description="Secondary switch"
    ),
    
    # BBS - CMS2
    Equipment(
        id=8,
        name="Server-2",
        status="online",
        last_checked=datetime.now(),
        data_rate=0.0,
        ligne="BBS",
        atelier="CMS2",
        type="server",
        location="Server Room",
        description="Secondary application server"
    ),
    Equipment(
        id=9,
        name="Storage-2",
        status="online",
        last_checked=datetime.now(),
        data_rate=0.0,
        ligne="BBS",
        atelier="CMS2",
        type="storage",
        location="Server Room",
        description="Secondary storage array"
    ),
    
    # BBS - Intégration
    Equipment(
        id=10,
        name="Backup-2",
        status="online",
        last_checked=datetime.now(),
        data_rate=0.0,
        ligne="BBS",
        atelier="intégration",
        type="backup",
        location="Server Room",
        description="Secondary backup server"
    )
]

# Generate some historical data for each equipment
def generate_dummy_history(equipment: Equipment) -> EquipmentHistory:
    data = []
    for i in range(20):
        timestamp = datetime.now() - timedelta(minutes=i)
        data_rate = random.uniform(0, 100)
        status = "online" if data_rate < 80 else "warning"
        data.append(EquipmentData(
            timestamp=timestamp,
            data_rate=data_rate,
            status=status
        ))
    return EquipmentHistory(
        equipment_id=equipment.id,
        data=data
    )

# Create dummy history for all equipment
dummy_history = {
    eq.id: generate_dummy_history(eq) for eq in dummy_equipment
}
