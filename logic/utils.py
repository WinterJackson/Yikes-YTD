
from typing import Optional
import shutil
import os

def parse_time_to_seconds(time_str: str) -> Optional[int]:
    """Parse time string (HH:MM:SS, MM:SS, or SS) to seconds. Returns None on invalid input."""
    try:
        parts = list(map(int, time_str.split(':')))
        # Validate: all parts must be non-negative
        if any(p < 0 for p in parts):
            return None
        if len(parts) == 3:
            return parts[0] * 3600 + parts[1] * 60 + parts[2]
        elif len(parts) == 2:
            return parts[0] * 60 + parts[1]
        elif len(parts) == 1:
            return parts[0]
    except:
        return None
    return None

def format_eta(seconds: Optional[int]) -> str:
    if seconds is None:
        return "Unknown"
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return "{:02}:{:02}:{:02}".format(int(hours), int(minutes), int(seconds))

def get_free_disk_space_gb(path: str) -> float:
    """Get free disk space in GB for the given path."""
    try:
        if not os.path.exists(path):
            path = os.path.dirname(path) or '.'
        usage = shutil.disk_usage(path)
        return usage.free / (1024 ** 3)  # Convert to GB
    except:
        return -1  # Unable to determine

def format_bytes(size_bytes: int) -> str:
    """Format bytes to human-readable string."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 ** 2:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 ** 3:
        return f"{size_bytes / (1024 ** 2):.1f} MB"
    else:
        return f"{size_bytes / (1024 ** 3):.2f} GB"
