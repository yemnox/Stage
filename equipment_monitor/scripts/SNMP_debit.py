#!/usr/bin/env python3
"""
SNMP Data Rate Monitor Script
Monitors network device data rates via SNMP and stores in MongoDB
"""

import sys
import os
import time
from pathlib import Path
from datetime import datetime
from pysnmp.hlapi import *

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Now import your application modules
try:
    from app.models.database_models import Equipment, EquipmentHistory
    from app.database import db_client
    print("Successfully imported database modules")
    print(f"Current working directory: {os.getcwd()}")
    print(f"Project root: {project_root}")
except ImportError as e:
    print(f"Error importing modules: {e}")
    print(f"Current Python path: {sys.path}")
    print(f"Current working directory: {os.getcwd()}")
    print(f"Project root: {project_root}")
    if project_root.exists():
        print(f"Contents of project root: {list(project_root.iterdir())}")
    sys.exit(1)

# SNMPv3 config
SNMP_USER = 'AdminUser'
AUTH_KEY = 'cisco12345'
PRIV_KEY = 'cisco54321'
TARGET_IP = '192.168.100.1'  # Your SNMP-enabled device IP
INTERFACE_INDEX = 1       # Interface index to monitor (change if needed)
SNMP_PORT = 161
# OID for ifHCInOctets (64-bit input counter for given interface)
OID_IN = f'1.3.6.1.2.1.31.1.1.1.6.{INTERFACE_INDEX}'


# SNMP Configuration
class SNMPConfig:
    def __init__(self):
        self.SNMP_USER = 'AdminUser'
        self.AUTH_KEY = 'cisco12345'
        self.PRIV_KEY = 'cisco54321'
        self.COMMUNITY = 'public'
        self.TARGET_IP = '192.168.100.1'
        self.INTERFACE_INDEX = 1
        self.SNMP_PORT = 161
        self.TIMEOUT = 5
        self.RETRIES = 2

        # OIDs
        self.OID_IN_OCTETS = f'1.3.6.1.2.1.31.1.1.1.6.{self.INTERFACE_INDEX}'   # ifHCInOctets
        self.OID_OUT_OCTETS = f'1.3.6.1.2.1.31.1.1.1.10.{self.INTERFACE_INDEX}' # ifHCOutOctets
        self.OID_INTERFACE_SPEED = f'1.3.6.1.2.1.2.2.1.5.{self.INTERFACE_INDEX}' 
        self.OID_INTERFACE_NAME = f'1.3.6.1.2.1.2.2.1.2.{self.INTERFACE_INDEX}'
        self.OID_SYS_UPTIME = '1.3.6.1.2.1.1.3.0' 



class SNMPMonitor:
    def __init__(self, config):
        self.config = config
        self.previous_in_octets = None
        self.previous_out_octets = None
        self.previous_timestamp = None
        self.device_info = None
        self.last_in_octets = None
        self.last_out_octets = None
        self.last_time = None
        
    def get_snmp_value_v3(self, oid):
        """Get SNMP value using SNMPv3."""
        try:
            response = next(getCmd(
                SnmpEngine(),
                UsmUserData(
                    self.config.SNMP_USER, 
                    self.config.AUTH_KEY, 
                    self.config.PRIV_KEY,
                    authProtocol=usmHMACSHAAuthProtocol,
                    privProtocol=usmDESPrivProtocol
                ),
                UdpTransportTarget((self.config.TARGET_IP, self.config.SNMP_PORT), 
                                 timeout=5, 
                                 retries=2),
                ContextData(),
                ObjectType(ObjectIdentity(oid))
            ))
            
            errorIndication, errorStatus, errorIndex, varBinds = response
            
            if errorIndication:
                print(f"SNMP v3 error indication: {errorIndication}")
                return None
            elif errorStatus:
                print(f"SNMP v3 error status: {errorStatus.prettyPrint()} at index {errorIndex}")
                return None
            else:
                for varBind in varBinds:
                    return str(varBind[1])
                    
        except Exception as e:
            print(f"SNMPv3 error for OID {oid}: {e}")
            return None
    
    def get_snmp_value_v2c(self, oid):
        """Get SNMP value using SNMPv2c (fallback)."""
        try:
            response = next(getCmd(
                SnmpEngine(),
                CommunityData('public'),
                UdpTransportTarget((self.config.TARGET_IP, self.config.SNMP_PORT), 
                                 timeout=5, 
                                 retries=2),
                ContextData(),
                ObjectType(ObjectIdentity(oid))
            ))
            
            errorIndication, errorStatus, errorIndex, varBinds = response
            
            if errorIndication:
                print(f"SNMP v2c error indication: {errorIndication}")
                return None
            elif errorStatus:
                print(f"SNMP v2c error status: {errorStatus.prettyPrint()} at index {errorIndex}")
                return None
            else:
                for varBind in varBinds:
                    return str(varBind[1])
                    
        except Exception as e:
            print(f"SNMPv2c error for OID {oid}: {e}")
            return None
    
    def get_snmp_value(self, oid):
        """Get SNMP value, trying v3 first, then v2c."""
        # Try SNMPv3 first
        value = self.get_snmp_value_v3(oid)
        if value is not None:
            return value
            
        # Fallback to SNMPv2c1.3.6.1.2.1.31.1.1.1.6.
        print("SNMPv3 failed, trying SNMPv2c...")
        return self.get_snmp_value_v2c(oid)
    
    def get_device_info(self):
        """Get basic device information."""
        if self.device_info is None:
            interface_name = self.get_snmp_value(f'1.3.6.1.2.1.2.2.1.2.{self.config.INTERFACE_INDEX}')
            interface_speed = self.get_snmp_value(f'1.3.6.1.2.1.2.2.1.5.{self.config.INTERFACE_INDEX}')
            
            self.device_info = {
                'interface_name': interface_name or f"Interface-{self.config.INTERFACE_INDEX}",
                'interface_speed': int(interface_speed) if interface_speed and interface_speed.isdigit() else 0
            }
        
        return self.device_info
    
    def calculate_data_rate(self):
        try:
            current_in = int(self.get_snmp_value(f'1.3.6.1.2.1.31.1.1.1.6.{self.config.INTERFACE_INDEX}'))
            current_out = int(self.get_snmp_value(f'1.3.6.1.2.1.31.1.1.1.10.{self.config.INTERFACE_INDEX}'))
            current_time = time.time()

            if None in (current_in, current_out):
                raise ValueError("Failed to retrieve SNMP data.")

            if any(v is None for v in [self.last_in_octets, self.last_out_octets, self.last_time]):
                self.last_in_octets = current_in
                self.last_out_octets = current_out
                self.last_time = current_time
                return None

            delta_in_octets = current_in - self.last_in_octets
            delta_out_octets = current_out - self.last_out_octets
            delta_time = current_time - self.last_time

            if delta_time == 0:
                raise ValueError("Delta time is zero, cannot calculate rate.")

            # Handle counter rollover
            if delta_in_octets < 0:
                delta_in_octets += 2**64
            if delta_out_octets < 0:
                delta_out_octets += 2**64

            in_bps = (delta_in_octets * 8) / delta_time
            out_bps = (delta_out_octets * 8) / delta_time
            total_bps = in_bps + out_bps

            self.last_in_octets = current_in
            self.last_out_octets = current_out
            self.last_time = current_time

            return in_bps / 1_000_000, out_bps / 1_000_000, total_bps / 1_000_000

        except Exception as e:
            print(f"[!] Error calculating data rate: {e}")
            return None
    
    def debug_print_state(self):
        print("==== SNMP Monitor State ====")
        #print(f"Device IP:         {self.config.ip}")
        #print(f"Community:         {self.config.community}")
        #print(f"Port:              {self.config.port}")
        print(f"OID_IF_IN_OCTETS:  {self.config.OID_IN_OCTETS}")
        print(f"OID_IF_OUT_OCTETS: {self.config.OID_OUT_OCTETS}")
        print(f"Last In Octets:    {self.last_in_octets}")
        print(f"Last Out Octets:   {self.last_out_octets}")
        print(f"Last Timestamp:    {self.last_time}")
        print("============================\n")


class DatabaseManager:
    def __init__(self, target_ip):
        self.target_ip = target_ip
        self.equipment = None
        self._ensure_equipment_exists()
    
    def _ensure_equipment_exists(self):
        """Ensure equipment entry exists in database."""
        try:
            # Try to find existing equipment by IP
            self.equipment = Equipment.get_by_ip(self.target_ip)
            
            if not self.equipment:
                print(f"Equipment with IP {self.target_ip} not found, creating new entry")
                
                # Create new equipment entry
                self.equipment = Equipment(
                    name=f"Network-Device-{self.target_ip}",
                    ip_address=self.target_ip,
                    ligne="default",
                    atelier="network",
                    description=f"SNMP monitored device at {self.target_ip}",
                    equipment_type="network_device",
                    status="unknown"
                )
                equipment_id = self.equipment.save()
                print(f"Created equipment entry with ID: {equipment_id}")
            else:
                print(f"Found existing equipment: {self.equipment.name} (ID: {self.equipment.id})")
                
        except Exception as e:
            print(f"Error ensuring equipment exists: {e}")
            raise
    
    def save_data_rate(self, data_rate_info, device_info=None):
        """Save data rate information to database."""
        try:
            if not self.equipment:
                print("No equipment entry available")
                return False
            
            # Update equipment with current data
            self.equipment.data_rate = data_rate_info['total_mbps']
            self.equipment.response_time = 0  # SNMP response time could be measured separately
            self.equipment.last_checked = data_rate_info['timestamp']
            self.equipment.status = "online"
            
            # Add device info if available
            if device_info:
                if not self.equipment.description or "SNMP monitored" in self.equipment.description:
                    self.equipment.description = f"SNMP device: {device_info.get('interface_name', 'Unknown')}"
            
            # Save equipment updates
            self.equipment.save()
            
            # Create history entry
            history = EquipmentHistory(
                equipment_id=self.equipment.id,
                timestamp=data_rate_info['timestamp'],
                status="online",
                data_rate=data_rate_info['total_mbps'],
                response_time=0,
                snmp_data={
                    'in_mbps': data_rate_info['in_mbps'],
                    'out_mbps': data_rate_info['out_mbps'],
                    'total_mbps': data_rate_info['total_mbps'],
                    'interface_info': device_info or {}
                }
            )
            history.save()
            
            return True
            
        except Exception as e:
            print(f"Error saving to database: {e}")
            return False
    
    def save_error_status(self, error_message):
        """Save error status when SNMP fails."""
        try:
            if not self.equipment:
                return False
            
            self.equipment.status = "offline"
            self.equipment.data_rate = 0.0
            self.equipment.last_checked = datetime.utcnow()
            self.equipment.save()
            
            # Create history entry for the error
            history = EquipmentHistory(
                equipment_id=self.equipment.id,
                timestamp=datetime.utcnow(),
                status="offline",
                data_rate=0.0,
                snmp_data={'error': error_message}
            )
            history.save()
            
            return True
            
        except Exception as e:
            print(f"Error saving error status: {e}")
            return False


"""
def main():
    #Main monitoring function.
    print("Starting SNMP Data Rate Monitor...")
    print("=" * 50)
    
    # Initialize configuration
    config = SNMPConfig()
    print(f"Target device: {config.TARGET_IP}")
    print(f"Interface index: {config.INTERFACE_INDEX}")
    print(f"SNMP timeout: {config.TIMEOUT} seconds")
    
    # Initialize monitor and database manager
    monitor = SNMPMonitor(config)
    db_manager = DatabaseManager(config.TARGET_IP)
    
    # Get device information
    print("\nGetting device information...")
    device_info = monitor.get_device_info()
    print(f"Interface: {device_info['interface_name']}")
    print(f"Interface speed: {device_info['interface_speed']} bps")
    
    # Initialize monitoring
    print("\nInitializing monitoring (first measurement)...")
    initial_result = monitor.calculate_data_rate()
    if initial_result is None:
        print("Initial measurement taken. Starting monitoring loop...")
    else:
        print("Warning: Got data on first measurement (unexpected)")
    
    print("\nMonitoring started. Press Ctrl+C to stop...")
    print("-" * 50)
    
    consecutive_errors = 0
    max_consecutive_errors = 5
    
    try:
        while True:
            time.sleep(10)  # 10-second interval between measurements
            
            # Calculate current data rate
            data_rate_info = monitor.calculate_data_rate()
            
            if data_rate_info:
                # Save to database
                if db_manager.save_data_rate(data_rate_info, device_info):
                    timestamp_str = data_rate_info['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
                    print(f"{timestamp_str} | "
                          f"IN: {data_rate_info['in_mbps']:.2f} Mbps | "
                          f"OUT: {data_rate_info['out_mbps']:.2f} Mbps | "
                          f"TOTAL: {data_rate_info['total_mbps']:.2f} Mbps")
                    consecutive_errors = 0
                else:
                    print("Failed to save to database")
                    consecutive_errors += 1
            else:
                print("Failed to retrieve SNMP data")
                db_manager.save_error_status("SNMP data retrieval failed")
                consecutive_errors += 1
            
            # Check for too many consecutive errors
            if consecutive_errors >= max_consecutive_errors:
                print(f"\nToo many consecutive errors ({consecutive_errors}). Stopping monitoring.")
                break
                
    except KeyboardInterrupt:
        print("\n\nMonitoring stopped by user")
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("Monitoring session ended")
"""

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

    # Properly instantiate SNMPConfig
    snmp_config = SNMPConfig()

    # Create an instance of SNMPMonitor with config
    monitor = SNMPMonitor(snmp_config)

    print("Monitoring started. Press Ctrl+C to stop...")

    try:
        while True:
            time.sleep(10)  # 10-second interval

            result = monitor.calculate_data_rate()
            monitor.debug_print_state()
            if result is None:
                print("Data rate calculation returned None. Retrying...")
                continue

            in_bps_mbps, out_bps_mbps, total_bps_mbps = result
            timestamp = datetime.utcnow()

            if save_to_database(total_bps_mbps, timestamp):
                print(f"{timestamp.strftime('%Y-%m-%d %H:%M:%S')} - IN: {in_bps_mbps:.2f} Mbps | OUT: {out_bps_mbps:.2f} Mbps | TOTAL: {total_bps_mbps:.2f} Mbps")
            else:
                print("Failed to save to database")

    except KeyboardInterrupt:
        print("\nMonitoring stopped by user")
    except Exception as e:
        print(f"Unexpected error: {e}")



if __name__ == "__main__":
    try:
        if db_client is None:
            print("Error: Database client not initialized")
            print("Make sure MongoDB is running and accessible")
            sys.exit(1)
        
        # Test database connection
        health = db_client.health_check()
        if health["status"] != "healthy":
            print(f"Error: Database not healthy - {health.get('error', 'Unknown error')}")
            sys.exit(1)
        
        print(f"Database connection healthy (response time: {health['response_time_ms']}ms)")
        
    except Exception as e:
        print(f"Error checking database: {e}")
        sys.exit(1)
    main()