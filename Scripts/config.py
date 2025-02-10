import os
import json

CONFIG_FILE = "config.json"

def load_credentials():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                saved_path = data.get("credentials", "")
                return saved_path if saved_path and os.path.exists(saved_path) else None
        except Exception as e:
            return None

def save_credentials(path):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump({"credentials": path}, f, ensure_ascii=False, indent=4)
