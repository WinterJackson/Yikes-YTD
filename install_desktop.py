#!/usr/bin/env python3
import os
import sys

# Define paths
CURRENT_DIR = os.getcwd()
DIST_BIN = os.path.join(CURRENT_DIR, "dist", "Yikes YTD")
ICON_SRC = os.path.join(CURRENT_DIR, "app-images", "icon.png")

# Template for .desktop file
DESKTOP_ENTRY = f"""[Desktop Entry]
Name=Yikes YTD
Comment=Professional YouTube Downloader (Development Build)
Exec="{DIST_BIN}"
Icon={ICON_SRC}
Terminal=false
Type=Application
Categories=Utility;Network;
StartupWMClass=Yikes YTD
"""

def install_desktop_file():
    # Setup path
    desktop_dir = os.path.expanduser("~/.local/share/applications")
    if not os.path.exists(desktop_dir):
        os.makedirs(desktop_dir, exist_ok=True)
        
    file_path = os.path.join(desktop_dir, "yikes-ytd.desktop")
    
    print(f"Creating .desktop file at: {file_path}")
    print(f"Exec: {DIST_BIN}")
    print(f"Icon: {ICON_SRC}")
    print(f"WM Class: Yikes YTD")
    
    with open(file_path, "w") as f:
        f.write(DESKTOP_ENTRY)
        
    print("Done! You may need to logout/login or restart GNOME Shell (Alt+F2, r) to see changes immediately.")
    print("Launch the app from your Applications Grid (App Launcher), NOT just the terminal, to verify the icon.")

if __name__ == "__main__":
    if not os.path.exists(DIST_BIN):
        print(f"Error: Dist binary not found at {DIST_BIN}. Please build first.")
        # We proceed anyway just to create the file for verification
    
    install_desktop_file()
