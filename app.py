import customtkinter as ctk
from tkinter import ttk, Menu, messagebox,PhotoImage
from ttkthemes import ThemedTk, ThemedStyle
from yt_dlp import YoutubeDL
import threading
from gtts import gTTS
import os
from PIL import Image, ImageTk
import requests
from io import BytesIO
import datetime
from copy import copy
import tkinter as tk

# Initialize 
mode = "dark"
download_in_progress = False

# Root window with ThemedTk
root = ThemedTk(theme="arc")

# Set appearance mode and content frame background color based on the initial mode
if mode == "dark":
    ctk.set_appearance_mode("System")
    content_frame_bg = "#222222"
else:
    ctk.set_appearance_mode("Light")
    content_frame_bg = "#FAFAFA"

# Configure root window background for dark mode
root.configure(bg=content_frame_bg)
root.title("Yikes YTD")
root.geometry("745x720")
root.minsize(745, 720)
root.maxsize(1145, 920)

# Path to icon file
icon_path = "images/icon.png" 

# Load PNG image
icon_image = PhotoImage(file=icon_path)

# Taskbar icon
root.tk.call("wm", "iconphoto", root._w, icon_image)

root.iconphoto(True, icon_image)

# Icon name for the window
root.wm_iconname("Yikes YTD")

style = ThemedStyle(root)
style.configure("Light.TButton", background="#FAFAFA")
style.configure("Dark.TButton", background="#222222")

# Custom font
custom_font = ctk.CTkFont(family="Comfortaa", size=12, weight="bold")
list_font = ctk.CTkFont(family="Comfortaa", size=10, weight="bold")
version_font = ctk.CTkFont(family="Comfortaa", size=9, weight="bold")

# Menu frame
menu_frame_style = ttk.Style()
menu_frame_style.configure("Menu.TFrame", background="#222222")
menu_frame = ttk.Frame(root, width=220, style="Dark.TFrame" if mode == "dark" else "Light.TFrame")
menu_frame.pack(side="left", fill="y", padx=(0), pady=(0))
menu_frame.pack_propagate(0)

# Toggle button to change appearance mode
def change():
    global mode
    if mode == "dark":
        entry_url.configure(bg_color="#FAFAFA")
        fetch_button.configure(bg_color="#FAFAFA")
        download_button.configure(bg_color="#FAFAFA")
        toggle_button.configure(bg_color="#FAFAFA")

        content_frame_style.configure("Light.TFrame", background="#FAFAFA")
        content_frame_style.configure("Dark.TFrame", background="#222222")
        for tab_frame in [home_content_frame, download_content_frame, settings_content_frame,
                            help_content_frame, about_content_frame, feedback_content_frame, button_frame1, details_frame, details_frame2, details_frame3, thumbnail_frame, video_title_frame, progress_frame, speed_frame, time_frame, menu_frame, btns_frame]:
            tab_frame.configure(style="Light.TFrame")
        mode = "light"
        toggle_button.configure(text="Dark Mode")  
        ctk.set_appearance_mode("Light")  
        logo_path = logo_image_light
    else:
        entry_url.configure(bg_color="#222222") 
        fetch_button.configure(bg_color="#222222")
        download_button.configure(bg_color="#222222")
        toggle_button.configure(bg_color="#222222")

        content_frame_style.configure("Light.TFrame", background="#FAFAFA")
        content_frame_style.configure("Dark.TFrame", background="#222222")
        for tab_frame in [home_content_frame, download_content_frame, settings_content_frame,
                            help_content_frame, about_content_frame, feedback_content_frame, button_frame1, details_frame, details_frame2, details_frame3, thumbnail_frame, video_title_frame, progress_frame, speed_frame, time_frame, menu_frame, btns_frame]:
            tab_frame.configure(style="Dark.TFrame")
        mode = "dark"
        toggle_button.configure(text="Light Mode") 
        ctk.set_appearance_mode("System")
        logo_path = logo_image_dark

    # Logo image
    update_logo_image(logo_path)

# Function to update logo image
def update_logo_image(path):
    logo_image = PhotoImage(file=path)
    logo_label.configure(image=logo_image)
    logo_label.image = logo_image 

# Toggle button to change appearance mode
toggle_button_text = "Light Mode" if mode == "dark" else "Dark Mode"
toggle_button = ctk.CTkButton(menu_frame, text=toggle_button_text, command=change, font=list_font)
toggle_button.pack(side="top", anchor="center", padx=0, pady=(20, 0))
toggle_button.configure(bg_color="#222222" if mode == "dark" else "#FAFAFA", font=list_font)

# Frame for buttons in the menu
btns_frame = ttk.Frame(menu_frame, style="Dark.TFrame" if mode == "dark" else "Light.TFrame")
btns_frame.pack(side="top", fill="y", anchor="center", padx=0, pady=(100, 0))

# Function to switch to a specific tab
def switch_to_tab(tab_index):
    notebook.select(tab_index)

# Buttons for each tab
tab_buttons = []
for index, tab_name in enumerate(["Home", "Download", "Settings", "Help & FAQs", "About", "Feedback & Support"]):
    # Container frame for each button
    button_frame = ttk.Frame(btns_frame, style="Dark.TFrame" if mode == "dark" else "Light.TFrame")
    button_frame.pack(side="top", fill="x", pady=(0, 30))

    # Tab button inside the frame
    tab_button = ctk.CTkButton(button_frame, text=tab_name, command=lambda idx=index: switch_to_tab(idx), font=custom_font)
    tab_button.pack(fill="x")
    tab_button.configure(bg_color="#222222" if mode == "dark" else "#FAFAFA")

    tab_buttons.append(tab_button)

# Frame for version information
version_frame = ttk.Frame(menu_frame, style="Dark.TFrame" if mode == "dark" else "Light.TFrame")
version_frame.pack(side="bottom", anchor="center", pady=(0, 20))

# Label displaying version of the application
version_label = ctk.CTkLabel(version_frame, text="Version 1.0.0", padx=10, pady=10, bg_color="#326092", text_color="white", font=version_font)
version_label.pack()

# Content frame for entire application
content_frame_style = ttk.Style()
content_frame_style.configure("Light.TFrame", background="#FAFAFA")
content_frame_style.configure("Dark.TFrame", background="#222222")

# Right side content frame
content_frame = tk.Frame(root, bg="#333333", borderwidth=20)
content_frame.pack(side="right", fill=ctk.BOTH, expand=True, padx=(0, 0), pady=(0, 0))

# Notebook (tabbed widget) for tabs
notebook_style = ttk.Style()
notebook_style.configure("TNotebook.Tab", font=("Comfortaa", 9, "bold"), foreground="black")
notebook = ttk.Notebook(content_frame, style="TNotebook")
notebook.pack(expand=1, fill="both", pady=0, padx=0)

# Frame for each tab
home_tab = ttk.Frame(notebook, style="Menu.TFrame")
download_tab = ttk.Frame(notebook, style="Menu.TFrame")
settings_tab = ttk.Frame(notebook, style="Menu.TFrame")
help_tab = ttk.Frame(notebook, style="Menu.TFrame")
about_tab = ttk.Frame(notebook, style="Menu.TFrame")
feedback_tab = ttk.Frame(notebook, style="Menu.TFrame")

# Tabs on the notebook
notebook.add(home_tab, text="Home")
notebook.add(download_tab, text="Download")
notebook.add(settings_tab, text="Settings")
notebook.add(help_tab, text="Help & FAQs")
notebook.add(about_tab, text="About")
notebook.add(feedback_tab, text="Feedback & Support")

# Set default selected tab
notebook.select(0)  # Home tab

# ...

# Home Tab Content Frame
home_content_frame = ttk.Frame(home_tab, style="Dark.TFrame" if mode == "dark" else "Light.TFrame")
home_content_frame.pack(fill=ctk.BOTH, expand=True)

# Logo Frame
logo_frame = ttk.Frame(home_content_frame)
logo_frame.pack(pady=100) 

# Logo
logo_image_dark = "images/logo-dark.png"
logo_image_light = "images/logo-light.png"
logo_path = logo_image_dark if mode == "dark" else logo_image_light
logo_image = PhotoImage(file=logo_path)
logo_label = ttk.Label(logo_frame, image=logo_image, borderwidth=0)
logo_label.pack()

# Welcome Message Frame
welcome_frame = ttk.Frame(home_content_frame)
welcome_frame.pack() 

# Welcome Message
welcome_message = ctk.CTkLabel(welcome_frame, text="Your Favourite YouTube Downloader!", text_color="white", padx=20, pady=20, bg_color="#326092", font=custom_font)
welcome_message.pack()

# Copyright contents
current_year = datetime.datetime.now().year
copyright_text = f"Copyright © {current_year} Yikes YTD. All Rights Reserved."

copy_right = ctk.CTkLabel(home_content_frame, text=copyright_text, text_color="white", bg_color="#444444", padx=10, pady=5, font=("Comfortaa", 8, "normal"))
copy_right.pack(side="bottom", anchor="s")

# ...

# Download Tab Content Frame
download_content_frame = ttk.Frame(download_tab, style="Dark.TFrame" if mode == "dark" else "Light.TFrame")
download_content_frame.pack(fill=ctk.BOTH, expand=True)

# URL label and entry widget
url_label = ctk.CTkLabel(download_content_frame, text="Enter the YouTube URL: ", text_color="white", padx=10, pady=10, bg_color="#333333", font=custom_font)
entry_url = ctk.CTkEntry(download_content_frame, width=400, height=40, bg_color="#222222", font=custom_font)
url_label.pack(pady=("35p", "5p"))
entry_url.pack(pady=("10p", "5p"))

# Buttons frame
button_frame1 = ttk.Frame(download_content_frame, style="Dark.TFrame" if mode == "dark" else "Light.TFrame", width=400)
button_frame1.pack(pady=("10p", "5p"))

# Fetch Formats button/ Check link button
fetch_button = ctk.CTkButton(button_frame1, text="Check Link", command=lambda: fetch_all_async(entry_url.get()), width=105, font=custom_font)
fetch_button.pack(side="left", padx=5)
fetch_button.configure(bg_color="#222222" if mode == "dark" else "#FAFAFA", font=custom_font)

# Resolutions combobox
resolutions = ["Available formats"]  
resolution_var = ctk.StringVar()
resolution_combobox = ttk.Combobox(button_frame1, values=resolutions, textvariable=resolution_var, font=custom_font)
resolution_combobox.pack(side="left", padx=2)
resolution_combobox.set(resolutions[0])

# Download button
download_button = ctk.CTkButton(button_frame1, text="Download", command=lambda: download(), width=105, font=custom_font)
download_button.pack(side="left", padx=5)
download_button.configure(bg_color="#222222" if mode == "dark" else "#FAFAFA", font=custom_font)

# Frame for details (speed, percentage, time)
details_frame = ttk.Frame(download_content_frame, style="Dark.TFrame" if mode == "dark" else "Light.TFrame", width=400)
details_frame.pack(pady=("5p", "0p"))

# Frame for progress label
progress_frame = ttk.Frame(details_frame, style="Dark.TFrame" if mode == "dark" else "Light.TFrame", width=100)
progress_frame.pack(side="left", padx=1)

# Frame for download speed
speed_frame = ttk.Frame(details_frame, style="Dark.TFrame" if mode == "dark" else "Light.TFrame", width=200)
speed_frame.pack(side="left", padx=1)

# Frame for ETA (time)
time_frame = ttk.Frame(details_frame, style="Dark.TFrame" if mode == "dark" else "Light.TFrame", width=100)
time_frame.pack(side="left", padx=1)

# Progress label
progress_label = ctk.CTkLabel(progress_frame, text="Percentage: 0%", text_color="white", padx=10, pady=10, bg_color="#333333", font=custom_font)
progress_label.pack()

# Label for download speed
speed_label = ctk.CTkLabel(speed_frame, text="Download Speed: 0.00 KB/s", text_color="white", padx=10, pady=10, bg_color="#333333", font=custom_font)
speed_label.pack()

# Label for ETA
time_label = ctk.CTkLabel(time_frame, text="Time: 00:00:00", text_color="white", padx=10, pady=10, bg_color="#333333", font=custom_font)
time_label.pack()

# Frame for details2 
details_frame2 = ttk.Frame(download_content_frame, style="Dark.TFrame" if mode == "dark" else "Light.TFrame", width=400)
details_frame2.pack()

# Frame for details3
details_frame3 = ttk.Frame(details_frame2, style="Dark.TFrame" if mode == "dark" else "Light.TFrame", width=400)
details_frame3.pack()

# Frame for thumbnail
thumbnail_frame = ttk.Frame(details_frame3, style="Dark.TFrame" if mode == "dark" else "Light.TFrame", width=150)
thumbnail_frame.pack(side="left", anchor="w")

# Play button
# play_button = ctk.CTkButton(thumbnail_frame, text="Play", command=play_video)

# Playlist title label
playlist_title_label = ctk.CTkLabel(details_frame3, text="", text_color="white", compound="top", padx=2, pady=5, wraplength=245, bg_color="#333333", font=custom_font, width=250, justify="left")

# Thumbnail label
thumbnail_label = ctk.CTkLabel(thumbnail_frame, text="", text_color="white", compound="top", padx=2, pady=5, wraplength=400, bg_color="#333333", font=custom_font)

# Frame for list of videos
playlist_videos_frame = ctk.CTkScrollableFrame(details_frame2, width=390, corner_radius=0, scrollbar_button_color='#326092', scrollbar_button_hover_color='#67a6eb')
playlist_videos_frame.bind_all("<Button-4>", lambda e: playlist_videos_frame._parent_canvas.yview("scroll", -1, "units"))
playlist_videos_frame.bind_all("<Button-5>", lambda e: playlist_videos_frame._parent_canvas.yview("scroll", 1, "units"))

# Frame for each video title
video_title_frame = ttk.Frame(playlist_videos_frame, style="Dark.TFrame" if mode == "dark" else "Light.TFrame", width=380)

# Checking label
checking_label = ctk.CTkLabel(download_content_frame, text="Checking...", text_color="white", padx=10, pady=10, bg_color="#333333", font=custom_font)

# Custom style for Progress Bar
progress_bar_style = ttk.Style()
progress_bar_style.layout("Custom.TProgressbar",
    [('Custom.Progressbar.trough', {'children': [('Custom.Progressbar.pbar', {'side': 'left', 'sticky': 'ns'})], 'sticky': 'nswe'}),
     ('Custom.Progressbar.label', {'sticky': ''})])

progress_bar_style.configure("Custom.TProgressbar", troughcolor="#F6F4F1", background="#326092", thickness=15)

# Progress Bar
progress_bar = ttk.Progressbar(download_content_frame, length=400, mode="determinate", style="Custom.TProgressbar")
progress_bar["value"] = 0.0  # Set initial value to 0

# Status label
status_label = ctk.CTkLabel(download_content_frame, text="Downloading...", text_color="white", padx=10, pady=10, bg_color="#333333", font=custom_font)

# Context menu for entry widget
entry_menu = Menu(root, tearoff=0)

# Customize appearance of menu items
entry_menu.add_command(label="Cut", font=("Comfortaa", 10), background="#FAFAFA", foreground="black", command=lambda: entry_url.event_generate('<Control-x>'))
entry_menu.add_command(label="Copy", font=("Comfortaa", 10), background="#FAFAFA", foreground="black", command=lambda: entry_url.event_generate('<Control-c>'))
entry_menu.add_command(label="Paste        ", font=("Comfortaa", 10), background="white", foreground="black", command=lambda: entry_url.event_generate('<Control-v>'))

# Bind the context menu to the entry widget
entry_url.bind("<Button-3>", lambda e: entry_menu.post(e.x_root, e.y_root))

# Check if URL is a playlist link
def is_playlist_link(url):
    return "playlist?list=" in url

# Fetch all asynchronously
def fetch_all_async(url):
    try:
        # Show the "Checking..." label
        show_checking_label()

        # Check if the URL is for a playlist
        if is_playlist_link(url):
            # Fetch playlist information asynchronously
            fetch_playlist_info_async(url)
        else:
            # Fetch video information asynchronously
            fetch_video_info_async(url)

    except Exception as e:
        status_label.configure(text=f"Error {str(e)}", text_color="white")
        set_elements_state("normal")

# Fetch video information asynchronously
def fetch_video_info_async(url):
    try:
        with YoutubeDL() as ydl:
            video_info = ydl.extract_info(url, download=False)

            # Fetch formats asynchronously
            fetch_formats_thread = threading.Thread(target=lambda: fetch_formats_async(copy(video_info)))
            fetch_thumbnail_thread = threading.Thread(target=lambda: fetch_thumbnail_async(copy(video_info)))
            fetch_title_thread = threading.Thread(target=lambda: fetch_title_async(copy(video_info)))

            fetch_formats_thread.start()
            fetch_thumbnail_thread.start()
            fetch_title_thread.start()

            # Return the entire video information
            return video_info

    except Exception as e:
        messagebox.showerror("Error", f"Failed to fetch video information: {str(e)}")
        return None
    finally:
        # Enable all elements after fetching
        set_elements_state("normal")

# Fetch playlist information asynchronously
def fetch_playlist_info_async(url):
    try:
        with YoutubeDL() as ydl:
            playlist_info = ydl.extract_info(url, download=False)

            # Fetch playlist formats asynchronously
            fetch_playlist_formats_thread = threading.Thread(target=lambda: fetch_playlist_formats_async(playlist_info))
            fetch_playlist_thumbnail_thread = threading.Thread(target=lambda: fetch_playlist_thumbnail_async(playlist_info))
            fetch_playlist_title_thread = threading.Thread(target=lambda: fetch_playlist_title_async(playlist_info))
            fetch_playlist_videos_thread = threading.Thread(target=lambda: fetch_playlist_video_titles_async(playlist_info))

            fetch_playlist_formats_thread.start()
            fetch_playlist_thumbnail_thread.start()
            fetch_playlist_title_thread.start()
            fetch_playlist_videos_thread.start()

            # Return the entire video information
            return playlist_info

    except Exception as e:
        messagebox.showerror("Error", f"Failed to fetch playlist information: {str(e)}")
    finally:
        # Enable all elements after fetching
        set_elements_state("normal")

# Show the "Checking..." label
def show_checking_label():
    checking_label.pack(pady=("10p", "5p"))

# Hide both labels
def hide_labels():
    checking_label.pack_forget()

# Fetch playlist Formats asynchronously
def fetch_playlist_formats_async(playlist_info):
    try:
        # Define the formats
        formats = {"Audio": "bestaudio", "Video": "best"}
        formats = list(formats.keys())

        # Check if 'entries' field is present in playlist_info
        if 'entries' in playlist_info:
            # Handle the fetched results on the main thread
            root.after(0, lambda: handle_fetch_playlist_results(formats))
        else:
            # Case if link is not a playlist
            raise ValueError("Provided URL is not a playlist.")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to fetch playlist formats: {str(e)}")
    finally:
        # Enable all elements after fetching
        set_elements_state("normal")

# Fetch playlist thumbnail asynchronously
def fetch_playlist_thumbnail_async(playlist_info):
    try:
        # Extract playlist information
        first_video_thumbnail_url = playlist_info['entries'][0]['thumbnail']

        # Fetch and display the thumbnail asynchronously
        threading.Thread(target=lambda: display_playlist_thumbnail(first_video_thumbnail_url)).start()

    except Exception as e:
        print(f"Error fetching playlist thumbnail: {str(e)}")

# Fetch playlist title asynchronously
def fetch_playlist_title_async(playlist_info):
    try:
        # Extract playlist information
        title = playlist_info.get('title')

        # Define the formats
        formats = {"Audio": "bestaudio", "Video": "best"}
        formats = list(formats.keys())

        # Update the UI with the fetched playlist title
        root.after(0, lambda: handle_fetch_playlist_results(formats))

        # Return the playlist title
        return title

    except Exception as e:
        messagebox.showerror("Error", f"Failed to fetch playlist title: {str(e)}")
    finally:
        # Enable all elements after fetching
        set_elements_state("normal")

# Fetch playlist video titles asynchronously
def fetch_playlist_video_titles_async(playlist_info):
    try:
        playlist_title = playlist_info.get('title')

        # Check if 'entries' field is present in playlist_info
        if 'entries' in playlist_info:
            video_titles = [entry.get('title') for entry in playlist_info['entries']]

            # Update the UI with the fetched video titles
            root.after(0, lambda: display_playlist_video_titles(video_titles, playlist_title))
        else:
            # Case if link is not a playlist
            raise ValueError("Provided URL is not a playlist.")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to fetch playlist video titles: {str(e)}")
    finally:
        # Enable all elements after fetching
        set_elements_state("normal")

# Fetch video Formats asynchronously
def fetch_formats_async(video_info):
    try:
        # Extract information from the provided video_info
        formats = [f"{format['format_id']} - {format['resolution']}" for format in video_info.get('formats', [])]
        title = video_info.get('title')

        # Call the handle_fetch_results function with the fetched data
        root.after(0, lambda: handle_video_fetch_results(formats, title, video_info))

    except Exception as e:
        messagebox.showerror("Error", f"Failed to fetch formats: {str(e)}")
    finally:
        # Enable all elements after fetching
        set_elements_state("normal")

# Fetch video thumbnail asynchronously
def fetch_thumbnail_async(video_info):
    try:
        if isinstance(video_info, dict):
            thumbnail_url = video_info.get('thumbnail')
        else:
            thumbnail_url = video_info

        if thumbnail_url:
            display_video_thumbnail(thumbnail_url)

    except Exception as e:
        print(f"Error fetching thumbnail: {str(e)}")

# Fetch video title asynchronously
def fetch_title_async(video_info):
    try:
        # Extract information from the provided video_info
        title = video_info.get('title')
        return title

    except Exception as e:
        print(f"Error fetching title: {str(e)}")
        return None

# display playlist thumbnail 
def display_playlist_thumbnail(thumbnail_url):
    try:
        response = requests.get(thumbnail_url)
        thumbnail = Image.open(BytesIO(response.content))

        # Resize the image to 100x50
        thumbnail = thumbnail.resize((150, 75))

        thumbnail = ImageTk.PhotoImage(thumbnail)

        # Display thumbnail on the main thread
        root.after(0, lambda: display_thumbnail(thumbnail))

    except Exception as e:
        print(f"Error displaying thumbnail: {str(e)}")

# Fetch video thumbnail
def display_video_thumbnail(url):
    try:
        response = requests.get(url)
        thumbnail = Image.open(BytesIO(response.content))

        # Resize the image to 400x200
        thumbnail = thumbnail.resize((400, 200))

        thumbnail = ImageTk.PhotoImage(thumbnail)
        
        # Display the thumbnail on the main thread
        root.after(0, lambda: display_thumbnail(thumbnail))
        
    except Exception as e:
        print(f"Error fetching thumbnail: {str(e)}")

# Function to display video titles in the playlist
def display_playlist_video_titles(video_titles, playlist_title):
    # Frame for list of videos
    playlist_videos_frame.pack()

    # Playlist title label
    playlist_title_label.configure(text=playlist_title)
    playlist_title_label.pack(side="top", pady=("10p", "0p"), padx=("2p", "0p"))

    # Iterate each playlist video/create video title
    for index, video_title in enumerate(video_titles, start=1):
        video_title_frame.pack(side="top", fill="x", pady=("5p", "5p"))

        # Video title label with numbering
        numbered_video_title = f"{index}. {video_title}"
        video_title_label = ctk.CTkLabel(video_title_frame, text=numbered_video_title, text_color="white", padx=10, pady=10, bg_color="#333333", font=list_font, wraplength=380, justify="left")
        video_title_label.pack(pady=1, anchor="w")

# Handle fetch results for playlist
def handle_fetch_playlist_results(formats):
    # Hide the "Checking..." label
    hide_labels()

    # Update combobox values with available formats
    update_combobox(formats)

    # Show the resolutions combobox
    resolution_combobox.pack(side="left", padx=5)

    # Remove thumbnail text
    thumbnail_label.configure(text="")

# Handle fetch results single video
def handle_video_fetch_results(formats, video_title, video_info):
    # Hide the "Checking..." label
    hide_labels()

    # Update combobox values with available formats
    update_combobox(formats)

    # Show the resolutions combobox
    resolution_combobox.pack(side="left", padx=5)

    # Ensure that the playlist_title_label is not displayed
    playlist_title_label.pack_forget()

    # Hide the playlist_videos_frame
    playlist_videos_frame.pack_forget()

    # Fetch and display the video thumbnail
    thumbnail_url = video_info.get('thumbnail')
    if thumbnail_url:
        fetch_thumbnail_async(thumbnail_url)

        # Set the video name in the thumbnail_label
        video_name = video_title
        thumbnail_label.configure(text=video_name)

# Display video thumbnail
def display_thumbnail(thumbnail):
    if thumbnail:
        thumbnail_label.configure(image=thumbnail)
        thumbnail_label.image = thumbnail  # Keep a reference to the image
        thumbnail_label.pack(pady=("10p", "5p"))

# Update combobox values
def update_combobox(values):
    resolution_combobox['values'] = values
    resolution_var.set(values[0])  # Set the default format

# Set the state of UI elements
def set_elements_state(state):
    entry_url["state"] = state
    resolution_combobox["state"] = state
    fetch_button["state"] = state
    download_button["state"] = state

# Set the state of the download button
def set_download_button_state(state):
    download_button["state"] = state

# Function to smoothly transition from single video to playlist UI
def transition_to_playlist_ui():
    # Hide elements related to single video download
    thumbnail_label.configure(text="")

    # Show elements related to playlist download
    playlist_title_label.pack(side="top", pady=("10p", "0p"), padx=("2p", "0p"))
    playlist_videos_frame.pack()

# Function to smoothly transition from playlist to single video UI
def transition_to_single_video_ui():
    # Hide elements related to playlist download
    playlist_title_label.pack_forget()
    playlist_videos_frame.pack_forget()

    # Show elements related to single video download
    thumbnail_label.pack(pady=("10p", "5p"))

# Download function
def download():
    print("Download function called.")
    global download_in_progress

    if not download_in_progress:
        print("Starting download...")
        # Show progress elements immediately when download starts
        speed_label.pack(pady=("5p", "5p"))
        progress_label.pack(pady=("5p", "5p"))
        progress_bar.pack(pady=("10p", "5p"))
        status_label.pack(pady=("5p", "5p"))
        time_label.pack(pady=("5p", "5p"))

        # Disable only the download button during download
        download_button["state"] = "disabled"

        # Set download_in_progress to True
        download_in_progress = True

        # Reset UI to initial state
        progress_bar["value"] = 0.0
        progress_label.configure(text="Percentage: 0%", text_color="white")
        status_label.configure(text="Downloading...", text_color="white")

        try:
            url = entry_url.get()

            if is_playlist_link(url):
                format_selection = resolution_combobox.get()
                playlist_info = fetch_playlist_info_async(url)
                playlist_title = playlist_info.get('title')

                # Call the transition function
                root.after(0, transition_to_playlist_ui)
                
                # Download playlist
                download_playlist(url, format_selection, playlist_title)

            else:
                format_selection = resolution_var.get().split(' - ')[0]

                # Call the transition function
                root.after(0, transition_to_single_video_ui)
                
                # Fetch video information asynchronously
                video_info = fetch_video_info_async(url)

                # Get single video title
                video_title = video_info.get('title')

                # Download single video
                download_single_video(url, format_selection, video_title)

        except Exception as e:
            root.after(0, lambda: status_label.configure(text=f"Error {str(e)}", text_color="white"))

# Download single video function
def download_playlist(url, format_selection, playlist_title):
    # Map "AU" to "bestaudio" and "AV" to "best"
    if format_selection == "Audio":
        format_selection = "bestaudio"
    elif format_selection == "Video":
        format_selection = "best"

    try:
        playlist_info = fetch_playlist_info_async(url)

        # Create a new folder in the "downloads" directory with the playlist title
        playlist_folder = os.path.join("downloads", playlist_title)
        os.makedirs(playlist_folder, exist_ok=True)

        # Create a thread for downloading the entire playlist
        download_thread = create_playlist_download_thread(url, format_selection, playlist_folder)
        download_thread.start()

        # Check the status of the download thread
        root.after(0, lambda: check_download_thread_status(download_thread, playlist_info))

    except Exception as e:
        status_label.configure(text=f"Error {str(e)}", text_color="white")

# Worker function for downloading the entire playlist
def download_playlist_worker(url, format_selection, playlist_folder):
    try:
        ydl_opts = {
                'format': format_selection,
                'outtmpl': os.path.join(playlist_folder, f"%(title)s.%(ext)s"),
                'postprocessors': [],
                'progress_hooks': [on_progress]
            }
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

    except Exception as e:
        status_label.configure(text=f"Error {str(e)}", text_color="white")

# Download single video function
def download_single_video(url, format_selection, video_title):
    try:
        ydl_opts = {
            'format': f"{format_selection}+bestaudio" if 'audio' not in format_selection else format_selection,
            'outtmpl': os.path.join("downloads", f"{video_title}_{format_selection}.%(ext)s"),
            'postprocessors': [],
            'progress_hooks': [on_progress]
        }

        # Create a thread for downloading a single video
        download_thread = create_download_thread(url, ydl_opts)
        download_thread.start()

        # Check the status of the download thread
        root.after(0, lambda: check_download_thread_status(download_thread, None))

    except Exception as e:
        status_label.configure(text=f"Error {str(e)}", text_color="white")

# Worker function for downloading a single video
def download_single_video_worker(url, ydl_opts):
    try:
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

    except Exception as e:
        status_label.configure(text=f"Error {str(e)}", text_color="white")

# Create a thread for downloading a single video
def create_download_thread(url, ydl_opts):
    return threading.Thread(target=lambda: download_single_video_worker(url, ydl_opts))

# Create a thread for downloading the entire playlist
def create_playlist_download_thread(url, format_selection, playlist_folder):
    return threading.Thread(target=lambda: download_playlist_worker(url, format_selection, playlist_folder))

# Check download thread status
def check_download_thread_status(download_thread, playlist_info):
    global download_in_progress

    if download_thread.is_alive():
        # If the thread is still alive, check again after 100 milliseconds
        root.after(100, lambda: check_download_thread_status(download_thread, playlist_info))
    else:
        # Check if download is already marked as complete
        if not download_in_progress:
            return

        # Set download_in_progress to False
        download_in_progress = False

        # Call the appropriate callback function for playlist download
        root.after(0, lambda: download_complete_callback())

# Callback function when playlist download is complete
def download_complete_callback():
    try:
        # Update UI elements
        progress_bar["value"] = 100.0
        progress_label.configure(text="Percentage: 100%")

    except Exception as e:
        status_label.configure(text=f"Error {str(e)}", text_color="white")
    finally:
        progress_bar["value"] = 100.0
        progress_label.configure(text="Percentage: 100%")
        status_label.configure(text="Download Successful!", text_color="white")

        # Reset the download_in_progress flag to False
        global download_in_progress
        download_in_progress = False

        # Re-enable the download button on the main thread
        root.after(0, lambda: download_button.configure(state="normal"))

        # Schedule the function to reset progress_bar and progress_label after 5 seconds
        root.after(5000, reset_progress_elements)
        # Schedule the function to hide the status_label after 5 seconds
        root.after(5000, hide_status_label)

# Handle progress updates during download
def on_progress(info):
    if info.get('status') == 'downloading':
        downloaded_bytes = info.get('downloaded_bytes') or 0
        if 'total_bytes' in info:
            total_bytes = info['total_bytes']
        else:
            total_bytes = info.get('total_bytes_estimate', -1)

        if total_bytes > 0:
            percentage_completed = (downloaded_bytes / total_bytes) * 100
            remaining_bytes = total_bytes - downloaded_bytes
            download_speed = info.get('speed') or 0

            # Convert download speed to kilobytes per second
            download_speed_kb = download_speed / 1024

            # Calculate ETA
            if download_speed > 0:
                eta_seconds = remaining_bytes / download_speed
                eta_str = format_eta(eta_seconds)
            else:
                eta_str = "Calculating ETA..."

            # Update progress elements on the main thread
            root.after(0, lambda: update_progress_elements(percentage_completed, download_speed_kb, eta_str))

# Format ETA into HH:MM:SS
def format_eta(seconds):
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return "{:02}:{:02}:{:02}".format(int(hours), int(minutes), int(seconds))

# Update progress elements on the UI
def update_progress_elements(percentage_completed, download_speed, eta_str):
    progress_bar["value"] = percentage_completed
    progress_label.configure(text=f"Percentage: {int(percentage_completed)}%")
    
    # Update download speed label to display in KB/s
    speed_label.configure(text=f"Download Speed: {download_speed:.2f} KB/s")
    
    time_label.configure(text=f"Time: {eta_str}")

# Function to hide the status_label
def hide_status_label():
    status_label.pack_forget()

def reset_progress_elements():
    speed_label.configure(text="Download Speed: 0.00 KB/s")

# Function to say text using gTTS
def say_text(text):
    tts = gTTS(text=text, lang='en')  # Adjust the language as needed
    tts.save('temp.mp3')
    os.system('mpg321 temp.mp3')  # Make sure 'mpg321' is installed on your system
    os.remove('temp.mp3')

# ...

# Settings Tab Content Frame
settings_content_frame = ttk.Frame(settings_tab, style="Dark.TFrame" if mode == "dark" else "Light.TFrame")
settings_content_frame.pack(fill=ctk.BOTH, expand=True)

# Settings title
settings_label = ctk.CTkLabel(settings_content_frame, text="Settings", text_color="white", padx=10, pady=10, bg_color="#333333", font=custom_font)
settings_label.pack(side="left", anchor="nw", pady=("15p","5p"), padx=("15p","0p"))


# ...

# Help Tab Content Frame
help_content_frame = ttk.Frame(help_tab, style="Dark.TFrame" if mode == "dark" else "Light.TFrame")
help_content_frame.pack(fill=ctk.BOTH, expand=True)

# Help & FAQs title
help_label = ctk.CTkLabel(help_content_frame, text="Help & FAQs", text_color="white", padx=10, pady=10, bg_color="#333333", font=custom_font)
help_label.pack(side="left", anchor="nw", pady=("15p","5p"), padx=("15p","0p"))

# ...

# About Tab Content Frame
about_content_frame = ttk.Frame(about_tab, style="Dark.TFrame" if mode == "dark" else "Light.TFrame")
about_content_frame.pack(fill=ctk.BOTH, expand=True)

# About us title
about_title_label = ctk.CTkLabel(about_content_frame, text="About Us", text_color="white", padx=10, pady=10, bg_color="#333333", font=custom_font)
about_title_label.pack(side="left", anchor="nw", pady=("15p","5p"), padx=("15p","0p"))

# ...

# Feedback Tab Content Frame
feedback_content_frame = ttk.Frame(feedback_tab, style="Dark.TFrame" if mode == "dark" else "Light.TFrame")
feedback_content_frame.pack(fill=ctk.BOTH, expand=True)

# Feedback and support title
fs_label = ctk.CTkLabel(feedback_content_frame, text="Feedback & Support", text_color="white", padx=10, pady=10, bg_color="#333333", font=custom_font)
fs_label.pack(side="left", anchor="nw", pady=("15p","5p"), padx=("15p","0p"))


# Start the app
root.mainloop()
