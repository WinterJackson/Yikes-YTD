
import sys
import os
import unittest
from unittest.mock import patch, MagicMock

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from logic.utils import parse_time_to_seconds, format_eta
from logic.downloader import build_ydl_opts

class TestUtils(unittest.TestCase):
    def test_parse_seconds(self):
        self.assertEqual(parse_time_to_seconds("01:30"), 90)
        self.assertEqual(parse_time_to_seconds("1:00:00"), 3600)
        self.assertEqual(parse_time_to_seconds("45"), 45)
        self.assertIsNone(parse_time_to_seconds("invalid"))

    def test_format_eta(self):
        self.assertEqual(format_eta(3661), "01:01:01")
        self.assertEqual(format_eta(65), "00:01:05")
        self.assertEqual(format_eta(None), "Unknown")

class TestDownloaderOpts(unittest.TestCase):
    
    @patch("logic.downloader.current_settings", {"download_path": "/tmp"})
    def test_format_parsing_mp3_320(self):
        opts = build_ydl_opts("/tmp", "mp3_320")
        
        # Check Postprocessors
        pp = opts.get('postprocessors', [])
        found = False
        for p in pp:
            if p['key'] == 'FFmpegExtractAudio' and p['preferredquality'] == '320':
                found = True
        self.assertTrue(found, "MP3 320k config missing")
        self.assertEqual(opts['format'], 'bestaudio/best')

    @patch("logic.downloader.current_settings", {"download_path": "/tmp"})
    def test_format_parsing_wav(self):
        opts = build_ydl_opts("/tmp", "wav")
        pp = opts.get('postprocessors', [])
        self.assertTrue(any(p['preferredcodec'] == 'wav' for p in pp))

    @patch("logic.downloader.current_settings", {"download_path": "/tmp"})
    def test_format_parsing_gif(self):
        opts = build_ydl_opts("/tmp", "gif")
        pp = opts.get('postprocessors', [])
        self.assertTrue(any(p['key'] == 'FFmpegVideoConvertor' and p['preferedformat'] == 'gif' for p in pp))
        self.assertIn("height<=720", opts['format'])

    @patch("logic.downloader.current_settings", {"download_path": "/tmp"})
    def test_format_parsing_video_1080p(self):
        opts = build_ydl_opts("/tmp", "1080p")
        self.assertIn("height=1080", opts['format'])

if __name__ == '__main__':
    unittest.main()
