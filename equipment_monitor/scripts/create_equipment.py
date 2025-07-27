# scripts/create_equipment.py
import sys
import os
from pathlib import Path

# Add the project root to the Python path
sys.path.append(str(Path(__file__).parent.parent))

from app.database import db_client
from app.models.equipment import Equipment

def main():
    # Example usage
    equipment = Equipment(
        name="Test Equipment",
        ip_address="192.168.1.100",
        ligne="Ligne 1",
        atelier="Atelier A"
    )
    equipment_id = equipment.save()
    print(f"Created equipment with ID: {equipment_id}")

if __name__ == "__main__":
    main()