import threading
import os
import shutil
from typing import Optional, Dict, List, Any, Callable
from .settings import current_settings

def get_ffmpeg_location():
    """Find FFmpeg binary, works in both dev and bundled app contexts."""
    # 1. Check system PATH first
    ffmpeg_path = shutil.which('ffmpeg')
    if ffmpeg_path:
        return ffmpeg_path
    
    # 2. Check common Linux paths when PATH lookup fails (e.g., in bundled apps)
    common_paths = ['/usr/bin/ffmpeg', '/usr/local/bin/ffmpeg', '/snap/bin/ffmpeg']
    for path in common_paths:
        if os.path.isfile(path) and os.access(path, os.X_OK):
            return path
    
    # 3. FFmpeg not found - return None (yt-dlp will try to proceed)
    return None

def fetch_video_info(url: str) -> Dict[str, Any]:
    from yt_dlp import YoutubeDL
    ydl_opts = {
        'quiet': True, 
        'skip_download': True,
        'js_runtimes': {'node': {}},
        'retries': 3
    }
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        return info

def fetch_playlist_info(url: str) -> Dict[str, Any]:
    from yt_dlp import YoutubeDL
    ydl_opts = {
        'quiet': True, 
        'extract_flat': True, 
        'skip_download': True,
        'js_runtimes': {'node': {}},
        'retries': 3
    }
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        return info

def on_progress_hook(d, callback, cancel_callback=None):
    # Check Cancel
    if cancel_callback and cancel_callback():
        raise Exception("Download Cancelled by User")

    if d['status'] == 'downloading':
        # Enrich with inferred content type (Video vs Audio)
        # Note: 'format_note' often contains 'video only' or 'audio only'
        # 'vcodec' != 'none' usually means video.
        
        # Check info_dict if available
        info_dict = d.get('info_dict', {})
        vcodec = info_dict.get('vcodec', 'none')
        acodec = info_dict.get('acodec', 'none')
        
        # Heuristic detection
        content_type = "Content"
        if vcodec != 'none' and acodec == 'none':
            content_type = "Video"
        elif acodec != 'none' and vcodec == 'none':
            content_type = "Audio"
        
        # Inject this into the dictionary for UI to use
        d['_content_type'] = content_type
        
        if callback:
            callback(d)

def on_postprocessor_hook(d, callback):
    # Detect Merging
    if d['status'] == 'started':
        # Check if it's the Merger or FFmpeg postprocessor
        pp_name = d.get('postprocessor')
        if pp_name in ['Merger', 'FFmpegMerger']:
            info = {'status': 'merging', 'msg': 'Merging Video & Audio...'}
            if callback:
                callback(info)



def download_worker(url: str, opts: Dict[str, Any], progress_callback: Callable, complete_callback: Callable, error_callback: Callable, cancel_callback: Optional[Callable] = None):
    from yt_dlp import YoutubeDL
    from yt_dlp.utils import DownloadError
    try:
        # Inject progress hook & postprocessor hook with cancel check
        opts['progress_hooks'] = [lambda d: on_progress_hook(d, progress_callback, cancel_callback)]
        opts['postprocessor_hooks'] = [lambda d: on_postprocessor_hook(d, progress_callback)]
        
        with YoutubeDL(opts) as ydl:
            ydl.download([url])
        
        if complete_callback:
            complete_callback()

    except Exception as e:
        msg = str(e)
        if "Download Cancelled" in msg:
             if error_callback: error_callback("Cancelled") # Special handling or just "Cancelled"
        elif isinstance(e, DownloadError):
             if error_callback:
                clean_msg = msg.replace('ERROR: ', '')
                error_callback(f"Download Failed: {clean_msg}")
        else:
             if error_callback:
                error_callback(f"System Error: {msg}")

def start_download_thread(url, opts, progress_callback, complete_callback, error_callback, cancel_callback=None):
    t = threading.Thread(target=download_worker, args=(url, opts, progress_callback, complete_callback, error_callback, cancel_callback))
    t.daemon = True
    t.start()
    return t

# Function to construct yt-dlp options based on settings and user choices
def build_ydl_opts(path, format_key, noplaylist=True, trim_range=None):
    opts = {
        'outtmpl': os.path.join(path, f"%(title)s.%(ext)s"),
        'noplaylist': noplaylist,
        'ignoreerrors': True,
        # Robustness & Performance
        'retries': 15,
        'fragment_retries': 15,
        'socket_timeout': 15, # Force timeout on stalled connections
        'http_chunk_size': 10485760, # 10MB chunks to prevent small-chunk overhead
        # 'concurrent_fragment_downloads': 4, # Removed for stability
        # Explicitly enable Node.js for signature extraction to avoid throttling
        'js_runtimes': {'node': {}}, 
        # Merging
        'merge_output_format': 'mp4',
        'remote_components': {'ejs:github'}, # Fixes 'n challenge' warning completely
        # 'postprocessor_args': {'ffmpeg': ['-c:a', 'aac']}, # Removed re-encode for stability. Trust format selector.
        'prefer_ffmpeg_merge': True, # Ensure ffmpeg is used
        'ffmpeg_location': get_ffmpeg_location(), # Robust path lookup for bundled apps
    }

    # Format Selection Logic
    # Key Format: 'type_quality' (e.g., mp3_320, wav, 4k)
    fmt_parts = format_key.split('_')
    base_fmt = fmt_parts[0]
    quality = fmt_parts[1] if len(fmt_parts) > 1 else '192'

    if base_fmt == 'mp3':
        opts['format'] = 'bestaudio/best'
        opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': quality,
        }]
    elif base_fmt == 'wav':
        opts['format'] = 'bestaudio/best'
        opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'wav',
        }]
    elif base_fmt == 'gif':
        # GIF conversion: Video only
        opts['format'] = 'bestvideo[height<=720]/bestvideo' # Limit calc for GIF size
        opts['postprocessors'] = [{
            'key': 'FFmpegVideoConvertor',
            'preferedformat': 'gif',
        }]
    elif format_key == 'm4a':
        opts['format'] = 'bestaudio[ext=m4a]/best'
    elif format_key == '4k':
        opts['format'] = 'bestvideo[height=2160][vcodec^=avc1]+bestaudio[acodec^=mp4a]/bestvideo[height=2160]+bestaudio/bestvideo[vcodec^=avc1]+bestaudio/best'
    elif format_key == '1080p':
        opts['format'] = 'bestvideo[height=1080][vcodec^=avc1]+bestaudio[acodec^=mp4a]/bestvideo[height=1080]+bestaudio/bestvideo[height<=1080][vcodec^=avc1]+bestaudio/best'
    elif format_key == '720p':
        opts['format'] = 'bestvideo[height=720][vcodec^=avc1]+bestaudio[acodec^=mp4a]/bestvideo[height=720]+bestaudio/bestvideo[height<=720][vcodec^=avc1]+bestaudio/best'
    elif format_key == '480p':
        opts['format'] = 'bestvideo[height=480][vcodec^=avc1]+bestaudio[acodec^=mp4a]/bestvideo[height=480]+bestaudio/bestvideo[height<=480][vcodec^=avc1]+bestaudio/best'
    else:
        # Fallback / Custom (Best Quality)
        # Explicit priority for H.264 (avc1) to avoid AV1 playback issues on some players
        opts['format'] = 'bestvideo[vcodec^=avc1]+bestaudio[acodec^=mp4a]/bestvideo[height<=1080][vcodec^=avc1]+bestaudio/bestvideo+bestaudio/best' 
        
    # Security: Restrict filenames to ASCII to prevent filesystem issues
    opts['restrictfilenames'] = True 

    if trim_range:
        start_sec, end_sec = trim_range
        def ranges_callback(info_dict, ydl):
            return [{'start_time': start_sec, 'end_time': end_sec}]
        opts['download_ranges'] = ranges_callback
        # Force re-encoding if trimming to ensure accuracy
        opts['force_keyframes_at_cuts'] = True

    # Modern settings
    settings = current_settings
    if settings.get("embed_thumbnail"): opts['writethumbnail'] = True
    if settings.get("embed_metadata"): opts['addmetadata'] = True
    if settings.get("download_subtitles"): opts['writesubtitles'] = True
    if settings.get("proxy_url"): opts['proxy'] = settings["proxy_url"]
    if settings.get("speed_limit"): opts['ratelimit'] = settings["speed_limit"]
    if settings.get("cookies_path") and os.path.exists(settings["cookies_path"]): 
        opts['cookiefile'] = settings["cookies_path"]

    return opts

def check_formats(url):
    """Helper to check available formats for a URL before downloading."""
    try:
        from yt_dlp import YoutubeDL
        ydl_opts = {'quiet': True, 'skip_download': True}
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return info.get('formats', [])
    except:
        return []
