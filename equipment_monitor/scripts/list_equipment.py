from app.database import db_client
from app.models.equipment import Equipment

def list_equipment():
    print("Listing all equipment:")
    for eq in Equipment.get_all():
        print(f"ID: {eq.id}, Name: {eq.name}, Status: {eq.status}")

if __name__ == "__main__":
    list_equipment()