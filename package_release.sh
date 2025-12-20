#!/bin/bash

# Define release folder name
REL_DIR="Yikes-YTD-Linux"
ZIP_NAME="Yikes-YTD-Linux.zip"

echo "Creating release package..."

# 1. Clean and create release directory
rm -rf "$REL_DIR" "$ZIP_NAME"
mkdir -p "$REL_DIR"

# 2. Copy the binary
if [ -f "dist/Yikes YTD" ]; then
    cp "dist/Yikes YTD" "$REL_DIR/Yikes-YTD"
    chmod +x "$REL_DIR/Yikes-YTD"
else
    echo "Error: dist/Yikes YTD not found. Build the app first!"
    exit 1
fi

# 3. Copy the icon
if [ -f "app-images/icon.png" ]; then
    cp "app-images/icon.png" "$REL_DIR/icon.png"
fi

# 4. Create a README.txt
cat <<EOF > "$REL_DIR/README.txt"
Yikes YTD - Linux Release
==========================

HOW TO RUN:
1. Extract this ZIP file.
2. Double-click the file named 'Yikes-YTD' to run the app.

OPTIONAL SETUP (Recommended):
To add the app to your system menu with the correct icon and name:
1. Open a terminal in this folder.
2. Run: ./setup.sh

This will create a desktop shortcut so you can find the app in your Applications menu.
EOF

# 5. Create a simple setup.sh script for the end-user
cat <<EOF > "$REL_DIR/setup.sh"
#!/bin/bash
# Make files executable
chmod +x Yikes-YTD

# Create local desktop entry
DESKTOP_FILE="\$HOME/.local/share/applications/yikes-ytd.desktop"
CUR_DIR=\$(pwd)

echo "[Desktop Entry]" > "\$DESKTOP_FILE"
echo "Name=Yikes YTD" >> "\$DESKTOP_FILE"
echo "Comment=Professional YouTube Downloader" >> "\$DESKTOP_FILE"
echo "Exec=\"\$CUR_DIR/Yikes-YTD\"" >> "\$DESKTOP_FILE"
echo "Icon=\$CUR_DIR/icon.png" >> "\$DESKTOP_FILE"
echo "Terminal=false" >> "\$DESKTOP_FILE"
echo "Type=Application" >> "\$DESKTOP_FILE"
echo "Categories=Utility;Network;" >> "\$DESKTOP_FILE"
echo "StartupWMClass=Yikes YTD" >> "\$DESKTOP_FILE"

chmod +x "\$DESKTOP_FILE"

echo "Success! Yikes YTD has been added to your applications menu."
echo "You can now launch it like any other app."
EOF

chmod +x "$REL_DIR/setup.sh"

# 6. Zip it up
zip -r "$ZIP_NAME" "$REL_DIR"

echo "Done! Release package created: $ZIP_NAME"
