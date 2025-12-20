import os
import json
import tempfile
import shutil

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
QUEUE_FILE = "queue.json"

def _atomic_write_json(filepath, data):
    """Write JSON atomically using tempfile + rename to prevent corruption."""
    dir_path = os.path.dirname(filepath) or '.'
    try:
        # Create temp file in same directory for atomic rename
        fd, tmp_path = tempfile.mkstemp(suffix='.tmp', dir=dir_path)
        try:
            with os.fdopen(fd, 'w') as f:
                json.dump(data, f, indent=2)
            # Atomic rename (works on same filesystem)
            shutil.move(tmp_path, filepath)
        except:
            # Clean up temp file on error
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            raise
    except Exception as e:
        # Fallback to direct write if temp approach fails
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r") as f:
                return {**DEFAULT_SETTINGS, **json.load(f)}
        except:
            return DEFAULT_SETTINGS
    return DEFAULT_SETTINGS

def save_settings(settings):
    _atomic_write_json(SETTINGS_FILE, settings)

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
    _atomic_write_json(HISTORY_FILE, history)

# --- Queue Management (Now Persistent) ---
def _load_queue():
    if os.path.exists(QUEUE_FILE):
        try:
            with open(QUEUE_FILE, "r") as f:
                return json.load(f)
        except:
            return []
    return []

def _save_queue(queue):
    _atomic_write_json(QUEUE_FILE, queue)

def add_to_queue(item):
    queue = _load_queue()
    queue.append(item)
    _save_queue(queue)

def remove_from_queue(index):
    queue = _load_queue()
    if 0 <= index < len(queue):
        del queue[index]
        _save_queue(queue)

def get_queue():
    return _load_queue()

def pop_queue():
    queue = _load_queue()
    if queue:
        item = queue.pop(0)
        _save_queue(queue)
        return item
    return None

def clear_queue():
    _save_queue([])

# Initialize settings
current_settings = load_settings()
