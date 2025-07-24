import os
import json
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

# Get the base directory of the project
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
DEVICES_JSON = BASE_DIR / "app" / "templates" / "monitoring" / "devices.json"

class DeviceMonitor:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DeviceMonitor, cls).__new__(cls)
            cls._instance.devices = cls._instance.load_devices()
            cls._instance.status_cache = {}
            cls._instance.history = {}
        return cls._instance
    
    def load_devices(self) -> Dict[str, str]:
        """Load devices from the JSON file."""
        try:
            with open(DEVICES_JSON, "r") as file:
                return json.load(file)
        except FileNotFoundError:
            print(f"Warning: {DEVICES_JSON} not found. Using empty device list.")
            return {}
    
    def ping(self, host: str) -> bool:
        """Ping a host to check if it's reachable."""
        # For Windows, use '-n 1' instead of '-c 1'
        param = '-n' if os.name.lower() == 'nt' else '-c 1'
        # For Windows, use '-w' instead of '-W' for timeout
        timeout_param = '-w' if os.name.lower() == 'nt' else '-W'
        
        # Build the ping command
        command = ['ping', param, '1', timeout_param, '1000', host]
        
        # Redirect output to null to avoid printing to console
        with open(os.devnull, 'w') as devnull:
            response = os.system(" ".join(command) + " >nul 2>&1" if os.name == 'nt' else " ".join(command) + " >/dev/null 2>&1")
        
        return response == 0
    
    async def check_device(self, name: str, ip: str) -> Dict:
        """Check the status of a single device."""
        is_online = await asyncio.get_event_loop().run_in_executor(
            None, self.ping, ip
        )
        
        status = {
            "name": name,
            "ip": ip,
            "status": "online" if is_online else "offline",
            "last_checked": datetime.utcnow().isoformat() + "Z"
        }
        
        # Update history
        if name not in self.history:
            self.history[name] = []
        self.history[name].append({
            "status": status["status"],
            "timestamp": status["last_checked"]
        })
        
        # Keep only last 100 entries per device
        if len(self.history[name]) > 100:
            self.history[name] = self.history[name][-100:]
        
        self.status_cache[name] = status
        return status
    
    async def check_all_devices(self) -> List[Dict]:
        """Check the status of all devices asynchronously."""
        tasks = []
        for name, ip in self.devices.items():
            tasks.append(self.check_device(name, ip))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out any exceptions
        return [result for result in results if not isinstance(result, Exception)]
    
    def get_status(self, name: str = None) -> Dict:
        """Get the status of a specific device or all devices."""
        if name:
            return self.status_cache.get(name, {"error": "Device not found"})
        return list(self.status_cache.values())
    
    def get_history(self, name: str = None) -> Dict:
        """Get the status history of a specific device or all devices."""
        if name:
            return {name: self.history.get(name, [])}
        return self.history

# Create a global instance of the monitor
monitor = DeviceMonitor()

async def run_monitoring():
    """Run the monitoring loop."""
    while True:
        try:
            await monitor.check_all_devices()
            await asyncio.sleep(5)  # Check every 5 seconds
        except Exception as e:
            print(f"Error in monitoring loop: {e}")
            await asyncio.sleep(5)  # Wait before retrying

# For testing
if __name__ == "__main__":
    async def main():
        print("Starting device monitoring...")
        await monitor.check_all_devices()
        print("Initial status:", monitor.get_status())
        
        print("\nStarting monitoring loop (Ctrl+C to stop)...")
        try:
            while True:
                await asyncio.sleep(5)
                await monitor.check_all_devices()
                print("\n" + "="*50)
                print(f"Status at {datetime.now()}")
                for device in monitor.get_status():
                    print(f"{device['name']} ({device['ip']}): {device['status'].upper()}")
        except KeyboardInterrupt:
            print("\nStopping monitoring...")
    
    asyncio.run(main())

