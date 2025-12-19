import os
import json

DEFAULT_SETTINGS = {
    "download_path": os.path.join(os.getcwd(), "downloads"),
    "theme": "System",
    "default_format": "Video",
    "cookies_path": "",
    "embed_thumbnail": True,
    "embed_metadata": True,
    "download_subtitles": False,
    "proxy_url": "",
    "speed_limit": "", # e.g. 5M
    "notifications": True,
    "clipboard_monitor": False
}

SETTINGS_FILE = "settings.json"
HISTORY_FILE = "history.json"

# In-memory Queue
QUEUE = []

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r") as f:
                return {**DEFAULT_SETTINGS, **json.load(f)}
        except:
            return DEFAULT_SETTINGS
    return DEFAULT_SETTINGS

def save_settings(settings):
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f)

def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r") as f:
                return json.load(f)
        except:
            return []
    return []

def save_history(entry):
    history = load_history()
    history.insert(0, entry) # Add to top
    # Limit to last 50
    history = history[:50]
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f)

def add_to_queue(item):
    QUEUE.append(item)

def remove_from_queue(index):
    if 0 <= index < len(QUEUE):
        del QUEUE[index]

def get_queue():
    return QUEUE

def pop_queue():
    if QUEUE:
        return QUEUE.pop(0)
    return None

# Initialize settings
current_settings = load_settings()
