# scripts/init_database.py
import sys
import os
from pathlib import Path
from datetime import datetime

# Add the project root to the Python path
sys.path.append(str(Path(__file__).parent.parent))

from app.database import db_client
from app.models.database_models import User, Equipment, SystemConfig, Alert, EquipmentHistory

def create_indexes():
    """Create database indexes for better performance."""
    print("Creating database indexes...")
    
    # Users collection indexes
    db_client.db.users.create_index("username", unique=True)
    db_client.db.users.create_index("email", unique=True, sparse=True)
    db_client.db.users.create_index([("username", 1), ("domain", 1)])
    
    # Equipment collection indexes
    db_client.db.equipment.create_index("name", unique=True)
    db_client.db.equipment.create_index("ip_address", unique=True)
    db_client.db.equipment.create_index([("ligne", 1), ("atelier", 1)])
    db_client.db.equipment.create_index("status")
    db_client.db.equipment.create_index("is_active")
    
    # Equipment history indexes
    db_client.db.equipment_history.create_index([("equipment_id", 1), ("timestamp", -1)])
    db_client.db.equipment_history.create_index("timestamp")
    
    # Alerts indexes
    db_client.db.alerts.create_index([("equipment_id", 1), ("timestamp", -1)])
    db_client.db.alerts.create_index("resolved")
    db_client.db.alerts.create_index("severity")
    db_client.db.alerts.create_index("timestamp")
    
    # System config indexes
    db_client.db.system_config.create_index("key", unique=True)
    
    print("✓ Database indexes created successfully")

def create_default_users():
    """Create default users."""
    print("Creating default users...")
    
    default_users = [
        {
            "name": "System Administrator",
            "username": "admin",
            "email": "admin@company.com",
            "password": "admin123",
            "role": "admin",
            "domain": "DESKTOP-YEMNOX"
        },
        {
            "name": "Production Manager",
            "username": "manager",
            "email": "manager@company.com",
            "password": "manager123",
            "role": "manager"
        },
        {
            "name": "Operator User",
            "username": "operator",
            "email": "operator@company.com",
            "password": "operator123",
            "role": "operator"
        },
        {
            "name": "Viewer User",
            "username": "viewer",
            "email": "viewer@company.com",
            "password": "viewer123",
            "role": "viewer"
        }
    ]
    
    for user_data in default_users:
        # Check if user already exists
        existing_user = User.get_by_username(user_data["username"])
        if not existing_user:
            user = User(
                name=user_data["name"],
                username=user_data["username"],
                email=user_data["email"],
                password=user_data["password"],
                role=user_data["role"],
                domain=user_data.get("domain")
            )
            user_id = user.save()
            print(f"✓ Created user: {user_data['username']} ({user_data['role']})")
        else:
            print(f"- User {user_data['username']} already exists")

def create_demo_equipment():
    """Create demo equipment for testing."""
    print("Creating demo equipment...")
    
    demo_equipment = [
        {
            "name": "Router-Main-001",
            "ip_address": "192.168.1.1",
            "ligne": "ligne1",
            "atelier": "atelier_a",
            "description": "Main network router for Ligne 1",
            "equipment_type": "router",
            "location": "Server Room A"
        },
        {
            "name": "Switch-L1A-001",
            "ip_address": "192.168.1.10",
            "ligne": "ligne1",
            "atelier": "atelier_a",
            "description": "Main switch for Atelier A",
            "equipment_type": "switch",
            "location": "Atelier A - Rack 1"
        },
        {
            "name": "Switch-L1B-001",
            "ip_address": "192.168.1.20",
            "ligne": "ligne1",
            "atelier": "atelier_b",
            "description": "Main switch for Atelier B",
            "equipment_type": "switch",
            "location": "Atelier B - Rack 1"
        },
        {
            "name": "Router-L2-001",
            "ip_address": "192.168.2.1",
            "ligne": "ligne2",
            "atelier": "atelier_c",
            "description": "Router for Ligne 2",
            "equipment_type": "router",
            "location": "Server Room B"
        },
        {
            "name": "Switch-L2C-001",
            "ip_address": "192.168.2.10",
            "ligne": "ligne2",
            "atelier": "atelier_c",
            "description": "Switch for Atelier C",
            "equipment_type": "switch",
            "location": "Atelier C - Rack 1"
        },
        {
            "name": "Switch-L2D-001",
            "ip_address": "192.168.2.20",
            "ligne": "ligne2",
            "atelier": "atelier_d",
            "description": "Switch for Atelier D",
            "equipment_type": "switch",
            "location": "Atelier D - Rack 1"
        },
        {
            "name": "Server-DB-001",
            "ip_address": "192.168.1.100",
            "ligne": "ligne1",
            "atelier": "atelier_a",
            "description": "Database server",
            "equipment_type": "server",
            "location": "Server Room A"
        },
        {
            "name": "Workstation-001",
            "ip_address": "192.168.1.200",
            "ligne": "ligne1",
            "atelier": "atelier_a",
            "description": "Operator workstation",
            "equipment_type": "workstation",
            "location": "Atelier A - Desk 1"
        }
    ]
    
    for eq_data in demo_equipment:
        # Check if equipment already exists
        existing_eq = Equipment.get_by_name(eq_data["name"])
        if not existing_eq:
            equipment = Equipment(
                name=eq_data["name"],
                ip_address=eq_data["ip_address"],
                ligne=eq_data["ligne"],
                atelier=eq_data["atelier"],
                description=eq_data["description"],
                equipment_type=eq_data["equipment_type"],
                location=eq_data["location"]
            )
            eq_id = equipment.save()
            print(f"✓ Created equipment: {eq_data['name']}")
        else:
            print(f"- Equipment {eq_data['name']} already exists")

def create_system_config():
    """Create default system configuration."""
    print("Creating system configuration...")
    
    default_configs = [
        {
            "key": "monitoring_interval",
            "value": 5,
            "description": "Monitoring interval in seconds"
        },
        {
            "key": "ping_timeout",
            "value": 5,
            "description": "Ping timeout in seconds"
        },
        {
            "key": "ping_count",
            "value": 4,
            "description": "Number of ping packets to send"
        },
        {
            "key": "snmp_community",
            "value": "public",
            "description": "SNMP community string"
        },
        {
            "key": "snmp_port",
            "value": 161,
            "description": "SNMP port number"
        },
        {
            "key": "snmp_timeout",
            "value": 2,
            "description": "SNMP timeout in seconds"
        },
        {
            "key": "alert_email_enabled",
            "value": False,
            "description": "Enable email alerts"
        },
        {
            "key": "alert_email_recipients",
            "value": ["admin@company.com"],
            "description": "Email recipients for alerts"
        },
        {
            "key": "history_retention_days",
            "value": 30,
            "description": "Number of days to keep history data"
        },
        {
            "key": "dashboard_refresh_interval",
            "value": 5,
            "description": "Dashboard refresh interval in seconds"
        },
        {
            "key": "data_rate_threshold_warning",
            "value": 80.0,
            "description": "Data rate threshold for warnings (percentage)"
        },
        {
            "key": "data_rate_threshold_critical",
            "value": 95.0,
            "description": "Data rate threshold for critical alerts (percentage)"
        },
        {
            "key": "response_time_threshold_warning",
            "value": 100.0,
            "description": "Response time threshold for warnings (ms)"
        },
        {
            "key": "response_time_threshold_critical",
            "value": 500.0,
            "description": "Response time threshold for critical alerts (ms)"
        },
        {
            "key": "packet_loss_threshold_warning",
            "value": 5.0,
            "description": "Packet loss threshold for warnings (percentage)"
        },
        {
            "key": "packet_loss_threshold_critical",
            "value": 20.0,
            "description": "Packet loss threshold for critical alerts (percentage)"
        }
    ]
    
    for config_data in default_configs:
        config = SystemConfig(
            key=config_data["key"],
            value=config_data["value"],
            description=config_data["description"],
            updated_by="system"
        )
        config.save()
        print(f"✓ Created config: {config_data['key']}")

def create_collections():
    """Ensure all collections exist."""
    print("Creating collections...")
    
    collections = [
        "users",
        "equipment", 
        "equipment_history",
        "alerts",
        "system_config"
    ]
    
    existing_collections = db_client.db.list_collection_names()
    
    for collection_name in collections:
        if collection_name not in existing_collections:
            db_client.db.create_collection(collection_name)
            print(f"✓ Created collection: {collection_name}")
        else:
            print(f"- Collection {collection_name} already exists")

def verify_database_connection():
    """Verify database connection."""
    try:
        # Test the connection
        db_client.client.admin.command('ping')
        print("✓ Database connection successful")
        
        # Get database info
        db_info = db_client.client.server_info()
        print(f"✓ MongoDB version: {db_info['version']}")
        print(f"✓ Database name: {db_client.db_name}")
        
        # List existing collections
        collections = db_client.db.list_collection_names()
        print(f"✓ Existing collections: {collections}")
        
        return True
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        return False

def cleanup_old_data():
    """Clean up old historical data."""
    print("Cleaning up old data...")
    
    try:
        # Clean up old equipment history (older than 30 days)
        deleted_count = EquipmentHistory.cleanup_old_records(30)
        print(f"✓ Cleaned up {deleted_count} old history records")
        
        # You can add more cleanup operations here
        return True
    except Exception as e:
        print(f"✗ Cleanup failed: {e}")
        return False

def main():
    """Main initialization function."""
    print("=" * 50)
    print("Equipment Monitor Database Initialization")
    print("=" * 50)
    
    # Step 1: Verify database connection
    if not verify_database_connection():
        print("Initialization failed - could not connect to database")
        return False
    
    print("\n" + "-" * 30)
    
    try:
        # Step 2: Create collections
        create_collections()
        
        print("\n" + "-" * 30)
        
        # Step 3: Create indexes
        create_indexes()
        
        print("\n" + "-" * 30)
        
        # Step 4: Create default users
        create_default_users()
        
        print("\n" + "-" * 30)
        
        # Step 5: Create demo equipment
        create_demo_equipment()
        
        print("\n" + "-" * 30)
        
        # Step 6: Create system configuration
        create_system_config()
        
        print("\n" + "-" * 30)
        
        # Step 7: Cleanup old data
        cleanup_old_data()
        
        print("\n" + "=" * 50)
        print("✓ Database initialization completed successfully!")
        print("=" * 50)
        
        # Print summary
        users_count = len(User.get_all())
        equipment_count = len(Equipment.get_all())
        configs_count = len(SystemConfig.get_all())
        
        print(f"\nSummary:")
        print(f"- Users: {users_count}")
        print(f"- Equipment: {equipment_count}")
        print(f"- System configs: {configs_count}")
        
        print(f"\nDefault login credentials:")
        print(f"- Admin: admin / admin123")
        print(f"- Manager: manager / manager123")
        print(f"- Operator: operator / operator123")
        print(f"- Viewer: viewer / viewer123")
        
        return True
        
    except Exception as e:
        print(f"\n✗ Initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    main()