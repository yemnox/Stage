from pysnmp.hlapi import *
import time
from datetime import datetime
import sys  

# Add the project root to the Python path
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Now import your application modules
try:
    from app.models.database_models import Equipment, EquipmentHistory
    from app.database import db_client
    print("Successfully imported database modules")
    print("Current working directory:", os.getcwd())
    print("Project root:", project_root)
except ImportError as e:
    print(f"Error importing modules: {e}")
    print("Current Python path:", sys.path)
    print("Current working directory:", os.getcwd())
    print("Project root:", project_root)
    print("Contents of project root:", os.listdir(project_root))
    sys.exit(1)


# SNMPv3 config
SNMP_USER = 'AdminUser'
AUTH_KEY = 'cisco12345'
PRIV_KEY = 'cisco54321'
TARGET_IP = '192.168.100.1'  # Your SNMP-enabled device IP
INTERFACE_INDEX = 1       # Interface index to monitor (change if needed)

# OID for ifHCInOctets (64-bit input counter for given interface)
OID_IN = f'1.3.6.1.2.1.31.1.1.1.6.{INTERFACE_INDEX}'

def get_snmp_value(oid):
    response = next(getCmd(
    SnmpEngine(),
    UsmUserData(SNMP_USER, AUTH_KEY, PRIV_KEY,
                authProtocol=usmHMACSHAAuthProtocol,
                privProtocol=usmDESPrivProtocol),
    UdpTransportTarget((TARGET_IP, 161), timeout=2, retries=1),
    ContextData(),
    ObjectType(ObjectIdentity(oid))
    ))
    errorIndication, errorStatus, errorIndex, varBinds = response


    if errorIndication:
        print(f"SNMP error: {errorIndication}")
        return None
    elif errorStatus:
        print(f"SNMP error: {errorStatus.prettyPrint()} at index {errorIndex}")
        return None
    else:
        for varBind in varBinds:
            return int(varBind[1])

def save_to_database(bit_rate, timestamp):
    """Save the data rate to MongoDB."""
    try:
        # Get or create equipment entry
        equipment = Equipment.get_by_ip(TARGET_IP)
        
        if not equipment:
            print(f"Equipment with IP {TARGET_IP} not found, creating new entry")
            equipment = Equipment(
                name=f"Network-Device-{TARGET_IP}",
                ip_address=TARGET_IP,
                ligne="default",
                atelier="network",
                description=f"Network device at {TARGET_IP}",
                equipment_type="network_device",
                status="online"
            )
            equipment.save()
        
        # Update equipment with current data rate
        equipment.data_rate = bit_rate
        equipment.response_time = 0  # You might want to measure this
        equipment.last_checked = datetime.utcnow()
        equipment.status = "online"
        equipment.save()
        
        # Save to history
        history = EquipmentHistory(
            equipment_id=equipment.id,
            timestamp=timestamp,
            status="online",
            data_rate=bit_rate,
            response_time=0  # You might want to measure this
        )
        history.save()
        
        return True
    except Exception as e:
        print(f"Error saving to database: {e}")
        return False




def main():
    print("Starting SNMP data rate monitor...")
    
    # Initial SNMP request
    last_value = get_snmp_value(OID_IN)
    if last_value is None:
        print("Initial SNMP request failed. Exiting.")
        return

    last_time = time.time()
    print("Monitoring started. Press Ctrl+C to stop...")

    try:
        while True:
            time.sleep(5)  # 5-second interval between measurements
            current_value = get_snmp_value(OID_IN)
            current_time = time.time()

            if current_value is not None:
                # Calculate bit rate
                delta_bits = (current_value - last_value) * 8  # Convert bytes to bits
                delta_time = current_time - last_time
                bit_rate = delta_bits / delta_time  # bits per second
                bit_rate_mbps = bit_rate / 1_000_000  # Convert to Mbps
                
                timestamp = datetime.utcnow()
                
                # Save to database
                if save_to_database(bit_rate_mbps, timestamp):
                    print(f"{timestamp.strftime('%Y-%m-%d %H:%M:%S')} - {bit_rate_mbps:.2f} Mbps")
                else:
                    print("Failed to save to database")
                
                # Update for next iteration
                last_value = current_value
                last_time = current_time
            else:
                print("Failed to retrieve SNMP data. Retrying...")
                
    except KeyboardInterrupt:
        print("\nMonitoring stopped by user")
    except Exception as e:
        print(f"Unexpected error: {e}")

if __name__ == "__main__":
    main()