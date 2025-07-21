from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta
import random

class User(BaseModel):
    id: int
    email: str
    name: str
    password: str
    created_at: datetime

class Equipment(BaseModel):
    id: int
    name: str
    status: str
    last_checked: datetime
    data_rate: float
    type: str
    location: str
    description: str

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
        password="admin123",
        created_at=datetime.now()
    ),
    "user@example.com": User(
        id=2,
        email="user@example.com",
        name="Jane Smith",
        password="user123",
        created_at=datetime.now()
    )
}

# Create dummy equipment
dummy_equipment = [
    Equipment(
        id=1,
        name="Router-1",
        status="online",
        last_checked=datetime.now(),
        data_rate=0.0,
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
        type="switch",
        location="Server Room",
        description="Main network switch"
    ),
    Equipment(
        id=3,
        name="Firewall-1",
        status="warning",
        last_checked=datetime.now(),
        data_rate=0.0,
        type="firewall",
        location="Perimeter",
        description="Perimeter firewall"
    ),
    Equipment(
        id=4,
        name="Storage-1",
        status="online",
        last_checked=datetime.now(),
        data_rate=0.0,
        type="storage",
        location="Storage Room",
        description="Primary storage server"
    ),
    Equipment(
        id=5,
        name="Backup-1",
        status="warning",
        last_checked=datetime.now(),
        data_rate=0.0,
        type="backup",
        location="Storage Room",
        description="Backup server"
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
