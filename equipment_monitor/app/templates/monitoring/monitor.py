import os
import time
import json
from datetime import datetime

# Load devices from the JSON file
def load_devices():
    with open("equipment_monitor/app/templates/monitoring/devices.json", "r") as file:
        return json.load(file)

devices = load_devices()

def ping(host):
    # -c 1: one ping, -W 1: 1 second timeout
    response = os.system(f"ping -c 1 -I 192.168.100.10 {host} > /dev/null 2>&1")
    return response == 0

def monitor():
    while True:
        print("⏱️  ", datetime.now())
        for name, ip in devices.items():
            status = "Online" if ping(ip) else "Offline"
            print(f"🔎 {name} ({ip}) is {status}")
        print("-" * 40)
        time.sleep(5)

if __name__ == "__main__":
    monitor()

