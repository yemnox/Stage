import json

def save_to_file(data):
    with open("data/status.json", "w") as f:
        json.dump(data, f, indent=4)
