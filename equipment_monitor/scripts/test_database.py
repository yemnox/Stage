# scripts/test_database.py
import sys
import os
from pathlib import Path

# Add the project root to the Python path
sys.path.append(str(Path(__file__).parent.parent))

from app.database import db_client, check_connection
from app.models.database_models import User, Equipment, SystemConfig

def test_database_connection():
    """Test basic database connection."""
    print("Testing database connection...")
    
    if db_client is None:
        print("✗ Database client not initialized")
        return False
    
    try:
        # Test connection
        health = db_client.health_check()
        if health["status"] == "healthy":
            print(f"✓ Database connection healthy (response time: {health['response_time_ms']}ms)")
            return True
        else:
            print(f"✗ Database connection unhealthy: {health.get('error', 'Unknown error')}")
            return False
    except Exception as e:
        print(f"✗ Database connection test failed: {e}")
        return False

def test_user_operations():
    """Test user CRUD operations."""
    print("\nTesting user operations...")
    
    try:
        # Create a test user
        test_user = User(
            name="Test User",
            username="testuser",
            email="test@example.com",
            password="testpass123",
            role="viewer"
        )
        
        user_id = test_user.save()
        print(f"✓ Created test user with ID: {user_id}")
        
        # Retrieve the user
        retrieved_user = User.get_by_id(user_id)
        if retrieved_user and retrieved_user.username == "testuser":
            print("✓ Successfully retrieved user by ID")
        else:
            print("✗ Failed to retrieve user by ID")
            return False
        
        # Test password verification
        if retrieved_user.verify_password("testpass123"):
            print("✓ Password verification successful")
        else:
            print("✗ Password verification failed")
            return False
        
        # Test permissions
        if retrieved_user.has_permission("VIEW_DASHBOARD"):
            print("✓ Permission check successful")
        else:
            print("✗ Permission check failed")
        
        # Clean up - delete test user
        if User.delete(user_id):
            print("✓ Test user deleted successfully")
        else:
            print("✗ Failed to delete test user")
            
        return True
        
    except Exception as e:
        print(f"✗ User operations test failed: {e}")
        return False

def test_equipment_operations():
    """Test equipment CRUD operations."""
    print("\nTesting equipment operations...")
    
    try:
        # Create test equipment
        test_equipment = Equipment(
            name="Test-Equipment-001",
            ip_address="192.168.99.99",
            ligne="test_ligne",
            atelier="test_atelier",
            description="Test equipment for database testing",
            equipment_type="test"
        )
        
        eq_id = test_equipment.save()
        print(f"✓ Created test equipment with ID: {eq_id}")
        
        # Retrieve the equipment
        retrieved_eq = Equipment.get_by_id(eq_id)
        if retrieved_eq and retrieved_eq.name == "Test-Equipment-001":
            print("✓ Successfully retrieved equipment by ID")
        else:
            print("✗ Failed to retrieve equipment by ID")
            return False
        
        # Test get by name
        eq_by_name = Equipment.get_by_name("Test-Equipment-001")
        if eq_by_name and eq_by_name.id == eq_id:
            print("✓ Successfully retrieved equipment by name")
        else:
            print("✗ Failed to retrieve equipment by name")
        
        # Update equipment status
        retrieved_eq.status = "online"
        retrieved_eq.data_rate = 85.5
        retrieved_eq.save()
        print("✓ Updated equipment status and data rate")
        
        # Clean up - delete test equipment
        if Equipment.delete(eq_id):
            print("✓ Test equipment deleted successfully")
        else:
            print("✗ Failed to delete test equipment")
            
        return True
        
    except Exception as e:
        print(f"✗ Equipment operations test failed: {e}")
        return False

def test_system_config():
    """Test system configuration operations."""
    print("\nTesting system configuration...")
    
    try:
        # Create test config
        test_config = SystemConfig(
            key="test_setting",
            value="test_value",
            description="Test configuration setting"
        )
        
        config_id = test_config.save()
        print(f"✓ Created test config with ID: {config_id}")
        
        # Retrieve config by key
        retrieved_config = SystemConfig.get_by_key("test_setting")
        if retrieved_config and retrieved_config.value == "test_value":
            print("✓ Successfully retrieved config by key")
        else:
            print("✗ Failed to retrieve config by key")
            return False
        
        # Update config value
        retrieved_config.value = "updated_value"
        retrieved_config.save()
        
        # Verify update
        updated_config = SystemConfig.get_by_key("test_setting")
        if updated_config and updated_config.value == "updated_value":
            print("✓ Successfully updated config value")
        else:
            print("✗ Failed to update config value")
        
        # Clean up
        SystemConfig.get_collection().delete_one({"key": "test_setting"})
        print("✓ Test config deleted successfully")
        
        return True
        
    except Exception as e:
        print(f"✗ System config test failed: {e}")
        return False

def test_database_stats():
    """Test database statistics."""
    print("\nTesting database statistics...")
    
    try:
        stats = db_client.get_database_stats()
        if stats:
            print(f"✓ Database: {stats.get('database', 'N/A')}")
            print(f"✓ Collections: {stats.get('collections', 0)}")
            print(f"✓ Objects: {stats.get('objects', 0)}")
            print(f"✓ Data size: {stats.get('data_size', 0)} bytes")
            return True
        else:
            print("✗ Failed to get database statistics")
            return False
    except Exception as e:
        print(f"✗ Database stats test failed: {e}")
        return False

def main():
    """Run all database tests."""
    print("=" * 60)
    print("Equipment Monitor Database Test Suite")
    print("=" * 60)
    
    tests = [
        ("Database Connection", test_database_connection),
        ("User Operations", test_user_operations),
        ("Equipment Operations", test_equipment_operations),
        ("System Configuration", test_system_config),
        ("Database Statistics", test_database_stats)
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            if test_func():
                passed += 1
                print(f"✓ {test_name} PASSED")
            else:
                failed += 1
                print(f"✗ {test_name} FAILED")
        except Exception as e:
            failed += 1
            print(f"✗ {test_name} FAILED with exception: {e}")
    
    print("\n" + "=" * 60)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("=" * 60)
    
    if failed == 0:
        print("🎉 All tests passed! Database is ready for use.")
        return True
    else:
        print("❌ Some tests failed. Please check the database setup.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)