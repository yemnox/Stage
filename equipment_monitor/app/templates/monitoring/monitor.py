# app/templates/monitoring/monitor.py
import asyncio
import subprocess
import time
import socket
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging
from dataclasses import dataclass
from pysnmp.hlapi import *
import threading
import queue
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class DeviceStatus:
    name: str
    ip_address: str
    status: str  # 'online', 'offline', 'timeout'
    response_time: Optional[float] = None
    packet_loss: Optional[float] = None
    snmp_data: Optional[Dict] = None
    last_checked: Optional[datetime] = None
    data_rate: Optional[float] = None
    ligne: Optional[str] = None
    atelier: Optional[str] = None

class NetworkMonitor:
    def __init__(self):
        self.devices: Dict[str, DeviceStatus] = {}
        self.is_running = False
        self.monitor_thread = None
        self.status_history: Dict[str, List[Dict]] = {}
        self.alert_callbacks = []
        
        # SNMP Configuration
        self.snmp_community = 'public'
        self.snmp_port = 161
        self.snmp_timeout = 2
        self.snmp_retries = 1
        
        # Monitoring Configuration
        self.ping_timeout = 5
        self.ping_count = 4
        self.monitor_interval = 5  # seconds
        
    def add_device(self, name: str, ip_address: str, ligne: str = None, atelier: str = None):
        """Add a device to monitor."""
        self.devices[name] = DeviceStatus(
            name=name,
            ip_address=ip_address,
            status='unknown',
            ligne=ligne,
            atelier=atelier
        )
        self.status_history[name] = []
        logger.info(f"Added device {name} ({ip_address}) to monitoring")
    
    def remove_device(self, name: str):
        """Remove a device from monitoring."""
        if name in self.devices:
            del self.devices[name]
            if name in self.status_history:
                del self.status_history[name]
            logger.info(f"Removed device {name} from monitoring")
    
    def ping_device(self, ip_address: str) -> Dict[str, Any]:
        """Ping a device using ICMP and return response time and packet loss."""
        try:
            import platform
            system = platform.system().lower()
            
            if system == "windows":
                cmd = ["ping", "-n", str(self.ping_count), ip_address]
            else:
                cmd = ["ping", "-c", str(self.ping_count), ip_address]
            
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=self.ping_timeout + 5
            )
            
            if result.returncode == 0:
                # Parse ping output
                output = result.stdout
                
                # Extract response time (simplified parsing)
                times = []
                if system == "windows":
                    import re
                    time_matches = re.findall(r'time[<=](\d+)ms', output)
                    times = [float(t) for t in time_matches]
                else:
                    import re
                    time_matches = re.findall(r'time=(\d+\.?\d*)ms', output)
                    times = [float(t) for t in time_matches]
                
                avg_time = sum(times) / len(times) if times else None
                packet_loss = ((self.ping_count - len(times)) / self.ping_count) * 100
                
                return {
                    'status': 'online' if packet_loss < 100 else 'timeout',
                    'response_time': avg_time,
                    'packet_loss': packet_loss
                }
            else:
                return {
                    'status': 'offline',
                    'response_time': None,
                    'packet_loss': 100.0
                }
                
        except subprocess.TimeoutExpired:
            logger.warning(f"Ping timeout for {ip_address}")
            return {
                'status': 'timeout',
                'response_time': None,
                'packet_loss': 100.0
            }
        except Exception as e:
            logger.error(f"Error pinging {ip_address}: {e}")
            return {
                'status': 'error',
                'response_time': None,
                'packet_loss': 100.0
            }
    
    def get_snmp_data(self, ip_address: str) -> Dict[str, Any]:
        """Get SNMP data from a device."""
        snmp_data = {}
        
        try:
            # Standard SNMP OIDs
            oids = {
                'sysDescr': '1.3.6.1.2.1.1.1.0',
                'sysUpTime': '1.3.6.1.2.1.1.3.0',
                'ifInOctets': '1.3.6.1.2.1.2.2.1.10.1',  # Interface 1 input octets
                'ifOutOctets': '1.3.6.1.2.1.2.2.1.16.1', # Interface 1 output octets
                'ifSpeed': '1.3.6.1.2.1.2.2.1.5.1',      # Interface 1 speed
            }
            
            for name, oid in oids.items():
                try:
                    for (errorIndication, errorStatus, errorIndex, varBinds) in nextCmd(
                        SnmpEngine(),
                        CommunityData(self.snmp_community),
                        UdpTransportTarget((ip_address, self.snmp_port), timeout=self.snmp_timeout, retries=self.snmp_retries),
                        ContextData(),
                        ObjectType(ObjectIdentity(oid)),
                        lexicographicMode=False,
                        maxRows=1):
                        
                        if errorIndication:
                            logger.debug(f"SNMP error indication for {ip_address} {name}: {errorIndication}")
                            break
                        elif errorStatus:
                            logger.debug(f"SNMP error status for {ip_address} {name}: {errorStatus.prettyPrint()}")
                            break
                        else:
                            for varBind in varBinds:
                                snmp_data[name] = str(varBind[1])
                            break
                except Exception as e:
                    logger.debug(f"SNMP error for {ip_address} {name}: {e}")
                    continue
            
            # Calculate data rate if we have the necessary data
            if 'ifInOctets' in snmp_data and 'ifOutOctets' in snmp_data:
                try:
                    in_octets = int(snmp_data['ifInOctets'])
                    out_octets = int(snmp_data['ifOutOctets'])
                    # This is a simplified calculation - in practice you'd need to track changes over time
                    total_octets = in_octets + out_octets
                    # Convert to Mbps (simplified - this should be calculated based on time difference)
                    data_rate = (total_octets * 8) / (1024 * 1024)  # Convert to Mbps
                    snmp_data['calculated_data_rate'] = min(data_rate, 100)  # Cap at 100 Mbps for demo
                except:
                    snmp_data['calculated_data_rate'] = 0
                    
        except Exception as e:
            logger.debug(f"SNMP collection failed for {ip_address}: {e}")
        
        return snmp_data
    
    def check_device(self, device: DeviceStatus) -> DeviceStatus:
        """Check a single device status using ICMP and SNMP."""
        logger.debug(f"Checking device {device.name} ({device.ip_address})")
        
        # Store previous status for comparison
        previous_status = device.status
        
        # Ping the device
        ping_result = self.ping_device(device.ip_address)
        device.status = ping_result['status']
        device.response_time = ping_result['response_time']
        device.packet_loss = ping_result['packet_loss']
        device.last_checked = datetime.now()
        
        # If device is online, try to get SNMP data
        if device.status == 'online':
            snmp_data = self.get_snmp_data(device.ip_address)
            device.snmp_data = snmp_data
            
            # Set data rate from SNMP or simulate it
            if 'calculated_data_rate' in snmp_data:
                device.data_rate = float(snmp_data['calculated_data_rate'])
            else:
                # Simulate data rate for demo purposes
                import random
                device.data_rate = round(random.uniform(10, 95), 2)
        else:
            device.data_rate = 0.0
            device.snmp_data = None
        
        # Store status history
        if device.name in self.status_history:
            history_entry = {
                'timestamp': device.last_checked.isoformat(),
                'status': device.status,
                'response_time': device.response_time,
                'data_rate': device.data_rate,
                'packet_loss': device.packet_loss
            }
            self.status_history[device.name].append(history_entry)
            
            # Keep only last 50 entries
            if len(self.status_history[device.name]) > 50:
                self.status_history[device.name] = self.status_history[device.name][-50:]
        
        # Trigger alerts if status changed
        if previous_status != device.status and previous_status != 'unknown':
            self.trigger_alert(device, previous_status, device.status)
        
        logger.debug(f"Device {device.name} status: {device.status}, response_time: {device.response_time}ms")
        return device
    
    def trigger_alert(self, device: DeviceStatus, old_status: str, new_status: str):
        """Trigger an alert when device status changes."""
        alert_data = {
            'device_name': device.name,
            'ip_address': device.ip_address,
            'old_status': old_status,
            'new_status': new_status,
            'timestamp': datetime.now().isoformat(),
            'ligne': device.ligne,
            'atelier': device.atelier
        }
        
        logger.info(f"ALERT: Device {device.name} status changed from {old_status} to {new_status}")
        
        # Call registered alert callbacks
        for callback in self.alert_callbacks:
            try:
                callback(alert_data)
            except Exception as e:
                logger.error(f"Error in alert callback: {e}")
    
    def add_alert_callback(self, callback):
        """Add a callback function to be called when alerts are triggered."""
        self.alert_callbacks.append(callback)
    
    def monitor_loop(self):
        """Main monitoring loop."""
        logger.info("Starting monitoring loop")
        
        while self.is_running:
            try:
                start_time = time.time()
                
                # Check all devices
                for device_name, device in self.devices.items():
                    if not self.is_running:
                        break
                    self.check_device(device)
                
                # Calculate sleep time to maintain consistent interval
                elapsed_time = time.time() - start_time
                sleep_time = max(0, self.monitor_interval - elapsed_time)
                
                if self.is_running:
                    time.sleep(sleep_time)
                    
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                if self.is_running:
                    time.sleep(self.monitor_interval)
    
    def start_monitoring(self):
        """Start the monitoring thread."""
        if self.is_running:
            logger.warning("Monitoring already running")
            return
        
        self.is_running = True
        self.monitor_thread = threading.Thread(target=self.monitor_loop, daemon=True)
        self.monitor_thread.start()
        logger.info("Monitoring started")
    
    def stop_monitoring(self):
        """Stop the monitoring thread."""
        if not self.is_running:
            return
        
        self.is_running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=10)
        logger.info("Monitoring stopped")
    
    def get_status(self) -> List[Dict[str, Any]]:
        """Get current status of all devices."""
        status_list = []
        for device in self.devices.values():
            status_list.append({
                'name': device.name,
                'ip_address': device.ip_address,
                'status': device.status,
                'response_time': device.response_time,
                'packet_loss': device.packet_loss,
                'data_rate': device.data_rate,
                'last_checked': device.last_checked.isoformat() if device.last_checked else None,
                'ligne': device.ligne,
                'atelier': device.atelier,
                'snmp_data': device.snmp_data
            })
        return status_list
    
    def get_device_history(self, device_name: str, limit: int = 20) -> List[Dict]:
        """Get historical data for a specific device."""
        if device_name in self.status_history:
            return self.status_history[device_name][-limit:]
        return []

# Global monitor instance
monitor = NetworkMonitor()

# Async wrapper functions for FastAPI compatibility
async def run_monitoring():
    """Start monitoring in a separate thread."""
    # Add some demo devices - you should load these from your database
    demo_devices = [
        {'name': 'Router-001', 'ip': '192.168.1.1', 'ligne': 'Ligne 1', 'atelier': 'Atelier A'},
        {'name': 'Switch-001', 'ip': '192.168.1.10', 'ligne': 'Ligne 1', 'atelier': 'Atelier A'},
        {'name': 'Server-001', 'ip': '192.168.1.100', 'ligne': 'Ligne 2', 'atelier': 'Atelier B'},
        {'name': 'Workstation-001', 'ip': '192.168.1.200', 'ligne': 'Ligne 2', 'atelier': 'Atelier B'},
    ]
    
    for device in demo_devices:
        monitor.add_device(device['name'], device['ip'], device['ligne'], device['atelier'])
    
    # Add alert callback for logging
    def log_alert(alert_data):
        logger.info(f"ALERT: {alert_data['device_name']} ({alert_data['ip_address']}) "
                   f"changed from {alert_data['old_status']} to {alert_data['new_status']}")
    
    monitor.add_alert_callback(log_alert)
    
    # Start monitoring
    monitor.start_monitoring()
    
    # Keep the function running
    try:
        while True:
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        monitor.stop_monitoring()
        raise

def get_monitor():
    """Get the global monitor instance."""
    return monitor