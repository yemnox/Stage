import os

username = os.getenv("USERNAME")
domain = os.getenv("USERDOMAIN")
print(f"Current Windows User: {domain}\\{username}")
