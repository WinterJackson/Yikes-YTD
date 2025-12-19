#!/bin/bash
# Make files executable
chmod +x Yikes-YTD

# Create local desktop entry
DESKTOP_FILE="$HOME/.local/share/applications/yikes-ytd.desktop"
CUR_DIR=$(pwd)

echo "[Desktop Entry]" > "$DESKTOP_FILE"
echo "Name=Yikes YTD" >> "$DESKTOP_FILE"
echo "Comment=Professional YouTube Downloader" >> "$DESKTOP_FILE"
echo "Exec=\"$CUR_DIR/Yikes-YTD\"" >> "$DESKTOP_FILE"
echo "Icon=$CUR_DIR/icon.png" >> "$DESKTOP_FILE"
echo "Terminal=false" >> "$DESKTOP_FILE"
echo "Type=Application" >> "$DESKTOP_FILE"
echo "Categories=Utility;Network;" >> "$DESKTOP_FILE"
echo "StartupWMClass=Yikes YTD" >> "$DESKTOP_FILE"

chmod +x "$DESKTOP_FILE"

echo "Success! Yikes YTD has been added to your applications menu."
echo "You can now launch it like any other app."
