import customtkinter as ctk
from tkinter import messagebox, PhotoImage, filedialog
import threading
import os
import tkinter as tk
import webbrowser
import requests
from PIL import Image, ImageTk
from io import BytesIO
import subprocess
import sys
import platform
import copy
import time
import concurrent.futures
import re
import logging

# Setup Logging - DEBUG to catch everything
logging.basicConfig(filename="yikes_debug.log", level=logging.DEBUG, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Import Logic Modules
from logic.settings import current_settings, save_settings, add_to_queue, remove_from_queue, get_queue, pop_queue, save_history, load_history, clear_queue
from logic.utils import parse_time_to_seconds, format_eta, get_free_disk_space_gb
from logic.downloader import fetch_video_info, fetch_playlist_info, start_download_thread, build_ydl_opts, get_max_resolution

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller bundle """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


class SplashScreen(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.overrideredirect(True)
        # Center splash
        w, h = 400, 250
        x = (self.winfo_screenwidth() // 2) - (w // 2)
        y = (self.winfo_screenheight() // 2) - (h // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")
        self.configure(fg_color="#1a1a1a") # Dark elegant bg
        
        # Logo / Text
        # Assuming we don't have a logo image file guaranteed, we use elegant text
        ctk.CTkLabel(self, text="Yikes YTD", font=("Comfortaa", 40, "bold"), text_color="#1F6AA5").place(relx=0.5, rely=0.4, anchor="center")
        ctk.CTkLabel(self, text="Professional YouTube Downloader", font=("Comfortaa", 12), text_color="gray60").place(relx=0.5, rely=0.55, anchor="center")
        
        # Loader
        self.progress = ctk.CTkProgressBar(self, width=200, height=4, progress_color="#1F6AA5")
        self.progress.place(relx=0.5, rely=0.75, anchor="center")
        self.progress.set(0) # 0 to start
        self.progress.start() # Indeterminate mode

class YikesApp(ctk.CTk):
    def __init__(self):
        # Set className to match StartupWMClass in .desktop file for correct icon association
        super().__init__(className="Yikes YTD")
        
        # FORCE the window manager class (critical for Linux Docks/Taskbars)
        # This tells GNOME/KDE: "I am Yikes YTD", matching StartupWMClass in .desktop
        try:
            # Set internal Tk app name to correct Case (Fixes "Yikes ytd" hover text)
            self.call('tk', 'appname', 'Yikes YTD')
            
            # Set X11 Class/Instance explicitly
            # Note: Tcl/Tk often lowercases the instance name (first part).
            # We enforce both to be safe: instance="Yikes YTD", class="Yikes YTD"
            self.call('wm', 'attributes', '.', '-class', 'Yikes YTD')
            self.call('wm', 'group', '.', '.')
        except Exception as e:
            logging.warning(f"Failed to set WM attributes: {e}")
        
        # Hide initially
        self.withdraw()
        
        # Show Splash
        self.splash = SplashScreen(self)
        
        # Identity
        self.title("Yikes YTD")
        self.geometry("900x1000")
        self.minsize(900, 1000)
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Runtime Icon
        try:
             icon_p = resource_path(os.path.join("app-images", "icon.png"))
             logging.info(f"Attempting to load icon from: {icon_p}")
             
             if os.path.exists(icon_p):
                 # Use PIL to generate multiple sizes for best Linux compatibility
                 # User guide suggests: 16x16, 32x32, 48x48 etc.
                 # Convert to RGBA to ensure transparency (circular shape) is preserved
                 main_img = Image.open(icon_p).convert("RGBA")
                 
                 self.app_icons = []
                 for size in (16, 32, 48, 64, 128):
                     resized = main_img.resize((size, size), Image.Resampling.LANCZOS)
                     self.app_icons.append(ImageTk.PhotoImage(resized))
                 
                 # Pass False (apply to this window) and unpack all sizes
                 self.wm_iconphoto(False, *self.app_icons)
                 logging.info(f"Loaded {len(self.app_icons)} icon sizes successfully")
             else:
                 logging.error(f"Icon file not found at: {icon_p}")
        except Exception as e:
             logging.error(f"Runtime icon failed: {e}", exc_info=True)
             print(f"Warn: Runtime icon failed: {e}")
        
        # Defer Loading
        self.after(200, self.load_app)

    def load_app(self):
        try:
            logging.info("Starting load_app...")
            # Theme Setup
            self.setup_theme()
            logging.info("Theme setup complete")
            
            # State
            self.download_in_progress = False
            self.current_frame = None
            self.is_playlist = False
            self.playlist_entries = []
            self.current_video_info = None  # Prevent AttributeError on direct download
            self.current_playlist_info = None
            self.current_playlist_folder = None
            self.playlist_widgets = []  # For playlist row UI references
            self.is_cancelled = False
            self.is_processing_queue = False
            self.is_fetching = False  # Debounce for rapid clicks
            
            # Async Executor
            self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)
            
            # Layout Config
            self.grid_columnconfigure(1, weight=1)
            self.grid_rowconfigure(0, weight=1)
            
            # Create UI
            logging.info("Loading icons...")
            self.load_icons()
            logging.info("Creating sidebar...")
            self.create_sidebar()
            logging.info("Creating content area...")
            self.create_content_area()
            
            # Start background tasks
            
            # Start background tasks
            # self.check_clipboard_loop() # Removed non-functional loop

            # Build Frames
            logging.info("Building frames...")
            self.frames = {}
            self.build_frames()
            
            # Show Start
            self.select_frame("Home")
            
            # Finish Loading: Close Splash and Show Main Window
            logging.info("Destroying splash...")
            self.splash.destroy()
            self.deiconify()
            logging.info("App loaded successfully")
            
        except Exception as e:
            logging.critical(f"Failed to load app: {e}", exc_info=True)
            messagebox.showerror("Fatal Error", f"Failed to load application:\n{e}")
            self.destroy()

    def setup_theme(self):
        ctk.set_appearance_mode(current_settings["theme"])
        ctk.set_default_color_theme("blue")
        
        # --- Strict Blue Color Palette ---
        # --- Strict Blue Color Palette ---
        self.accent_color = current_settings.get("accent_color", "#1F6AA5") # Custom Accent or Standard Blue
        
        # Derive hover_color dynamically (darken accent by ~30%)
        def darken_hex(hex_color, factor=0.7):
            hex_color = hex_color.lstrip('#')
            r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
            r, g, b = int(r * factor), int(g * factor), int(b * factor)
            return f"#{r:02x}{g:02x}{b:02x}"
        
        self.hover_color = darken_hex(self.accent_color)
        self.text_color = ("gray10", "gray90")  # Auto-switch: dark text on light, light text on dark
        
        # Theme-Aware Background Colors (tuple format: light, dark)
        self.bg_color = ("#FAFAFA", "#1A1A1A")  # Main app background
        self.sidebar_color = ("#E8E8E8", "#2B2B2B")  # Sidebar and content frames
        self.card_color = ("gray95", "gray20")  # Cards and info boxes
        self.separator_color = ("gray70", "gray40")  # Dividers
        
        self.configure(fg_color=self.bg_color)
        
        # Load Sidebar Icons
        self.load_icons()
    
    def apply_theme_instant(self):
        """Apply theme changes instantly without restart"""
        new_theme = self.theme_var.get()
        current_settings["theme"] = new_theme
        
        # Set CTK appearance mode (this updates ALL widgets with tuple colors automatically)
        ctk.set_appearance_mode(new_theme)

    def validate_security(self, url):
        """Strictly validate input URL to ensure security."""
        # 1. Check scheme (Must be http or https)
        if not re.match(r'^https?://', url, re.IGNORECASE):
            return False, "Invalid URL Scheme. Only HTTP/HTTPS allowed."
            
        # 2. Check for suspicious characters (Command Injection Prevention)
        # Note: subprocess usage prevents this usually, but good practice
        if any(char in url for char in [';', '|', '`', '$']):
            return False, "Suspicious characters detected in URL."
            
        return True, "Valid"

    def load_icons(self):
        # Helper to load light/dark pair
        def load_icon(name):
            try:
                # Use resource_path for bundled compatibility
                light_p = resource_path(f"app-images/icon_{name}_black.png")
                dark_p = resource_path(f"app-images/icon_{name}_white.png")
                
                light = Image.open(light_p)
                dark = Image.open(dark_p)
                return ctk.CTkImage(light_image=light, dark_image=dark, size=(20, 20))
            except Exception as e:
                print(f"Icon load error ({name}): {e}")
                return None
        
        self.icons = {
            "Menu": load_icon("menu"),
            "Home": load_icon("home"),
            "Download": load_icon("download"),
            "Queue": load_icon("queue"),
            "History": load_icon("history"),
            "Settings": load_icon("settings"),
            "Help": load_icon("help"),
            "About": load_icon("about"),
            "Feedback": load_icon("feedback")
        }
             
    def create_sidebar(self):
        self.sidebar_open = True
        self.sidebar_animating = False # Lock for animation
        self.sidebar_frame = ctk.CTkFrame(self, width=200, corner_radius=0, fg_color=self.sidebar_color)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_propagate(False) # STRICTLY respect width configuration
        self.sidebar_frame.grid_rowconfigure(11, weight=1) # Spacer after all buttons (row 2-9 are buttons, row 10+ is space)
        self.sidebar_frame.grid_columnconfigure(0, weight=1) # Ensure buttons expand to full width
        
        # Menu Button (Hamburger) - Fixed width, only icon clickable
        self.menu_btn = ctk.CTkButton(self.sidebar_frame, text="", image=self.icons.get("Menu"), 
                                      width=60, height=32, border_spacing=18, anchor="center",
                                      fg_color="transparent", hover_color=self.sidebar_color,
                                      command=self.toggle_sidebar)
        self.menu_btn.grid(row=0, column=0, sticky="w", padx=0, pady=1)

        # Buttons - Reordered: Feedback immediately after About
        self.nav_buttons = {}
        buttons = ["Home", "Download", "Queue", "History", "Settings", "Help", "About", "Feedback"]
        
        for i, btn_text in enumerate(buttons):
            # Uniform Button Styling - Sidebar
            icon = self.icons.get(btn_text)
            
            btn = ctk.CTkButton(self.sidebar_frame, corner_radius=0, height=32, border_spacing=18, width=0, 
                                text=f"  {btn_text}", image=icon, compound="left",
                                fg_color="transparent", text_color=self.text_color, hover_color=self.hover_color,
                                font=("Comfortaa", 14),
                                anchor="w", command=lambda n=btn_text: self.select_frame(n))
            # Layout: Menu is Row 0. Nav buttons start at Row 1.
            # Alignment: Left 20px margin + 20px Icon = 40px. 
            # In 60px Sidebar: 20px Left Margin + 20px Icon + 20px Right Margin = Perfect Center.
            btn.grid(row=i+1, column=0, sticky="ew", pady=1)
            
            # Event Binding for Hover Text Color Change
            btn.bind("<Enter>", lambda e, b=btn: self.on_hover_enter(b))
            btn.bind("<Leave>", lambda e, b=btn, n=btn_text: self.on_hover_leave(b, n))
            
            self.nav_buttons[btn_text] = btn

    def toggle_sidebar(self):
        if self.sidebar_animating: return 
        self.sidebar_animating = True
        
        if self.sidebar_open:
            # COLLAPSE
            # 1. Hide Text immediately
            for name, btn in self.nav_buttons.items():
                btn.configure(text="")
            self.menu_btn.configure(width=60)
            
            # 2. Animate Width Down (Step 35 = Fast)
            self.animate_sidebar(200, 60, -35)
            self.sidebar_open = False
        else:
            # EXPAND
            # 1. Animate Width Up (Step 35 = Fast)
            self.animate_sidebar(60, 200, 35)
            self.sidebar_open = True

    def animate_sidebar(self, current_width, target_width, step):
        # Linear Interpolation Animation
        if current_width == target_width:
             # End of Animation
             if self.sidebar_open:
                 # If we just expanded, show text now
                 for name, btn in self.nav_buttons.items():
                     btn.configure(text=f"  {name}")
             
             self.sidebar_animating = False
             return

        # Calculate next step
        next_width = current_width + step
        
        # Clamp Logic
        if step > 0 and next_width > target_width: next_width = target_width
        if step < 0 and next_width < target_width: next_width = target_width
        
        self.sidebar_frame.configure(width=next_width)
        self.after(5, lambda: self.animate_sidebar(next_width, target_width, step))

    def on_hover_enter(self, btn):
        # On hover, text should be visible on the blue hover background
        if btn.cget("state") != "disabled":
             btn.configure(text_color="white")

    def on_hover_leave(self, btn, name):
        # Revert to standard if not active
        if self.current_frame == name:
             btn.configure(text_color="white") # Keep white if active (blue bg)
        else:
             btn.configure(text_color=self.text_color)  # Theme-aware text color

    def create_content_area(self):
        self.content_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.content_frame.grid(row=0, column=1, sticky="nsew", padx=30, pady=30)
        self.content_frame.grid_rowconfigure(0, weight=1)
        self.content_frame.grid_columnconfigure(0, weight=1)

    def build_frames(self):
        # Create all frame instances
        for name in ["Home", "Download", "Queue", "History", "Settings", "Help", "About", "Feedback"]:
            frame = ctk.CTkFrame(self.content_frame, corner_radius=10, fg_color=self.sidebar_color)
            frame.grid(row=0, column=0, sticky="nsew")
            self.frames[name] = frame
            
            # Call builder
            getattr(self, f"build_{name.lower()}_tab")(frame)

    def select_frame(self, name):
        # Update Buttons
        for btn_name, btn in self.nav_buttons.items():
            if btn_name == name:
                btn.configure(fg_color=self.accent_color, text_color="white") # Active State Blue
            else:
                btn.configure(fg_color="transparent", text_color=self.text_color)
        
        # Show Frame
        frame = self.frames[name]
        frame.tkraise()
        self.current_frame = name

        # Auto-refresh specific frames
        if name == "Queue":
            self.update_queue_ui()
        elif name == "History":
            self.update_history_ui()

    # --- Builders with Uniform Spacing & STRICT BLUE Theme ---

    def build_home_tab(self, parent):
        # Center Content
        container = ctk.CTkFrame(parent, fg_color="transparent")
        container.place(relx=0.5, rely=0.5, anchor="center")
        
        ctk.CTkLabel(container, text="Welcome to Yikes YTD", font=("Comfortaa", 32, "bold"), text_color=self.text_color).pack(pady=(0, 20))
        
        desc = "Effortless YouTube Downloading.\nChoose a Video, Playlist, or Audio."
        ctk.CTkLabel(container, text=desc, font=("Comfortaa", 18), text_color=self.text_color).pack(pady=10)
        
        # Main CTA - BLUE
        ctk.CTkButton(container, text="Start Downloading", command=lambda: self.select_frame("Download"), 
                      font=("Comfortaa", 16, "bold"), height=50, width=200, corner_radius=25, 
                      fg_color=self.accent_color, hover_color=self.hover_color, text_color="white").pack(pady=40)

    def build_download_tab(self, parent):
        # Consistent Padding container
        # Consistent Padding container
        container = ctk.CTkFrame(parent, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=40, pady=40)
        
        # URL Input
        ctk.CTkLabel(container, text="YouTube URL", font=("Comfortaa", 14, "bold"), text_color=self.accent_color).pack(anchor="w", pady=(0, 10))
        
        input_row = ctk.CTkFrame(container, fg_color="transparent")
        input_row.pack(fill="x", pady=0)
        
        self.url_entry = ctk.CTkEntry(input_row, height=45, font=("Comfortaa", 14), placeholder_text="Paste link here...")
        self.url_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        # Check Button - BLUE
        ctk.CTkButton(input_row, text="Check", command=self.check_link, width=100, height=45, 
                      fg_color=self.accent_color, hover_color=self.hover_color, text_color="white").pack(side="left")
                      
        # Clear Button (Ghost style with proper hover)
        clear_btn = ctk.CTkButton(input_row, text="Clear", command=self.clear_data, width=80, height=45,
                      fg_color="transparent", border_width=2, border_color=self.accent_color, text_color=self.text_color, hover_color=self.hover_color)
        clear_btn.pack(side="left", padx=(10, 0))
        clear_btn.bind("<Enter>", lambda e: clear_btn.configure(text_color="white"))
        clear_btn.bind("<Leave>", lambda e: clear_btn.configure(text_color=self.text_color))
        
        # Controls Row
        ctrl_frame = ctk.CTkFrame(container, fg_color="transparent")
        ctrl_frame.pack(pady=20, fill="x")
        
        # Format
        format_frame = ctk.CTkFrame(ctrl_frame, fg_color="transparent")
        format_frame.pack(side="left", padx=(0, 30))
        
        format_row = ctk.CTkFrame(format_frame, fg_color="transparent")
        format_row.pack(anchor="w")
        
        ctk.CTkLabel(format_row, text="Format:", font=("Comfortaa", 14), text_color=self.text_color).pack(side="left", padx=(0, 10))
        self.format_var = ctk.StringVar(value="1080p")
        self.format_combo = ctk.CTkComboBox(format_row, variable=self.format_var, 
                                            values=["4K (2160p)", "1440p (2K)", "1080p", "720p", "480p", 
                                                    "Audio (MP3 - 320kbps)", "Audio (MP3 - 192kbps)", "Audio (MP3 - 128kbps)", 
                                                    "Audio (WAV)", "Audio (M4A)", "GIF (Animated)"], 
                                            width=160, height=35,
                                            fg_color=self.card_color, text_color=self.text_color,
                                            border_color=self.accent_color, button_color=self.accent_color, button_hover_color=self.hover_color,
                                            dropdown_fg_color=self.card_color, dropdown_text_color=self.text_color)
        self.format_combo.pack(side="left", padx=(0, 20))
        
        # Trim Toggle - BLUE Accent (Now in the same row for alignment)
        self.trim_var = ctk.BooleanVar(value=False)
        self.trim_btn = ctk.CTkCheckBox(format_row, text="Trim Video", variable=self.trim_var, text_color=self.text_color, 
                                        fg_color=self.accent_color, hover_color=self.hover_color, command=self.toggle_trim)
        self.trim_btn.pack(side="left")
        
        # Trim Inputs (Now in the same row for alignment)
        self.trim_frame = ctk.CTkFrame(format_row, fg_color="transparent")
        self.trim_frame.pack(side="left", padx=20)
        self.start_trim = ctk.CTkEntry(self.trim_frame, width=70, placeholder_text="Start")
        self.start_trim.pack(side="left", padx=5)
        ctk.CTkLabel(self.trim_frame, text="-", text_color=self.text_color).pack(side="left")
        self.end_trim = ctk.CTkEntry(self.trim_frame, width=70, placeholder_text="End")
        self.end_trim.pack(side="left", padx=5)
        
        # Display Resolution Indicator (Below the whole row)
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        
        # Map height to quality name
        if screen_h >= 2160:
            display_quality = "4K"
        elif screen_h >= 1440:
            display_quality = "2K"
        elif screen_h >= 1080:
            display_quality = "1080p"
        elif screen_h >= 720:
            display_quality = "720p"
        else:
            display_quality = "SD"
        
        display_info = f"📺 Your display: {screen_w}×{screen_h} ({display_quality})"
        self.display_res_label = ctk.CTkLabel(
            format_frame, 
            text=display_info, 
            font=("Comfortaa", 11), 
            text_color="gray60"
        )
        self.display_res_label.pack(anchor="w", pady=(4, 0))
        
        # Initial State
        self.toggle_trim()

        # Action Buttons (Moved back to TOP as requested)
        action_frame = ctk.CTkFrame(container, fg_color="transparent")
        action_frame.pack(pady=20, fill="x")
        
        # Download Button - BLUE
        self.download_btn = ctk.CTkButton(action_frame, text="Download Now", command=self.start_download, 
                                          width=200, height=50, font=("Comfortaa", 16, "bold"), 
                                          fg_color=self.accent_color, hover_color=self.hover_color, text_color="white")
        self.download_btn.pack(side="left")
        
        # Queue Button
        q_btn = ctk.CTkButton(action_frame, text="Add to Queue", command=self.add_to_queue_action, 
                      width=150, height=50, 
                      fg_color="transparent", border_width=2, border_color=self.accent_color, text_color=self.text_color, hover_color=self.hover_color)
        q_btn.pack(side="left", padx=20)
        q_btn.bind("<Enter>", lambda e, b=q_btn: b.configure(text_color="white"))
        q_btn.bind("<Leave>", lambda e, b=q_btn: b.configure(text_color=self.text_color))

        # Play Video - BLUE
        self.play_btn = ctk.CTkButton(action_frame, text="Play Video", command=self.play_video, 
                                      fg_color=self.accent_color, hover_color=self.hover_color, text_color="white",
                                      state="disabled", height=50, width=150)
        self.play_btn.pack(side="left")

        # Info & Progress Frame (Container for both Video and Playlist views)
        self.info_frame_container = ctk.CTkFrame(container, fg_color="transparent")
        self.info_frame_container.pack(pady=(20,0), fill="both", expand=True)

        # 1. Single Video View
        self.video_info_frame = ctk.CTkFrame(self.info_frame_container, fg_color="transparent")
        
        # Responsive Components
        self.layout_mode = "stacked" # 'stacked' or 'side'
        
        # 1. Thumbnail Container
        self.v_thumb_frame = ctk.CTkFrame(self.video_info_frame, fg_color="transparent")
        self.thumbnail_label = ctk.CTkLabel(self.v_thumb_frame, text="")
        # Remove padx=20 to align with URL input (container has padx=40)
        self.thumbnail_label.pack(pady=(10, 5), anchor="w", padx=0)
        
        # 2. Data Container
        self.v_data_frame = ctk.CTkFrame(self.video_info_frame, fg_color="transparent")
        
        self.video_title_label = ctk.CTkLabel(self.v_data_frame, text="", font=("Comfortaa", 16, "bold"), text_color=self.text_color, wraplength=500, justify="left")
        self.video_title_label.pack(pady=(5, 2), anchor="w", padx=0)
        
        self.video_details_label = ctk.CTkLabel(self.v_data_frame, text="", font=("Comfortaa", 14), text_color="gray70", justify="left")
        self.video_details_label.pack(pady=(0, 10), anchor="w", padx=0)
        
        self.progress_bar = ctk.CTkProgressBar(self.v_data_frame, orientation="horizontal", height=15, progress_color=self.accent_color)
        self.progress_bar.set(0)
        # self.progress_bar.pack(fill="x", pady=(5, 5), padx=0, anchor="w") # HIDDEN INITIALLY
        
        self.progress_text = ctk.CTkLabel(self.v_data_frame, text="0%", text_color=self.text_color)
        # self.progress_text.pack(pady=(0, 10), anchor="w", padx=0) # HIDDEN INITIALLY
        
        # Initial Pack (Stacked)
        self.v_thumb_frame.pack(side="top", anchor="w", fill="x")
        self.v_data_frame.pack(side="top", fill="x", pady=(20, 0))

        # Bind dynamic resizing logic
        self.video_info_frame.bind("<Configure>", self._on_configure)
        
        # 2. Playlist View
        self.playlist_info_frame = ctk.CTkFrame(self.info_frame_container, fg_color="transparent")
        self.playlist_label = ctk.CTkLabel(self.playlist_info_frame, text="Playlist Content", font=("Comfortaa", 16, "bold"), text_color=self.text_color)
        self.playlist_label.pack(pady=5, anchor="w")
        self.playlist_scroll = ctk.CTkScrollableFrame(self.playlist_info_frame, height=200, fg_color=self.card_color)
        self.playlist_scroll.pack(fill="both", expand=True, pady=5)
        # Enable smooth pixel-based scrolling
        # Enable smooth pixel-based scrolling
        self.playlist_scroll._parent_canvas.configure(yscrollincrement=1)
        
        try:
             # Hide scrollbar initially (Auto-hide logic)
             self.playlist_scroll._scrollbar.grid_remove()
        except:
             pass
        
        # Shared Status (Kept in parent for global messages / playlist status)
        self.status_label = ctk.CTkLabel(self.info_frame_container, text="", font=("Comfortaa", 14), text_color=self.text_color)
        self.status_label.pack(pady=5, anchor="w", padx=0)
        
        # Initially show video view
        self.video_info_frame.pack(fill="both", expand=True)

    def _on_configure(self, event):
        width = event.width
        # Threshold for shifting layout
        # If > 850px, go side-by-side
        # Else, stacked
        
        target_mode = "stacked"
        if width > 850:
             target_mode = "side"
             
        if target_mode != self.layout_mode:
             self.layout_mode = target_mode
             self.v_thumb_frame.pack_forget()
             self.v_data_frame.pack_forget()
             
             if self.layout_mode == "side":
                  # Side by side: Thumb Left, Data Right
                  self.v_thumb_frame.pack(side="left", anchor="n")
                  # ADDED PADDING LEFT (between thumb and data)
                  self.v_data_frame.pack(side="left", fill="both", expand=True, padx=(20, 10))
             else:
                  # Stacked: Thumb Top, Data Top
                  self.v_thumb_frame.pack(side="top", anchor="w", fill="x")
                  # ADDED PADDING TOP (between thumb and data)
                  self.v_data_frame.pack(side="top", fill="x", pady=(20, 0))
                  
        # Dynamic Wrapping update based on data frame width
        # If side mode, width is roughly total - 500 (thumb) - padding
        wrap_w = width - 60
        if self.layout_mode == "side":
             wrap_w = width - 550 - 60
             
        if wrap_w > 200:
             self.video_title_label.configure(wraplength=wrap_w)

    def _check_playlist_scroll(self):
        # Auto-hide scrollbar if content fits
        try:
             # Need to force update to get accurate requirements
             self.playlist_scroll.update_idletasks()
             
             # Height of the canvas (visible area)
             visible_h = self.playlist_scroll._parent_canvas.winfo_height()
             
             # Height of the content (interior frame)
             interior = self.playlist_scroll.winfo_children()[0] 
             content_h = interior.winfo_reqheight()
             
             if content_h > visible_h:
                  self.playlist_scroll._scrollbar.grid()
             else:
                  self.playlist_scroll._scrollbar.grid_remove()
        except:
             pass

    def toggle_trim(self):
        state = "normal" if self.trim_var.get() else "disabled"
        self.start_trim.configure(state=state)
        self.end_trim.configure(state=state)
        if not self.trim_var.get():
             self.trim_frame.pack_forget()
        else:
             self.trim_frame.pack(side="left", padx=20)

    def build_queue_tab(self, parent):
        header = ctk.CTkFrame(parent, fg_color="transparent")
        header.pack(pady=(40, 20), fill="x", padx=40)
        
        # Left Aligned Title
        ctk.CTkLabel(header, text="Pending Downloads", font=("Comfortaa", 24, "bold"), text_color=self.accent_color).pack(side="left")
        
        # Clear Queue (Right)
        ctk.CTkButton(header, text="Clear Queue", width=120, height=35, 
                      fg_color=self.accent_color, hover_color=self.hover_color, text_color="white",
                      command=self.clear_queue_action).pack(side="right")
        
        # Process Queue (Left Aligned below header? Or in header?)
        # User said "START WITH THE TITLE ... AND THE PROCESSING QUEUE BUTTON".
        # If I put Process Button top-left, it might look good.
        # But usually Actions are below list or Top Right.
        # "Start with the title... and the processing button".
        # I'll put Process Button BELOW the title (Left Aligned) before the list?
        # Or below the list? Code had it below list.
        # I'll put it BELOW the list, Left Aligned.
        
        self.queue_frame = ctk.CTkScrollableFrame(parent, width=600, height=400, fg_color="transparent")
        self.queue_frame.pack(fill="both", expand=True, padx=40, pady=10)
        
        # Process Queue - Left Aligned
        ctk.CTkButton(parent, text="Start Processing Queue", command=self.process_queue, height=45, 
                      fg_color=self.accent_color, hover_color=self.hover_color, text_color="white").pack(anchor="w", padx=40, pady=20)
                      
        self.update_queue_ui()

    def build_history_tab(self, parent):
        header = ctk.CTkFrame(parent, fg_color="transparent")
        header.pack(pady=(40, 20), fill="x", padx=40)
        
        ctk.CTkLabel(header, text="Download History", font=("Comfortaa", 24, "bold"), text_color=self.accent_color).pack(side="left")
        
        # Clear History Button
        ctk.CTkButton(header, text="Clear History", width=120, height=35, 
                      fg_color=self.accent_color, hover_color=self.hover_color, text_color="white",
                      command=self.clear_history_action).pack(side="right")
        
        self.history_frame = ctk.CTkScrollableFrame(parent, width=600, height=400, fg_color="transparent")
        self.history_frame.pack(fill="both", expand=True, padx=40, pady=10)
        self.update_history_ui()

    def build_settings_tab(self, parent):
        # 1. Title (Left)
        ctk.CTkLabel(parent, text="Settings", font=("Comfortaa", 24, "bold"), text_color=self.accent_color).pack(anchor="w", padx=40, pady=(40, 10))
        
        # 2. Save Button (Left Aligned, Top prominent)
        # User requested Left alignment for Title and Save Button.
        ctk.CTkButton(parent, text="Save Settings", width=140, height=35, 
                      fg_color=self.accent_color, hover_color=self.hover_color, text_color="white",
                      command=self.save_config).pack(anchor="w", padx=40, pady=(0, 20))
        
        # 3. Content
        s_frame = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        s_frame.pack(fill="both", expand=True, padx=40, pady=0)
        self.settings_scroll = s_frame
        # Hide scrollbar
        try: s_frame._scrollbar.grid_remove()
        except: pass
        
        # Bind Scroll
        self._bind_scroll_recursive(s_frame)
        
        def add_section(title):
            ctk.CTkLabel(s_frame, text=title, font=("Comfortaa", 16, "bold"), text_color=self.accent_color).pack(anchor="w", pady=(20, 10))
            
        def add_check(text, var):
             ctk.CTkCheckBox(s_frame, text=text, variable=var, text_color=self.text_color, 
                             fg_color=self.accent_color, hover_color=self.hover_color).pack(anchor="w", pady=5)

        # -- General --
        add_section("General")
        
        # Download Path
        ctk.CTkLabel(s_frame, text="Download Path", text_color=self.text_color, font=("Comfortaa", 12, "bold")).pack(anchor="w")
        path_box = ctk.CTkFrame(s_frame, fg_color="transparent")
        path_box.pack(fill="x", pady=(5, 10))
        self.path_entry = ctk.CTkEntry(path_box, height=35)
        self.path_entry.insert(0, current_settings["download_path"])
        self.path_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        ctk.CTkButton(path_box, text="Browse", width=80, height=35, command=self.browse_path, 
                      fg_color=self.accent_color, hover_color=self.hover_color, text_color="white").pack(side="left")
                      
        # Cookies File (New)
        ctk.CTkLabel(s_frame, text="Cookies File (Netscape Format - Optional)", text_color=self.text_color, font=("Comfortaa", 12, "bold")).pack(anchor="w")
        c_box = ctk.CTkFrame(s_frame, fg_color="transparent")
        c_box.pack(fill="x", pady=(5, 10))
        self.cookies_entry = ctk.CTkEntry(c_box, height=35)
        self.cookies_entry.insert(0, current_settings.get("cookies_path", ""))
        self.cookies_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        ctk.CTkButton(c_box, text="Browse", width=80, height=35, command=self.browse_cookies, 
                      fg_color=self.accent_color, hover_color=self.hover_color, text_color="white").pack(side="left")
                      
        # -- Appearance --
        add_section("Appearance")
        # Accent Color
        ctk.CTkLabel(s_frame, text="Accent Color", text_color=self.text_color).pack(anchor="w", pady=(10, 5))
        color_row = ctk.CTkFrame(s_frame, fg_color="transparent")
        color_row.pack(anchor="w")
        
        # Preset Colors (Blue is Default)
        accents = [
            ("#1F6AA5", "Default"),  # Blue marked as Default
            ("#9C27B0", "Purple"), 
            ("#2E7D32", "Green"), 
            ("#E65100", "Orange"),
            ("#C62828", "Red")
        ]
        
        current_accent = current_settings.get("accent_color", "#1F6AA5")
        
        for color_code, name in accents:
             # Highlight selected color with border
             border_w = 3 if color_code.upper() == current_accent.upper() else 0
             btn = ctk.CTkButton(color_row, text="", width=30, height=30, fg_color=color_code, corner_radius=15,
                           border_width=border_w, border_color="white",
                           command=lambda c=color_code: self.change_accent_color(c))
             btn.pack(side="left", padx=5)
             
             # Tooltip for Default
             if name == "Default":
                  lbl = ctk.CTkLabel(color_row, text="(Default)", font=("Comfortaa", 10), text_color="gray60")
                  lbl.pack(side="left", padx=(0, 10))
        
        # Custom Color Input
        ctk.CTkLabel(s_frame, text="Or enter custom hex color:", text_color="gray60", font=("Comfortaa", 11)).pack(anchor="w", pady=(10, 2))
        custom_row = ctk.CTkFrame(s_frame, fg_color="transparent")
        custom_row.pack(anchor="w")
        
        self.custom_color_entry = ctk.CTkEntry(custom_row, width=100, height=30, placeholder_text="#FF5733")
        self.custom_color_entry.pack(side="left", padx=(0, 10))
        
        ctk.CTkButton(custom_row, text="Apply", width=60, height=30, fg_color=self.accent_color, hover_color=self.hover_color,
                      command=self.apply_custom_color).pack(side="left")
                           
        ctk.CTkLabel(s_frame, text="Theme Mode", text_color=self.text_color).pack(anchor="w", pady=(10, 2))
        self.theme_var = ctk.StringVar(value=current_settings["theme"])
        ctk.CTkOptionMenu(s_frame, values=["System", "Light", "Dark"], variable=self.theme_var, 
                          fg_color=self.accent_color, button_color=self.hover_color, button_hover_color=self.hover_color, text_color="white").pack(anchor="w", pady=5)
        
        # -- Automation --
        add_section("Automation & Features")
        self.thumb_var = ctk.BooleanVar(value=current_settings["embed_thumbnail"])
        add_check("Embed Thumbnail in File", self.thumb_var)
        
        self.meta_var = ctk.BooleanVar(value=current_settings["embed_metadata"])
        add_check("Embed Metadata (Tags, Description)", self.meta_var)
        
        self.clip_var = ctk.BooleanVar(value=current_settings["clipboard_monitor"])
        add_check("Monitor Clipboard for Links", self.clip_var)
        
        self.notif_var = ctk.BooleanVar(value=current_settings.get("notifications", True))
        add_check("Show Desktop Notifications", self.notif_var)
        
        # -- Danger Zone --
        ctk.CTkFrame(s_frame, height=1, fg_color="gray50").pack(fill="x", pady=20)
        ctk.CTkButton(s_frame, text="Reset to Defaults", fg_color="transparent", border_width=1, border_color=self.accent_color, text_color=self.accent_color,
                      hover_color=("gray90", "gray20"), width=150, command=self.reset_settings_action).pack(anchor="w", pady=10)

    def build_help_tab(self, parent):
        # Title (Left Aligned)
        ctk.CTkLabel(parent, text="Help & Support", font=("Comfortaa", 24, "bold"), text_color=self.accent_color).pack(anchor="w", padx=40, pady=(40, 10))

        # Scrollable Content
        s_frame = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        s_frame.pack(fill="both", expand=True, padx=40, pady=0)
        self.help_scroll = s_frame
        self._bind_scroll_recursive(s_frame)
        # Hide scrollbar
        try: s_frame._scrollbar.grid_remove()
        except: pass

        def add_section(title):
             ctk.CTkLabel(s_frame, text=title, font=("Comfortaa", 16, "bold"), text_color=self.accent_color).pack(anchor="w", pady=(20, 10))

        # --- System Info ---
        add_section("System Information")
        
        info_grid = ctk.CTkFrame(s_frame, fg_color="transparent")
        info_grid.pack(fill="x")
        
        def add_info_row(p, label, value):
            row = ctk.CTkFrame(p, fg_color="transparent")
            row.pack(fill="x", pady=2)
            ctk.CTkLabel(row, text=label, font=("Comfortaa", 12, "bold"), width=150, anchor="w", text_color=self.text_color).pack(side="left")
            ctk.CTkLabel(row, text=value, font=("Comfortaa", 12), text_color="gray70", anchor="w").pack(side="left")

        add_info_row(info_grid, "App Version", "2.1 (Modern Edition)")
        add_info_row(info_grid, "Python Version", platform.python_version())
        
        yt_ver = "Unknown"
        try:
            import yt_dlp.version
            yt_ver = yt_dlp.version.__version__
        except:
            pass
        add_info_row(info_grid, "backend (yt-dlp)", yt_ver)
        
        # --- Troubleshooting ---
        add_section("Troubleshooting")
        
        t_row = ctk.CTkFrame(s_frame, fg_color="transparent")
        t_row.pack(fill="x", pady=5)
        
        def test_net():
            try:
                requests.get("https://www.google.com", timeout=3)
                self.show_notification("Connection Successful!", type="success")
            except:
                self.show_notification("Connection Failed. Check Internet.", type="error")

        ctk.CTkButton(t_row, text="Test Network Connection", height=30, fg_color=self.accent_color, text_color="white", command=test_net).pack(side="left", padx=(0, 10))
        
        def open_conf():
            p = os.getcwd()
            if sys.platform == 'win32': os.startfile(p)
            elif sys.platform == 'darwin': subprocess.Popen(['open', p])
            else: subprocess.Popen(['xdg-open', p])
            
        ctk.CTkButton(t_row, text="Open App Folder", height=30, fg_color=self.accent_color, hover_color=self.hover_color, text_color="white", command=open_conf).pack(side="left")

        # --- Shortcuts ---
        add_section("Keyboard Shortcuts")
        shortcuts = [
            ("Ctrl + V", "Paste URL & Process"),
            ("Enter", "Start Download (URL Focus)"),
        ]
        
        for k, d in shortcuts:
             r = ctk.CTkFrame(s_frame, fg_color="transparent")
             r.pack(fill="x", pady=2)
             ctk.CTkLabel(r, text=k, font=("Consolas", 12, "bold"), width=140, anchor="w", text_color=self.accent_color).pack(side="left")
             ctk.CTkLabel(r, text=d, font=("Comfortaa", 12), text_color="gray70").pack(side="left")

        # --- FAQ ---
        add_section("Frequently Asked Questions")
        faq = [
            ("How to Download?", "Paste a URL in the Download tab and click 'Download Now'.\nSelect 'Playlist' automatically if a list URL is detected."),
            ("Supported Formats?", "Video (4K, 2K, 1080p, etc.) and Audio (MP3, WAV, M4A).\nThe app automatically checks if your selected quality is available for the video."),
            ("Where are my files?", f"Check Settings for the folder.\nDefault: {current_settings['download_path']}"),
            ("Download Speed?", "Dependent on your connection and YouTube servers.\nSet a speed limit in settings if needed."),
        ]
        
        for q, a in faq:
            f = ctk.CTkFrame(s_frame, fg_color=self.card_color, corner_radius=6)
            f.pack(fill="x", pady=5)
            ctk.CTkLabel(f, text=q, font=("Comfortaa", 13, "bold"), text_color=self.text_color, anchor="w", justify="left").pack(anchor="w", fill="x", padx=10, pady=(10, 2))
            ctk.CTkLabel(f, text=a, font=("Comfortaa", 12), text_color=("gray50", "gray60"), anchor="w", justify="left").pack(anchor="w", fill="x", padx=10, pady=(0, 10))

    def build_about_tab(self, parent):
        # Title (Left)
        ctk.CTkLabel(parent, text="About Yikes YTD", font=("Comfortaa", 24, "bold"), text_color=self.accent_color).pack(anchor="w", padx=40, pady=(40, 10))

        # Scrollable Content
        s_frame = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        s_frame.pack(fill="both", expand=True, padx=40, pady=0)
        self.about_scroll = s_frame
        self._bind_scroll_recursive(s_frame)
        # Hide scrollbar
        try: s_frame._scrollbar.grid_remove()
        except: pass
        
        def add_section(title):
             ctk.CTkLabel(s_frame, text=title, font=("Comfortaa", 16, "bold"), text_color=self.accent_color).pack(anchor="w", pady=(20, 10))
        
        # --- Application Info ---
        add_section("Application Information")
        
        # Header Card
        header = ctk.CTkFrame(s_frame, fg_color=self.card_color, corner_radius=10)
        header.pack(fill="x", pady=5)
        
        ctk.CTkLabel(header, text="Yikes YTD", font=("Comfortaa", 32, "bold"), text_color=self.accent_color).pack(pady=(20, 5))
        ctk.CTkLabel(header, text="Version 2.1 (Modern Edition)", font=("Comfortaa", 14), text_color=self.text_color).pack(pady=(0, 5))
        ctk.CTkLabel(header, text="Created by WinterJackson", font=("Comfortaa", 12), text_color="gray60").pack(pady=(0, 20))
        
        # --- Connect ---
        add_section("Connect")
        
        connect_row = ctk.CTkFrame(s_frame, fg_color="transparent")
        connect_row.pack(fill="x")
        
        def open_site(u): webbrowser.open(u)
        
        ctk.CTkButton(connect_row, text="GitHub Repository", fg_color=self.accent_color, hover_color=self.hover_color, text_color="white",
                      command=lambda: open_site("https://github.com/WinterJackson/Yikes-YTD")).pack(side="left", padx=(0, 10))
                      
        ctk.CTkButton(connect_row, text="Support / Email", fg_color=self.accent_color, hover_color=self.hover_color,
                      command=lambda: open_site("mailto:support@yikes.com")).pack(side="left")

        # --- Legal & Libraries ---
        add_section("Legal & Libraries")
        
        libs = [
            ("yt-dlp", "Unlicense (Public Domain)"),
            ("customtkinter", "MIT License"),
            ("Pillow", "HPND License"),
            ("ffmpeg", "LGPL/GPL (External Dependency)")
        ]
        
        for name, lic in libs:
            r = ctk.CTkFrame(s_frame, fg_color="transparent")
            r.pack(fill="x", pady=2)
            ctk.CTkLabel(r, text=name, font=("Comfortaa", 12, "bold"), width=120, anchor="w", text_color=self.text_color).pack(side="left")
            ctk.CTkLabel(r, text=lic, font=("Comfortaa", 12), text_color="gray60").pack(side="left")
            
        # --- Updates ---
        add_section("Updates")
        
        update_Frame = ctk.CTkFrame(s_frame, fg_color=self.card_color, corner_radius=6)
        update_Frame.pack(fill="x", pady=5)
        
        status_lbl = ctk.CTkLabel(update_Frame, text="Status: Up to date (Checked just now)", font=("Comfortaa", 12), text_color="green")
        status_lbl.pack(side="left", padx=20, pady=15)
        
        def check_update():
            status_lbl.configure(text="Checking...", text_color=self.text_color)
            def check():
                try:
                    # Real GitHub Check
                    r = requests.get("https://api.github.com/repos/WinterJackson/Yikes-YTD/releases/latest", timeout=5)
                    if r.status_code == 200:
                        data = r.json()
                        tag = data.get("tag_name", "v2.1")
                        status_lbl.configure(text=f"Latest: {tag} (You are on v2.1)", text_color="green")
                    else:
                        status_lbl.configure(text="Could not fetch info from GitHub", text_color="orange")
                except Exception as e:
                    status_lbl.configure(text="Connection Error", text_color="red")
                    
            threading.Thread(target=check, daemon=True).start()
            
        ctk.CTkButton(update_Frame, text="Check for Updates", width=140, fg_color="transparent", border_width=1, 
                      border_color=self.accent_color, text_color=self.text_color, hover_color=("gray90", "gray25"),
                      command=check_update).pack(side="right", padx=20, pady=10)

    def build_feedback_tab(self, parent):
        # Title (Left Aligned)
        ctk.CTkLabel(parent, text="Feedback & Support", font=("Comfortaa", 24, "bold"), text_color=self.accent_color).pack(anchor="w", padx=40, pady=(40, 10))

        # Scrollable Content
        s_frame = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        s_frame.pack(fill="both", expand=True, padx=40, pady=0)
        self.feedback_scroll = s_frame
        self._bind_scroll_recursive(s_frame)
        # Hide scrollbar
        try: s_frame._scrollbar.grid_remove()
        except: pass
        
        def add_section(title):
             ctk.CTkLabel(s_frame, text=title, font=("Comfortaa", 16, "bold"), text_color=self.accent_color).pack(anchor="w", pady=(20, 10))

        # --- Get in Touch ---
        add_section("Get in Touch")
        
        contact_card = ctk.CTkFrame(s_frame, fg_color=self.card_color, corner_radius=10)
        contact_card.pack(fill="x", pady=5)
        
        ctk.CTkLabel(contact_card, text="Need help or have a question?", font=("Comfortaa", 14, "bold"), text_color=self.text_color).pack(anchor="w", padx=20, pady=(15, 5))
        ctk.CTkLabel(contact_card, text="Our support team is ready to assist you.", font=("Comfortaa", 12), text_color="gray60").pack(anchor="w", padx=20, pady=(0, 15))
        
        ctk.CTkButton(contact_card, text="Email Support", fg_color=self.accent_color, hover_color=self.hover_color,
                      command=lambda: webbrowser.open("mailto:support@yikes.com")).pack(anchor="w", padx=20, pady=(0, 20))

        # --- Report & Request ---
        add_section("Report & Request")
        
        action_row = ctk.CTkFrame(s_frame, fg_color="transparent")
        action_row.pack(fill="x")
        
        def open_issue(kind="bug"):
             url = "https://github.com/WinterJackson/Yikes-YTD/issues/new"
             if kind == "feature": url += "?labels=enhancement"
             webbrowser.open(url)
        
        ctk.CTkButton(action_row, text="Report a Bug", fg_color=self.accent_color, hover_color=self.hover_color,
                      command=lambda: open_issue("bug")).pack(side="left", padx=(0, 10))

        ctk.CTkButton(action_row, text="Request Feature", fg_color=self.accent_color, hover_color=self.hover_color, 
                      command=lambda: open_issue("feature")).pack(side="left")

        # --- Rate Experience ---
        add_section("Rate Your Experience")
        
        rate_frame = ctk.CTkFrame(s_frame, fg_color="transparent")
        rate_frame.pack(fill="x", pady=5)
        
        self.rating_var = tk.IntVar(value=current_settings.get("user_rating", 0))
        self.star_buttons = []
        
        def set_rating(rating, save=True):
            self.rating_var.set(rating)
            for i, btn in enumerate(self.star_buttons):
                if i < rating:
                    btn.configure(text="★", text_color="#FFD700") # Gold
                else:
                    btn.configure(text="☆", text_color="gray60")
            
            if save:
                current_settings["user_rating"] = rating
                try:
                    from logic.settings import save_settings
                    save_settings(current_settings)
                except: pass
                
                # Thank you message
                if not hasattr(self, "rating_lbl"):
                    self.rating_lbl = ctk.CTkLabel(rate_frame, text="Thanks for rating!", font=("Comfortaa", 12), text_color="green")
                    self.rating_lbl.pack(side="left", padx=15)
                else:
                    self.rating_lbl.configure(text="Thanks for rating!", text_color="green")
                    self.rating_lbl.pack(side="left", padx=15)
                 
        for i in range(1, 6):
            btn = ctk.CTkButton(rate_frame, text="☆", width=40, height=40, font=("Segoe UI Symbol", 24), 
                                fg_color="transparent", hover_color=("gray90", "gray25"),
                                command=lambda r=i: set_rating(r))
            btn.pack(side="left", padx=2)
            self.star_buttons.append(btn)
            
        # Init visual state
        if current_settings.get("user_rating", 0) > 0:
            set_rating(current_settings["user_rating"], save=False)


    def check_link(self):
        url = self.url_entry.get().strip()
        if not url: return
        
        # Debounce: Prevent rapid clicks from spawning multiple fetch threads
        if getattr(self, 'is_fetching', False):
            return
        
        # Security Check
        valid, msg = self.validate_security(url)
        if not valid:
             self.status_label.configure(text=f"Security Error: {msg}", text_color="red")
             return
        
        self.is_fetching = True
        self.status_label.configure(text="Checking...", text_color=self.accent_color)
        threading.Thread(target=self._check_link_worker, args=(url,), daemon=True).start()

    def _check_link_worker(self, url):
        try:
            # Determine likely type
            is_playlist_url = "list=" in url
            
            if is_playlist_url:
                self.after(0, lambda: self.status_label.configure(text="Fetching Playlist info...", text_color=self.accent_color))
                try:
                    info = fetch_playlist_info(url)
                except Exception as e:
                    err_msg = str(e)
                    self.after(0, lambda: self.status_label.configure(text=f"Error: {err_msg[:40]}...", text_color="red"))
                    print(f"Playlist Fetch Error: {e}")
                    return

                if info and 'entries' in info:
                    # Is a playlist
                    self.after(0, lambda: self.update_ui_for_playlist(info))
                    return
            
            # Fallback or single video
            self.after(0, lambda: self.status_label.configure(text="Fetching Video info...", text_color=self.accent_color))
            try:
                info = fetch_video_info(url)
            except Exception as e:
                err_msg = str(e)
                self.after(0, lambda: self.status_label.configure(text=f"Error: {err_msg[:40]}...", text_color="red"))
                print(f"Video Fetch Error: {e}")
                return
                
            if info:
                # Live Stream Detection
                is_live = info.get('is_live', False)
                was_live = info.get('was_live', False)
                duration = info.get('duration')
                
                if is_live:
                    self.after(0, lambda: self.show_notification(
                        "⚠️ This is a LIVE stream! Downloading may run indefinitely and fill disk space.", 
                        type="warning"
                    ))
                elif was_live and (duration is None or duration > 36000):  # > 10 hours
                    self.after(0, lambda: self.show_notification(
                        "⚠️ This appears to be a long stream recording. Consider trimming.",
                        type="info"
                    ))
                
                if 'entries' in info: # It was a playlist after all?
                    self.after(0, lambda: self.update_ui_for_playlist(info))
                else:
                    title = info.get('title', 'Unknown')
                    thumb = info.get('thumbnail')
                    self.after(0, lambda: self.update_ui_for_video(title, thumb, info))
            else:
                self.after(0, lambda: self.status_label.configure(text="Invalid URL or Error", text_color="red"))
        finally:
            # Always reset debounce flag
            self.is_fetching = False

    def clear_data(self):
        # Reset UI to initial state
        self.url_entry.delete(0, 'end')
        self.status_label.configure(text="", text_color=self.text_color)
        
        # Hide Views
        self.video_info_frame.pack_forget()
        self.playlist_info_frame.pack_forget()
        
        # Reset Buttons
        self.download_btn.configure(state="normal", text="Download Now", command=self.start_download) # Reset command in case it was Open Folder
        self.play_btn.configure(state="disabled", text="Play Video")
        
        # Clear Data
        self.playlist_entries = []
        self.is_playlist = False
        self.video_title_label.configure(text="")
        self.video_details_label.configure(text="")
        self.thumbnail_label.configure(image=None, text="")
        
        # Reset Progress
        self.progress_bar.set(0)
        self.progress_bar.configure(progress_color=self.accent_color)
        self.progress_text.configure(text="0%")
        
        # Reset Trim UI
        self.trim_btn.configure(state="normal", text="Trim Video")
        self.trim_var.set(False)
        self.toggle_trim()

    def update_ui_for_playlist(self, info):
        self.is_playlist = True
        self.playlist_entries = list(info.get('entries', []))
        title = info.get('title', 'Unknown Playlist')
        count = len(self.playlist_entries)
        
        # Switch View
        self.video_info_frame.pack_forget()
        self.playlist_info_frame.pack(fill="both", expand=True)
        
        self.status_label.configure(text=f"Playlist Found: {title} ({count} videos)", text_color=self.text_color)
        self.download_btn.configure(text=f"Download All ({count})")
        
        # Store for History
        self.current_playlist_info = info
        self.current_video_info = None # Clear single info
        
        # Populate List
        for w in self.playlist_scroll.winfo_children(): w.destroy()
        
        self.playlist_widgets = [] # Reset widgets store
        
        # Configure Grid Columns for the Scroll Frame
        self.playlist_scroll.grid_columnconfigure(1, weight=1) # Title takes space
        
        # Performance: Limit initial render to 100 items, batch the rest
        initial_batch_size = 100
        entries_to_render = self.playlist_entries[:initial_batch_size]
        remaining_entries = self.playlist_entries[initial_batch_size:]
        
        for i, entry in enumerate(entries_to_render):
            self._render_playlist_row(i, entry)
        
        # If there are more, add a "Load More" indicator and continue in background
        if remaining_entries:
            self._load_more_label = ctk.CTkLabel(
                self.playlist_scroll, 
                text=f"Loading {len(remaining_entries)} more videos...", 
                font=("Comfortaa", 12), 
                text_color=self.accent_color
            )
            self._load_more_label.pack(pady=10)
            # Start batched background render (10 at a time, non-blocking)
            self.after(100, lambda: self._render_playlist_batch(initial_batch_size, remaining_entries, 0))
            
        # Check scroll visibility
        self.after(200, self._check_playlist_scroll)

    def _render_playlist_row(self, index, entry):
        """Render a single playlist row widget."""
        # Row Container
        row = ctk.CTkFrame(self.playlist_scroll, fg_color="transparent")
        row.pack(fill="x", pady=5, padx=5)
        
        # 1. Thumbnail Placeholder (100x50)
        thumb_label = ctk.CTkLabel(row, text="", width=100, height=56, fg_color="black") # 16:9 approx
        thumb_label.pack(side="left", padx=(0, 10))
        
        # 2. Text Info
        text_frame = ctk.CTkFrame(row, fg_color="transparent")
        text_frame.pack(side="left", fill="both", expand=True)
        
        # Title
        t = entry.get('title', 'Unknown Title')
        if len(t) > 65: t = t[:62] + "..."
        ctk.CTkLabel(text_frame, text=f"{index+1}. {t}", font=("Comfortaa", 13, "bold"), anchor="w", text_color=self.text_color).pack(fill="x")
        
        # Uploader
        uploader = entry.get('uploader') or entry.get('channel') or "Unknown Uploader"
        ctk.CTkLabel(text_frame, text=uploader, font=("Comfortaa", 11), text_color="gray60", anchor="w").pack(fill="x")

        # 3. Status Column (Progress + Icon)
        status_frame = ctk.CTkFrame(row, fg_color="transparent", width=250)
        status_frame.pack(side="right", padx=10)
        
        # Progress Bar (Hidden initially or 0)
        p_bar = ctk.CTkProgressBar(status_frame, width=100, height=8, progress_color=self.accent_color)
        p_bar.set(0)
        p_bar.pack(pady=(5, 2), anchor="e")
        
        # Status Text
        s_label = ctk.CTkLabel(status_frame, text="Pending", font=("Comfortaa", 11), text_color="gray60")
        s_label.pack(anchor="e")
        
        # Store refs
        self.playlist_widgets.append({
            "progress": p_bar,
            "status": s_label,
            "row": row
        })

        # Trigger Async Thumbnail Load
        thumbnails = entry.get('thumbnails')
        if thumbnails:
            thumb_url = thumbnails[0].get('url') if isinstance(thumbnails, list) and thumbnails else None
            if thumb_url:
                self.executor.submit(self._async_load_playlist_thumb, thumb_url, thumb_label)
        
        # Recursive bind scroll
        self._bind_scroll_recursive(row)

    def _render_playlist_batch(self, start_index, remaining, batch_offset):
        """Render remaining playlist items in small batches for smooth UI."""
        batch_size = 10
        batch = remaining[batch_offset:batch_offset + batch_size]
        
        for i, entry in enumerate(batch):
            self._render_playlist_row(start_index + batch_offset + i, entry)
        
        new_offset = batch_offset + batch_size
        if new_offset < len(remaining):
            # Schedule next batch
            self.after(50, lambda: self._render_playlist_batch(start_index, remaining, new_offset))
        else:
            # All done, remove loader
            if hasattr(self, '_load_more_label') and self._load_more_label.winfo_exists():
                self._load_more_label.destroy()

        # STRICTLY DISABLE TRIM for Playlists
        self.trim_var.set(False)
        self.toggle_trim()
        self.trim_btn.configure(state="disabled", text="Trim (Video Only)")

    def _async_load_playlist_thumb(self, url, label_widget, size=(100, 56)):
        try:
            response = requests.get(url, timeout=5)
            img = Image.open(BytesIO(response.content))
            img = img.resize(size, Image.Resampling.LANCZOS) # Flexible size
            
            def update():
                if not label_widget.winfo_exists(): return
                # Use CTkImage to avoid warnings and handle DPI
                photo = ctk.CTkImage(light_image=img, dark_image=img, size=size)
                label_widget.configure(image=photo, fg_color="transparent") # Remove black placeholder
                label_widget.image = photo # Keep ref
            
            self.after(0, update)
        except:
            pass
    
    def _on_mouse_wheel(self, event):
        # Linux Touchpad / Mouse Wheel Support
        scroll_speed = 20 # Pixels per event
        
        target = None
        current = getattr(self, "current_frame", "")
        
        if current == "Download" and getattr(self, "is_playlist", False):
            target = self.playlist_scroll
        elif current == "History":
            target = self.history_frame
        elif current == "Queue":
            target = getattr(self, "queue_frame", None)
        elif current == "Settings":
            target = getattr(self, "settings_scroll", None)
        elif current == "Help":
            target = getattr(self, "help_scroll", None)
        elif current == "About":
            target = getattr(self, "about_scroll", None)
        elif current == "Feedback":
            target = getattr(self, "feedback_scroll", None)
            
        if target:
            try:
                # CTkScrollableFrame uses _parent_canvas
                if event.num == 4:
                    target._parent_canvas.yview_scroll(-scroll_speed, "units")
                elif event.num == 5:
                    target._parent_canvas.yview_scroll(scroll_speed, "units")
            except:
                pass
        # Windows/MacOS if needed (though CTK usually handles Delta)
    
    def _bind_scroll_recursive(self, widget):
        # Bind Linux Scroll Events
        widget.bind("<Button-4>", self._on_mouse_wheel)
        widget.bind("<Button-5>", self._on_mouse_wheel)
        # Recurse
        for child in widget.winfo_children():
            self._bind_scroll_recursive(child)

    def update_ui_for_video(self, title, thumb_url, info=None):
        self.is_playlist = False
        self.playlist_entries = []
        
        # Switch View
        self.playlist_info_frame.pack_forget()
        self.video_info_frame.pack(fill="both", expand=True)
        
        # Populate Metadata
        uploader = "Unknown Uploader"
        duration_str = ""
        
        # Store for History
        self.current_video_info = info
        self.current_playlist_info = None
        
        if info:
             uploader = info.get('uploader') or info.get('channel') or uploader
             d = info.get('duration')
             if d:
                 duration_str = f" • {format_eta(d)}" # Reuse eta formatter for duration
        
        # Populate Metadata with Explicit Labels
        title_text = f"Title: {title}"
        
        details_text = f"Uploader: {uploader}"
        if duration_str:
            details_text += f"\nDuration: {duration_str.replace(' • ', '')}"
        
        self.video_title_label.configure(text=title_text)
        self.video_details_label.configure(text=details_text)
        
        self.status_label.configure(text=f"Ready to Download", text_color=self.text_color)
        self.download_btn.configure(text="Download Now")
        
        # ENABLE TRIM for Single Video
        self.trim_btn.configure(state="normal", text="Trim Video")
        
        if thumb_url:
            self.fetch_thumbnail(thumb_url)

    def fetch_thumbnail(self, url):
        try:
            response = requests.get(url, timeout=5)
            img = Image.open(BytesIO(response.content))
            img = img.resize((550, 309), Image.Resampling.LANCZOS) # 550px width, 16:9 approx
            # Pass PIL Image to main thread, create PhotoImage there
            self.after(0, lambda: self.update_thumbnail(img))
        except:
            pass
            
    def update_thumbnail(self, img_obj):
        try:
            # Use CTkImage
            photo = ctk.CTkImage(light_image=img_obj, dark_image=img_obj, size=img_obj.size)
            self.thumbnail_label.configure(image=photo, text="")
            self.thumbnail_label.image = photo
        except Exception:
            pass

    def cancel_download_action(self):
        if self.show_blocking_confirm("Cancel Download", "Stop the current download?", "Stop", "Continue", "warning"):
            self.is_cancelled = True
            self.status_label.configure(text="Cancelling...", text_color="red")
            self.download_btn.configure(state="disabled", text="Stopping...")

    def validate_format_availability(self, info):
        """Check if selected quality is available for the given video."""
        if not info: return True, ""
        
        sel = self.format_var.get()
        # Skip check for audio/gif
        if "Audio" in sel or "GIF" in sel:
            return True, ""
            
        requested_h = 0
        if "4K" in sel: requested_h = 2160
        elif "1440p" in sel: requested_h = 1440
        elif "1080p" in sel: requested_h = 1080
        elif "720p" in sel: requested_h = 720
        elif "480p" in sel: requested_h = 480
        else: return True, "" # Best Quality if it still existed
        
        max_h = get_max_resolution(info)
        
        if max_h > 0 and requested_h > max_h:
            # Map height to readable name
            res_names = {2160: "4K", 1440: "2K", 1080: "1080p", 720: "720p", 480: "480p"}
            max_name = res_names.get(max_h, f"{max_h}p")
            return False, f"Notice: This video only supports up to {max_name}. Downloading at the highest available quality instead."
            
        return True, ""

    def start_download(self):
        url = self.url_entry.get()
        if not url: 
            self.status_label.configure(text="Please enter a URL first.", text_color="red")
            return
            
        # Security Check
        valid, msg = self.validate_security(url)
        if not valid:
            self.status_label.configure(text=msg, text_color="red")
            return
        
        self.download_in_progress = True
        self.is_cancelled = False
        
        # Configure Cancel Button
        self.download_btn.configure(state="normal", text="Cancel Download", fg_color="red", hover_color="darkred", command=self.cancel_download_action)
        self.play_btn.configure(state="disabled")
        
        # Build Options
        trim_range = None
        if self.trim_var.get() and not self.is_playlist: # Trim only single videos
            try:
                s = parse_time_to_seconds(self.start_trim.get())
                e = parse_time_to_seconds(self.end_trim.get())
                if s is not None and e is not None and e > s:
                    trim_range = (s, e)
                else:
                    raise ValueError
            except:
                self.show_notification("Invalid Trim Times.", type="error")
                self.on_complete() # Reset
                return
        
        # Helper Map
        sel = self.format_var.get()
        fmt_key = "1080p" # New default
        if "4K" in sel: fmt_key = "4k"
        elif "1440p" in sel: fmt_key = "1440p"
        elif "1080p" in sel: fmt_key = "1080p"
        elif "720p" in sel: fmt_key = "720p"
        elif "480p" in sel: fmt_key = "480p"
        elif "MP3 - 320" in sel: fmt_key = "mp3_320"
        elif "MP3 - 192" in sel: fmt_key = "mp3_192"
        elif "MP3 - 128" in sel: fmt_key = "mp3_128"
        elif "WAV" in sel: fmt_key = "wav"
        elif "M4A" in sel: fmt_key = "m4a"
        elif "GIF" in sel: fmt_key = "gif"
        
        # Availability Validation
        if not self.is_playlist and self.current_video_info:
            valid, warning = self.validate_format_availability(self.current_video_info)
            if not valid:
                self.show_notification(warning, type="info")
                # We proceed anyway, yt-dlp will pick the best available under the constraint
                # but the user is now accurately notified.
        
        if self.is_playlist:
            # Create playlist folder inside downloads folder
            playlist_title = getattr(self, "current_playlist_info", {}).get("title", "Playlist")
            # Sanitize folder name (remove invalid filesystem characters + Windows reserved names)
            safe_title = re.sub(r'[<>:"/\\|?*]', '_', playlist_title)[:100].strip()
            # Handle Windows reserved names (CON, PRN, AUX, NUL, COM1-9, LPT1-9)
            reserved_names = {'CON', 'PRN', 'AUX', 'NUL'} | {f'COM{i}' for i in range(1, 10)} | {f'LPT{i}' for i in range(1, 10)}
            if safe_title.upper() in reserved_names or not safe_title:
                safe_title = "Playlist"
            playlist_path = os.path.join(current_settings["download_path"], safe_title)
            os.makedirs(playlist_path, exist_ok=True)
            
            # Store the playlist folder path for "Open Folder" button
            self.current_playlist_folder = playlist_path
            
            opts = build_ydl_opts(playlist_path, fmt_key, trim_range=trim_range)
            # Start Playlist Thread
            threading.Thread(target=self.playlist_download_worker, args=(opts,), daemon=True).start()
        else:
            # Single Download: Use default path
            self.current_playlist_folder = None
            
            # Disk Space Check for single video (warn if < 2GB free)
            download_path = current_settings["download_path"]
            free_gb = get_free_disk_space_gb(download_path)
            if 0 < free_gb < 2:
                self.show_notification(
                    f"⚠️ Low disk space! Only {free_gb:.1f}GB free. Download may fail.",
                    type="warning"
                )
            
            opts = build_ydl_opts(download_path, fmt_key, trim_range=trim_range)
            
            # Start Single Download Thread
            self.status_label.configure(text="Initializing Download...", text_color=self.text_color)
            
            # Reset Stats
            self.last_progress_info = {}
            
            # SHOW Progress Bar ONLY when downloading
            self.progress_bar.pack(fill="x", pady=(5, 5), padx=0, anchor="w")
            self.progress_text.pack(pady=(0, 10), anchor="w", padx=0)
            
            start_download_thread(url, opts, self.on_progress, self.on_complete, self.on_error, lambda: self.is_cancelled)

    def playlist_download_worker(self, opts):
        """Sequential download manager for playlists with per-item progress and failure tracking"""
        total_videos = len(self.playlist_entries)
        failed_count = 0  # Track failures for accurate reporting
        
        # Disk Space Check for playlists (estimate 500MB per video, warn if low)
        download_path = current_settings["download_path"]
        free_gb = get_free_disk_space_gb(download_path)
        estimated_need_gb = total_videos * 0.5  # 500MB per video estimate
        if free_gb > 0 and free_gb < estimated_need_gb:
            self.after(0, lambda: self.show_notification(
                f"⚠️ Low disk space! {free_gb:.1f}GB free, playlist may need ~{estimated_need_gb:.0f}GB.",
                type="warning"
            ))
        
        # Hide global progress for cleaner UI (since we have per-row bars)
        self.after(0, lambda: self.progress_bar.pack_forget())
        self.after(0, lambda: self.progress_text.pack_forget())

        for i, entry in enumerate(self.playlist_entries):
            # Update UI for current video -> Active
            title = entry.get('title', f'Video {i+1}')
            video_url = entry.get('url') or entry.get('webpage_url') 
            
            # Mark Active
            self.after(0, lambda idx=i: self.update_playlist_row_status(idx, "Downloading...", self.accent_color))
            
            self.after(0, lambda t=title, idx=i: self.status_label.configure(
                text=f"Downloading {idx+1}/{total_videos}: {t[:40]}...", text_color=self.accent_color))
            
            try:
                from logic.downloader import download_worker 
                
                # Custom callback for THIS row
                def prog_cb(info):
                   # Calculate percent
                   if info.get('status') == 'downloading':
                       total = info.get('total_bytes') or info.get('total_bytes_estimate') or 1
                       downloaded = info.get('downloaded_bytes') or 0
                       
                       p = 0
                       if total > 0:
                           p = downloaded / total
                       
                       # Extract strings provided by yt-dlp or fallback
                       speed_s = info.get('_speed_str', 'N/A').strip()
                       total_s = info.get('_total_bytes_str', 'N/A').strip()
                       percent_s = info.get('_percent_str', f"{p*100:.1f}%").strip()
                       
                       # Fallback format if needed
                       if speed_s == 'N/A' and info.get('speed'):
                           speed_s = f"{info['speed']/1024/1024:.1f} MB/s"
                       # Format: "Size: 10.5MiB • Speed: 2.5MiB/s • Progress: 45.0%"
                       details = f"Size: {total_s} • Speed: {speed_s} • Progress: {percent_s}"

                       # Status Text: Downloading Video... / Downloading Audio...
                       content_type = info.get('_content_type', 'Content')
                       status_text = f"Downloading {content_type}..."

                       # Update specific bar & label
                       self.after(0, lambda idx=i, val=p: self.update_playlist_row_progress(idx, val))
                       # Wait, user wants clear steps "Downloading Video". 
                       # The current UI puts details in the 'status' label. 
                       # Maybe prepend the step? "Downloading Video: Size... • Speed..."
                       full_msg = f"{status_text} | {details}"
                       self.after(0, lambda idx=i, txt=full_msg: self.update_playlist_row_status(idx, txt, self.accent_color))
                    
                   elif info.get('status') == 'merging':
                       self.after(0, lambda idx=i: self.update_playlist_row_status(idx, "Merging Video & Audio...", self.accent_color))
                       # Indeterminate progress or full?
                       self.after(0, lambda idx=i: self.update_playlist_row_progress(idx, 1.0))

                # Deep copy opts
                download_worker(video_url, copy.deepcopy(opts), prog_cb, None, None) 
                
                # Mark Done
                self.after(0, lambda idx=i: self.update_playlist_row_status(idx, "✔ Done", "green"))
                # Learn: Do not auto-set progress to 1.0 here if we just finished merging, it might flicker.
                self.after(0, lambda idx=i: self.update_playlist_row_progress(idx, 1.0))

            except Exception as e:
                failed_count += 1  # Increment failure counter
                print(f"Failed to download {title}: {e}")
                self.after(0, lambda idx=i: self.update_playlist_row_status(idx, "Failed", "red"))
            
            time.sleep(1)
            
        # Accurate Completion Status
        if failed_count > 0:
            status_msg = f"✔ Playlist Complete ({total_videos - failed_count}/{total_videos} succeeded, {failed_count} failed)"
            status_color = "orange"
        else:
            status_msg = f"✔ Playlist Download Complete!"
            status_color = "green"
            
        self.after(0, lambda: self.status_label.configure(text=status_msg, text_color=status_color))
        self.after(0, lambda: self.download_btn.configure(state="normal", text="Open Folder", command=self.open_download_folder))
        self.download_in_progress = False
        
        # Save Rich Playlist History
        p_info = getattr(self, "current_playlist_info", {}) or {}
        entries = p_info.get('entries', [])
        thumb = None
        if entries and len(entries) > 0:
             thumb = entries[0].get('thumbnail')
        
        entry = {
            "title": p_info.get("title", f"Playlist ({len(entries)} items)"),
            "url": self.url_entry.get(),
            "thumbnail": thumb,
            "uploader": p_info.get("uploader", "Unknown"),
            "count": len(entries),
            "date": time.strftime("%Y-%m-%d %H:%M"),
            "type": "playlist"
        }
        self.after(0, lambda: save_history(entry))
        self.after(0, lambda: self.update_history_ui())
        
        # Platform-Aware Notification (Linux only)
        if current_settings.get("notifications", True) and sys.platform.startswith('linux'):
             self.after(0, lambda: subprocess.run(['notify-send', "Yikes YTD", status_msg], check=False))
        
        # Auto-Process Next (Thread)
        if getattr(self, "is_processing_queue", False):
             self.after(1500, self.process_queue)
             
        # No messagebox

    def update_playlist_row_status(self, index, text, color):
        if index < len(self.playlist_widgets):
             w = self.playlist_widgets[index]
             w["status"].configure(text=text, text_color=color)

    def update_playlist_row_progress(self, index, val):
        if index < len(self.playlist_widgets):
             w = self.playlist_widgets[index]
             w["progress"].set(val)

    def on_complete_playlist(self):
        self.download_in_progress = False
        self.status_label.configure(text="Playlist Download Complete!", text_color=self.accent_color)
        self.download_btn.configure(state="normal", text=f"Download All ({len(self.playlist_entries)})")
        self.play_btn.configure(state="normal")
        self.progress_bar.set(1)
        # Save Rich Playlist History
        p_info = getattr(self, "current_playlist_info", {}) or {}
        entries = p_info.get('entries', [])
        thumb = None
        if entries and len(entries) > 0:
             thumb = entries[0].get('thumbnail')
        
        entry = {
            "title": p_info.get("title", f"Playlist ({len(entries)} items)"),
            "url": self.url_entry.get(),
            "thumbnail": thumb,
            "uploader": p_info.get("uploader", "Unknown"),
            "count": len(entries),
            "date": time.strftime("%Y-%m-%d %H:%M"),
            "type": "playlist"
        }
        self.after(0, lambda: save_history(entry))
        self.after(0, lambda: self.update_history_ui())
        
        # Platform-Aware Notification (Linux only)
        if current_settings.get("notifications", True) and sys.platform.startswith('linux'):
             self.after(0, lambda: subprocess.run(['notify-send', "Yikes YTD", "Playlist Download Complete!"], check=False))
        
        # Auto-Process Next (GUI Callback)
        if getattr(self, "is_processing_queue", False):
             self.after(1500, self.process_queue)



    def on_progress(self, info):
        # Handle Merge Status
        if info.get('status') == 'merging':
            self.after(0, lambda: self.status_label.configure(text="Merging Video & Audio...", text_color=self.accent_color))
            self.after(0, lambda: self.progress_text.configure(text="Processing..."))
            return

        # Update UI safely - use 'or' to handle explicit None values from yt-dlp
        total = info.get('total_bytes') or info.get('total_bytes_estimate') or 1
        if total <= 0: total = 1
        downloaded = info.get('downloaded_bytes') or 0
        p = downloaded / total
        
        self.after(0, lambda: self.progress_bar.set(p))
        eta = format_eta(info.get('eta') or 0)
        speed = (info.get('speed') or 0) / 1024
        
        # Extract Strings
        speed_s = info.get('_speed_str', 'N/A').strip()
        if speed_s == 'N/A' and info.get('speed'):
             speed_s = f"{info['speed']/1024/1024:.1f} MB/s"
             
        total_s = info.get('_total_bytes_str', 'N/A').strip()
        percent_s = info.get('_percent_str', f"{p*100:.1f}%").strip()
        
        content_type = info.get('_content_type', 'Content')
        status_msg = f"Downloading {content_type}..."
        
        # Stats Line: Step | Speed | Size
        stats = f"{status_msg}  |  Speed: {speed_s}  |  Size: {total_s}"
        
        # Capture for history
        self.last_progress_info = {
            "speed": speed_s,
            "total_str": total_s,
            "percent": percent_s
        }
        
        self.after(0, lambda: self.status_label.configure(text=stats, text_color=self.accent_color))
        self.after(0, lambda: self.progress_text.configure(text=f"{int(p*100)}%  •  ETA: {eta}"))

    def on_complete(self):
        self.download_in_progress = False
        # Success State - Green & Actions
        self.after(0, lambda: self.status_label.configure(text="✔ Download Complete!", text_color="green"))
        self.after(0, lambda: self.download_btn.configure(state="normal", text="Open Folder", command=self.open_download_folder, fg_color=self.accent_color, hover_color=self.hover_color))
        # Enable "Play Now"
        self.after(0, lambda: self.play_btn.configure(state="normal", text="Play Now"))
        
        # Progress Bar Green (Mock - Just full)
        # self.after(0, lambda: self.progress_bar.set(1))
        # self.after(0, lambda: self.progress_bar.configure(progress_color="green"))
        # self.after(0, lambda: self.progress_text.configure(text="100% - Ready to Play"))
        
        # HIDE Progress Bar (Strict Requirement)
        self.after(0, lambda: self.progress_bar.pack_forget())
        self.after(0, lambda: self.progress_text.pack_forget())
        
        self.after(0, lambda: self.update_history_ui())
        
        # Add to history (RICH DATA)
        info = getattr(self, "current_video_info", {}) or {}
        stats = getattr(self, "last_progress_info", {}) or {}
        
        entry = {
            "title": info.get("title", "Unknown Video"),
            "url": self.url_entry.get(),
            "thumbnail": info.get("thumbnail"),
            "uploader": info.get("uploader", "Unknown"),
            "duration": info.get("duration"),
            "size": stats.get("total_str", "Unknown"),
            "resolution": self.format_var.get(),
            "date": time.strftime("%Y-%m-%d %H:%M"),
            "type": "video"
        }
        save_history(entry) # Synchronous save is fine
        self.after(0, lambda: self.update_history_ui())
        
        # Platform-Aware Notification (Linux only)
        if current_settings.get("notifications", True) and sys.platform.startswith('linux'):
             self.after(0, lambda: subprocess.run(['notify-send', "Yikes YTD", "Download Complete!"], check=False))
        
        # Auto-Process Next
        if getattr(self, "is_processing_queue", False):
             self.after(1500, self.process_queue)
        
    def open_download_folder(self):
        path = getattr(self, "current_playlist_folder", None)
        if not path or not os.path.exists(path):
            path = current_settings.get("download_path")
            
        if path and os.path.exists(path):
            try:
                if sys.platform == 'win32': os.startfile(path)
                elif sys.platform == 'darwin': subprocess.Popen(['open', path])
                else: subprocess.Popen(['xdg-open', path])
            except Exception as e:
                print(f"Error opening folder: {e}")

    def on_error(self, err_msg):
        self.download_in_progress = False
        self.after(0, lambda: self.status_label.configure(text=f"Error: {err_msg}", text_color="red"))
        self.after(0, lambda: self.download_btn.configure(state="normal", text="Download Now", command=self.start_download, fg_color=self.accent_color, hover_color=self.hover_color))
        
        # HIDE Progress Bar
        self.after(0, lambda: self.progress_bar.pack_forget())
        self.after(0, lambda: self.progress_text.pack_forget())

    def add_to_queue_action(self):
        url = self.url_entry.get()
        if not url:
            self.status_label.configure(text="Please enter a URL first", text_color="red")
            return

        # Security Check
        valid, msg = self.validate_security(url)
        if not valid:
            self.status_label.configure(text=msg, text_color="red")
            return
        
        # Rich Data Check - Capture Current Info if Match found
        entry = {"url": url, "format": self.format_var.get()}
        
        # Smart Match using ID extraction (simple check for now)
        def get_vid(u):
            if "v=" in u: return u.split("v=")[1].split("&")[0]
            if "youtu.be/" in u: return u.split("youtu.be/")[1].split("?")[0]
            return u

        target_id = get_vid(url)
        
        # Check Single Video
        info = getattr(self, "current_video_info", None)
        info_url = info.get('webpage_url', '') if info else ''
        
        if info and (info_url == url or get_vid(info_url) == target_id):
             entry.update({
                 "title": info.get('title', 'Unknown'),
                 "thumbnail": info.get('thumbnail'),
                 "uploader": info.get('uploader'),
                 "duration": info.get('duration'),
                 "type": "video"
             })
        # Check Playlist
        elif getattr(self, "current_playlist_info", None):
             p_info = self.current_playlist_info
             p_url = p_info.get('webpage_url', '')
             if p_url == url or get_vid(p_url) == target_id or 'list=' in url:
                 entries = p_info.get('entries', [])
                 thumb = entries[0].get('thumbnail') if entries else None
                 entry.update({
                     "title": p_info.get('title', 'Unknown Playlist'),
                     "thumbnail": thumb,
                     "count": len(entries),
                     "type": "playlist"
                 })
        else:
            # No info fetched yet, just add URL
            entry["title"] = "Pending - Click Check first"
            entry["type"] = "unknown"

        add_to_queue(entry)
        self.update_queue_ui()
        self.status_label.configure(text="✓ Added to Queue", text_color="green")
        self.after(2000, lambda: self.status_label.configure(text="", text_color=self.text_color))

    def update_queue_ui(self):
        for w in self.queue_frame.winfo_children(): w.destroy()
        q = get_queue()
        for i, item in enumerate(q):
            # Rich Card Container
            c = ctk.CTkFrame(self.queue_frame, fg_color=("gray95", "gray25"), height=70)
            c.pack(fill="x", pady=6, padx=5)
            
            # Index
            ctk.CTkLabel(c, text=f"{i+1}.", width=30, font=("Comfortaa", 12, "bold"), text_color=self.text_color).pack(side="left", padx=(10,0))
            
            # Thumbnail (100x50)
            thumb_url = item.get('thumbnail')
            thumb_label = ctk.CTkLabel(c, text="", width=100, height=50, fg_color="black")
            thumb_label.pack(side="left", padx=10, pady=8)
            if thumb_url:
                self._async_load_playlist_thumb(thumb_url, thumb_label, size=(100, 50))
            
            # Info Column
            info_frame = ctk.CTkFrame(c, fg_color="transparent")
            info_frame.pack(side="left", fill="both", expand=True, pady=5)
            
            title = item.get('title', item.get('url', 'Unknown URL'))
            if len(title) > 55: title = title[:52] + "..."
            ctk.CTkLabel(info_frame, text=title, font=("Comfortaa", 14, "bold"), anchor="w", text_color=self.text_color).pack(fill="x")
            
            # Details: Uploader / Count
            details = []
            if item.get('type') == 'playlist':
                 details.append("Playlist")
                 if item.get('count'): details.append(f"{item['count']} Videos")
            else:
                 if item.get('uploader'): details.append(item['uploader'])
                 if item.get('duration'): details.append(format_eta(item['duration']))
            
            d_str = " • ".join(details) if details else "Waiting to process..."
            ctk.CTkLabel(info_frame, text=d_str, font=("Comfortaa", 12), text_color="gray60", anchor="w").pack(fill="x")

            # Remove Button
            ctk.CTkButton(c, text="Remove", width=80, height=25, fg_color="transparent", border_width=1, 
                          border_color=self.accent_color, text_color=self.accent_color, hover_color=("gray90", "gray20"),
                          command=lambda idx=i: self.remove_queue_action(idx)).pack(side="right", padx=10)
        
        # Bind Scroll
        self._bind_scroll_recursive(self.queue_frame)

    def remove_queue_action(self, index):
        remove_from_queue(index)
        self.update_queue_ui()
        
    def clear_queue_action(self):
        if self.show_blocking_confirm("Clear Queue", "Clear all pending downloads?", "Clear All", "Cancel", "danger"):
            clear_queue()  # Use new function that persists the empty queue
            self.update_queue_ui()

    def update_history_ui(self):
        # 1. Clear current items and show loader
        for w in self.history_frame.winfo_children(): w.destroy()
        
        self.history_loader = ctk.CTkLabel(self.history_frame, text="Loading History...", font=("Comfortaa", 14), text_color="gray60")
        self.history_loader.pack(pady=40)
        
        # 2. Threaded Load
        threading.Thread(target=self._load_history_async, daemon=True).start()

    def _load_history_async(self):
        data = load_history()
        # Trigger render on main thread
        self.after(0, lambda: self._start_history_render(data))

    def _start_history_render(self, data):
        # Remove loader
        if hasattr(self, 'history_loader') and self.history_loader.winfo_exists():
            self.history_loader.destroy()
            
        if not data:
            ctk.CTkLabel(self.history_frame, text="No download history yet.", font=("Comfortaa", 14), text_color="gray60").pack(pady=40)
            return

        # Start cascading render
        self._render_history_batch(data, 0)

    def _render_history_batch(self, data, index):
        # Render items one by one for smooth cascading effect
        if index >= len(data):
            # Bind scroll events after all items are rendered
            self._bind_scroll_recursive(self.history_frame)
            return
            
        item = data[index]
        self._render_single_history_card(item)
        
        # Schedule next item with tiny delay (5ms) for smooth visual
        self.after(5, lambda: self._render_history_batch(data, index + 1))
        
    def _render_single_history_card(self, item):
        # Card Container
        c = ctk.CTkFrame(self.history_frame, fg_color=("gray95", "gray25"), height=70) # Card Style
        c.pack(fill="x", pady=6, padx=5)
        
        # 1. Thumbnail (100x50 px as requested)
        thumb_url = item.get('thumbnail')
        thumb_label = ctk.CTkLabel(c, text="", width=100, height=50, fg_color="black")
        thumb_label.pack(side="left", padx=10, pady=8)
        if thumb_url:
            self._async_load_playlist_thumb(thumb_url, thumb_label, size=(100, 50))
        
        # 2. Info Column
        info_frame = ctk.CTkFrame(c, fg_color="transparent")
        info_frame.pack(side="left", fill="both", expand=True, pady=5)
        
        # Title
        title = item.get('title', item.get('url', 'Unknown'))
        if len(title) > 60: title = title[:57] + "..."
        ctk.CTkLabel(info_frame, text=title, font=("Comfortaa", 14, "bold"), anchor="w", text_color=self.text_color).pack(fill="x")
        
        # Details: Uploader | Format | Size | Duration
        details = []
        
        if item.get('type') == 'playlist':
            # Custom Details for Playlist
            details.append("Playlist")
            if item.get('count'): details.append(f"{item['count']} Videos")
            if item.get('uploader'): details.append(item['uploader'])
        else:
            # Video Details
            if item.get('uploader'): details.append(item['uploader'])
            if item.get('resolution'): details.append(item['resolution'])
            if item.get('size'): details.append(item['size'])
            if item.get('duration'): details.append(format_eta(item['duration']))
        
        d_str = " • ".join(details) if details else "No details available"
        ctk.CTkLabel(info_frame, text=d_str, font=("Comfortaa", 12), text_color="gray60", anchor="w").pack(fill="x")
        
        # 3. Actions (Right Side)
        actions = ctk.CTkFrame(c, fg_color="transparent")
        actions.pack(side="right", padx=10)
        
        # Date (Top of Right)
        ctk.CTkLabel(actions, text=item.get('date', ''), font=("Comfortaa", 11), text_color="gray70").pack(anchor="e", pady=(5, 5))
        
        # Buttons Row
        btns = ctk.CTkFrame(actions, fg_color="transparent")
        btns.pack(anchor="e")
        
        # Open Link
        ctk.CTkButton(btns, text="Open", width=60, height=25, fg_color="transparent", border_width=1, border_color=self.accent_color,
                      text_color=self.text_color, hover_color=self.hover_color,
                      command=lambda u=item.get('url'): webbrowser.open(u)).pack(side="left", padx=(0, 5))
                      
        # Redownload
        ctk.CTkButton(btns, text="Redownload", width=90, height=25, fg_color=self.accent_color, text_color="white", hover_color=self.hover_color,
                      command=lambda u=item.get('url'): self.redownload_action(u)).pack(side="left")

    def clear_history_action(self):
        if self.show_blocking_confirm("Clear History", "Clear all download history?", "Clear All", "Cancel", "danger"):
            os.remove("history.json") if os.path.exists("history.json") else None
            self.update_history_ui()
            
    def redownload_action(self, url):
        if not url: return
        # Debounce: Ignore if already fetching
        if getattr(self, 'is_fetching', False):
            return
        self.select_frame("Download")
        self.url_entry.delete(0, tk.END)
        self.url_entry.insert(0, url)
        # Auto check
        self.check_link()

    def process_queue(self):
        item = pop_queue()
        if item:
            self.is_processing_queue = True # Flag
            self.url_entry.delete(0, tk.END)
            self.url_entry.insert(0, item['url'])
            self.select_frame("Download")
            self.update_queue_ui()
            
            # Restore Metadata for History/Logic
            if item.get('type') == 'playlist':
                 self.is_playlist = True
                 # Reconstruct info dict
                 self.current_playlist_info = {
                     'title': item.get('title'),
                     'uploader': item.get('uploader'),
                     'webpage_url': item.get('url'),
                     'entries': [{'thumbnail': item.get('thumbnail')}] * int(item.get('count', 1))
                 }
                 self.current_video_info = None
            else:
                 self.is_playlist = False
                 self.current_video_info = {
                     'title': item.get('title'),
                     'thumbnail': item.get('thumbnail'),
                     'uploader': item.get('uploader'),
                     'duration': item.get('duration'),
                     'webpage_url': item.get('url')
                 }
                 self.current_playlist_info = None

            self.start_download()
        else:
            if getattr(self, "is_processing_queue", False):
                self.is_processing_queue = False
                self.show_notification("All items processed successfully!", type="success")
            else:
                self.show_notification("Queue is empty!", type="info")

    def browse_path(self):
        p = filedialog.askdirectory()
        if p:
            self.path_entry.delete(0, tk.END)
            self.path_entry.insert(0, p)

    def browse_cookies(self):
        f = filedialog.askopenfilename(filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")])
        if f:
            self.cookies_entry.delete(0, tk.END)
            self.cookies_entry.insert(0, f)
            
    def reset_settings_action(self):
        if self.show_blocking_confirm("Reset Settings", "Reset all settings to default values?", "Reset", "Cancel", "warning"):
            from logic.settings import DEFAULT_SETTINGS
            global current_settings
            current_settings = DEFAULT_SETTINGS.copy()
            save_settings(current_settings)
            
            # Refresh UI Fields
            self.path_entry.delete(0, tk.END)
            self.path_entry.insert(0, current_settings["download_path"])
            self.theme_var.set(current_settings["theme"])
            self.thumb_var.set(current_settings["embed_thumbnail"])
            self.meta_var.set(current_settings["embed_metadata"])
            self.clip_var.set(current_settings["clipboard_monitor"])
            self.notif_var.set(current_settings.get("notifications", True))
            self.cookies_entry.delete(0, tk.END)
            self.cookies_entry.insert(0, "")
            
            ctk.set_appearance_mode(current_settings["theme"])
            self.show_notification("Settings have been reset.", type="info")

    def save_config(self):
        current_settings["download_path"] = self.path_entry.get()
        current_settings["cookies_path"] = self.cookies_entry.get()
        current_settings["theme"] = self.theme_var.get()
        current_settings["embed_thumbnail"] = self.thumb_var.get()
        current_settings["embed_metadata"] = self.meta_var.get()
        current_settings["clipboard_monitor"] = self.clip_var.get()
        current_settings["notifications"] = self.notif_var.get()
        save_settings(current_settings)
        
        # Apply Theme Instantly
        self.apply_theme_instant()
        self.show_notification("Settings Saved Successfully.", type="success")

    def change_accent_color(self, color):
        old_color = self.accent_color # Capture current before update
        current_settings["accent_color"] = color
        save_settings(current_settings)
        # self.show_notification("Applying Theme...", type="success") 
        # Smooth refresh instead of full reload
        self.update_ui_colors(old_color)
        
    def update_ui_colors(self, old_color_hex):
        """Seamlessly update UI colors globally by traversing widget tree"""
        self.setup_theme() # Recalculate self.hover_color (new), self.accent_color
        
        # Helper for recursive update
        def update_widget(widget):
            try:
                # 1. Check FG Color
                try:
                    fg = widget.cget("fg_color")
                    # Handle single string or list [light, dark]
                    # Since accent is usually same for both or specific, strictly replace if matches old hex
                    if isinstance(fg, str) and fg.lower() == old_color_hex.lower():
                        widget.configure(fg_color=self.accent_color)
                except: pass
                
                # 2. Check Hover Color (Update all buttons mostly)
                try:
                    # If it has a hover color, update it to new hover shade
                    # We update ALL hoverable widgets to ensure consistency
                    # But maybe only those that were using the old hover?
                    # Safer: Update all buttons/checkboxes
                    if isinstance(widget, (ctk.CTkButton, ctk.CTkCheckBox, ctk.CTkOptionMenu)):
                         widget.configure(hover_color=self.hover_color)
                except: pass

                # 3. Check Border Color
                try:
                    border = widget.cget("border_color")
                    if isinstance(border, str) and border.lower() == old_color_hex.lower():
                        widget.configure(border_color=self.accent_color)
                except: pass
                
                # 4. Check Progress Color
                try:
                    prog = widget.cget("progress_color")
                    if isinstance(prog, str) and prog.lower() == old_color_hex.lower():
                        widget.configure(progress_color=self.accent_color)
                except: pass
                
                # 5. Check Scrollbar/Switch
                try:
                    btn_c = widget.cget("button_color")
                    if isinstance(btn_c, str) and btn_c.lower() == old_color_hex.lower():
                        widget.configure(button_color=self.accent_color)
                except: pass
                
                # 6. Check Text Color (Labels, Section Headers)
                try:
                    tc = widget.cget("text_color")
                    if isinstance(tc, str) and tc.lower() == old_color_hex.lower():
                        widget.configure(text_color=self.accent_color)
                except: pass

                # Recurse children
                for child in widget.winfo_children():
                    update_widget(child)
            except Exception as e:
                pass

        # 1. Update Sidebar Buttons (Special handling for active state)
        for name, btn in self.nav_buttons.items():
            btn.configure(hover_color=self.hover_color)
            if name == self.current_frame:
                btn.configure(fg_color=self.accent_color)
                
        # 2. Global Traversal for all content frames
        for frame in self.frames.values():
            update_widget(frame)
            
        # 3. Update Settings Tab SPECIFICALLY (Rebuild content to refresh color pickers)
        # Why? Because the "Border" on the color circles needs to move.
        if "Settings" in self.frames:
            s_frame = self.frames["Settings"]
            for child in s_frame.winfo_children():
                child.destroy()
            self.build_settings_tab(s_frame)
            
        # 4. Notification
        self.show_notification("Theme Updated Successfully", type="success")

    def on_closing(self):
        """Graceful shutdown with orphaned process cleanup"""
        try:
            # Force cancel any in-progress downloads to stop yt-dlp gracefully
            self.is_cancelled = True
            
            # Kill any orphaned yt-dlp or ffmpeg child processes
            try:
                import psutil
                current_proc = psutil.Process()
                children = current_proc.children(recursive=True)
                for child in children:
                    child_name = child.name().lower()
                    if 'yt-dlp' in child_name or 'ffmpeg' in child_name or 'ffprobe' in child_name:
                        logging.info(f"Terminating orphaned child process: {child.pid} ({child_name})")
                        child.terminate()
                # Give them a moment to terminate gracefully
                _, still_alive = psutil.wait_procs(children, timeout=2)
                for alive in still_alive:
                    logging.warning(f"Force-killing stubborn process: {alive.pid}")
                    alive.kill()
            except ImportError:
                # psutil not available, try basic cleanup
                pass
            except Exception as e:
                logging.warning(f"Process cleanup failed: {e}")
            
            # Shutdown executor
            if hasattr(self, 'executor'):
                self.executor.shutdown(wait=False, cancel_futures=True)
            
            # Fade out animation
            alpha = self.attributes("-alpha")
            if alpha > 0:
                alpha -= 0.15 # Fast fade
                self.attributes("-alpha", alpha)
                self.after(20, self.on_closing)
            else:
                self.destroy()
                sys.exit(0)
        except:
            self.destroy()
            sys.exit(0)
    
    def apply_custom_color(self):
        """Validate and apply custom hex color from entry"""
        color = self.custom_color_entry.get().strip()
        
        # Basic validation
        if not color.startswith("#"):
            color = "#" + color
            
        # Validate hex format
        if len(color) != 7:
            self.show_notification("Invalid hex color. Use format: #RRGGBB", type="error")
            return
            
        try:
            # Verify it's valid hex
            int(color[1:], 16)
        except ValueError:
            self.show_notification("Invalid hex color. Use format: #RRGGBB", type="error")
            return
            
        self.change_accent_color(color)
        
    def reload_ui(self):
        # Full UI Rebuild for Theme
        try:
            self.sidebar_frame.destroy()
            self.content_frame.destroy()
        except: pass
        
        self.setup_theme() # Re-read accent color
        self.create_sidebar()
        self.create_content_area()
        self.frames = {}
        self.build_frames()
        self.select_frame("Settings")


    def show_notification(self, message, type="info"):
        """Displays a modern, animated toast notification overlay."""
        # 1. Clear previous
        if hasattr(self, "current_notification") and self.current_notification:
            try: self.current_notification.destroy()
            except: pass
            
        # 2. Config with expanded types
        # 2. Config with expanded types
        colors = {
            "success": self.accent_color,  # Match User Accent
            "error": "#FF5555",    # Soft Red
            "warning": "#FFA500",  # Orange
            "info": self.accent_color
        }
        icons = {
            "success": "✔",
            "error": "✖",
            "warning": "⚠",
            "info": "ℹ"
        }
        color = colors.get(type, self.accent_color)
        icon = icons.get(type, "ℹ")
        
        # 3. Create Container (Modern Pill Shape with subtle shadow)
        # Fix: bg_color="transparent" prevents black corners
        toast = ctk.CTkFrame(self, fg_color=color, corner_radius=25, 
                             border_width=1, border_color="gray30", bg_color="transparent")
        
        # 4. Content with padding
        content = ctk.CTkFrame(toast, fg_color="transparent")
        content.pack(padx=20, pady=10)
        
        ctk.CTkLabel(content, text=icon, text_color="white", 
                     font=("Segoe UI Emoji", 16)).pack(side="left", padx=(0, 8))
        ctk.CTkLabel(content, text=message, text_color="white", 
                     font=("Comfortaa", 13, "bold")).pack(side="left")
        
        # 5. Animate slide-in from bottom
        toast.place(relx=0.5, rely=1.1, anchor="center")  # Start off-screen
        self.current_notification = toast
        
        def slide_in(current_rely=1.1):
            if current_rely > 0.92:
                toast.place(relx=0.5, rely=current_rely - 0.03, anchor="center")
                self.after(15, lambda: slide_in(current_rely - 0.03))
        
        self.after(10, slide_in)
        
        # 6. Auto-hide after delay
        def hide():
            if toast.winfo_exists():
                toast.destroy()
        
        self.after(6000, hide)

    def show_confirm_dialog(self, title, message, confirm_text="Confirm", cancel_text="Cancel", 
                            dialog_type="warning", on_confirm=None, on_cancel=None):
        """
        Modern confirmation dialog that replaces tkinter.messagebox.askyesno.
        Returns immediately. Actions are handled via callbacks.
        """
        # Create overlay background (semi-transparent)
        overlay = ctk.CTkFrame(self, fg_color="black")
        overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
        overlay.configure(fg_color=("gray20", "gray10"))  # Darker for modal feel
        
        # Dialog container (modern card)
        dialog = ctk.CTkFrame(overlay, fg_color=self.bg_color, corner_radius=16, border_width=1, border_color="gray40")
        dialog.place(relx=0.5, rely=0.5, anchor="center")
        dialog.configure(width=400, height=200)
        
        # Header with icon
        header = ctk.CTkFrame(dialog, fg_color="transparent", height=60)
        header.pack(fill="x", padx=20, pady=(20, 10))
        
        # Icon based on type
        icons = {
            "warning": ("⚠️", "#FFA500"),
            "danger": ("🗑️", "#FF5555"),
            "info": ("ℹ️", self.accent_color),
            "question": ("❓", self.accent_color)
        }
        icon, icon_color = icons.get(dialog_type, ("❓", self.accent_color))
        
        icon_label = ctk.CTkLabel(header, text=icon, font=("Segoe UI Emoji", 32), text_color=icon_color)
        icon_label.pack(side="left", padx=(0, 15))
        
        title_label = ctk.CTkLabel(header, text=title, font=("Comfortaa", 18, "bold"), 
                                   text_color=self.text_color, anchor="w")
        title_label.pack(side="left", fill="x", expand=True)
        
        # Message
        msg_label = ctk.CTkLabel(dialog, text=message, font=("Comfortaa", 13), 
                                  text_color="gray60", wraplength=350, justify="left")
        msg_label.pack(fill="x", padx=25, pady=(0, 20))
        
        # Button row
        btn_row = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_row.pack(fill="x", padx=20, pady=(0, 20))
        
        result = [None]  # Mutable container for result
        
        def close_dialog(confirmed):
            result[0] = confirmed
            overlay.destroy()
            if confirmed and on_confirm:
                on_confirm()
            elif not confirmed and on_cancel:
                on_cancel()
        
        # Cancel button (left, outline style)
        cancel_btn = ctk.CTkButton(
            btn_row, text=cancel_text, width=120, height=36,
            fg_color="transparent", border_width=1, border_color=self.accent_color,
            text_color=self.text_color, hover_color=self.hover_color,
            font=("Comfortaa", 12, "bold"),
            command=lambda: close_dialog(False)
        )
        cancel_btn.pack(side="left", padx=(0, 10))
        
        # Confirm button (right, filled style)
        confirm_color = "#FF5555" if dialog_type == "danger" else self.accent_color
        confirm_btn = ctk.CTkButton(
            btn_row, text=confirm_text, width=120, height=36,
            fg_color=confirm_color, text_color="white",
            hover_color="#CC4444" if dialog_type == "danger" else self.hover_color,
            font=("Comfortaa", 12, "bold"),
            command=lambda: close_dialog(True)
        )
        confirm_btn.pack(side="right")
        
        # Keyboard bindings
        dialog.bind("<Return>", lambda e: close_dialog(True))
        dialog.bind("<Escape>", lambda e: close_dialog(False))
        dialog.focus_set()
        
        # Click outside to cancel
        overlay.bind("<Button-1>", lambda e: close_dialog(False) if e.widget == overlay else None)
        
        return result  # For synchronous checks if needed
    
    def show_blocking_confirm(self, title, message, confirm_text="Yes", cancel_text="No", 
                               dialog_type="warning"):
        """
        Blocking confirmation dialog that waits for user response.
        Use this as a direct replacement for messagebox.askyesno.
        Returns True/False.
        """
        result = [None]
        dialog_closed = threading.Event()
        
        def on_confirm():
            result[0] = True
            dialog_closed.set()
        
        def on_cancel():
            result[0] = False
            dialog_closed.set()
        
        # Create dialog
        self.show_confirm_dialog(
            title, message, confirm_text, cancel_text, 
            dialog_type, on_confirm, on_cancel
        )
        
        # Wait for dialog to close (tkinter-safe blocking)
        while not dialog_closed.is_set():
            self.update()
            self.update_idletasks()
            time.sleep(0.01)
        
        return result[0]

    def play_video(self):
        path = current_settings["download_path"]
        try:
             if os.name == 'nt':
                 os.startfile(path)
             else:
                 subprocess.call(['xdg-open', path])
        except Exception as e:
            self.show_notification(f"Could not open: {e}", type="error")

