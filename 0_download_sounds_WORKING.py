#!/usr/bin/env python3
"""
Working Sound Downloader - Multiple Sources
Downloads woodpecker and predator sounds from YouTube and direct sources
"""
import os
import subprocess
import time
from pathlib import Path

SOUNDS_DIR = "static/sounds"

# YouTube videos with bird sounds
YOUTUBE_SOURCES = {
    "woodpecker_drumming": [
        "https://www.youtube.com/watch?v=wSM0YS_72NE",  # Great Spotted Woodpecker drumming
        "https://www.youtube.com/watch?v=Vp47VpjN6xQ",  # Woodpecker drumming compilation
        "https://www.youtube.com/watch?v=5PXSK7rLqSQ",  # Drumming sounds
    ],
    "woodpecker_calls": [
        "https://www.youtube.com/watch?v=I7GHoSUPZHw",  # Woodpecker calls
        "https://www.youtube.com/watch?v=XuG4Bl1fB3k",  # Various woodpecker sounds
    ],
    "predator_hawk": [
        "https://www.youtube.com/watch?v=NVBxLXyleyQ",  # Red-tailed Hawk
        "https://www.youtube.com/watch?v=33DWqRyAAUw",  # Hawk sounds
    ],
    "predator_owl": [
        "https://www.youtube.com/watch?v=ezaBqCf0hv0",  # Tawny Owl
        "https://www.youtube.com/watch?v=R5iRcWmfhNg",  # Great Horned Owl
    ],
    "predator_buzzard": [
        "https://www.youtube.com/watch?v=S8vCFBGqLxc",  # Common Buzzard
        "https://www.youtube.com/watch?v=IKHGd1YYhAo",  # Buzzard calls
    ]
}

def download_from_youtube(url, output_dir, filename):
    """Download audio from YouTube using yt-dlp"""
    try:
        output_path = os.path.join(output_dir, filename)

        # yt-dlp command to extract audio as mp3
        cmd = [
            "/opt/homebrew/bin/yt-dlp",
            "-x",  # Extract audio
            "--audio-format", "mp3",
            "--audio-quality", "0",  # Best quality
            "-o", output_path,
            "--max-filesize", "10M",  # Limit file size
            "--max-downloads", "1",
            "--no-playlist",
            url
        ]

        print(f"   Downloading from {url[:50]}...")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

        # yt-dlp adds .mp3 extension automatically
        expected_file = output_path + ".mp3"
        if os.path.exists(expected_file):
            print(f"   ✅ Downloaded: {filename}.mp3")
            return True
        elif os.path.exists(output_path):
            print(f"   ✅ Downloaded: {filename}")
            return True
        else:
            print(f"   ⚠️  Download may have failed for {url}")
            return False

    except subprocess.TimeoutExpired:
        print(f"   ⏱️  Timeout for {url}")
        return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def main():
    print("""
    ╔══════════════════════════════════════════════════════════╗
    ║        🎵 SOUND DOWNLOADER - WORKING VERSION            ║
    ║           Downloading from YouTube + Direct             ║
    ╚══════════════════════════════════════════════════════════╝
    """)

    # Create directories
    for category in YOUTUBE_SOURCES.keys():
        dir_path = os.path.join(SOUNDS_DIR, category)
        os.makedirs(dir_path, exist_ok=True)

    total_downloaded = 0

    # Download from YouTube
    for category, urls in YOUTUBE_SOURCES.items():
        print(f"\n{'='*60}")
        print(f"📂 Category: {category.upper()}")
        print(f"{'='*60}")

        output_dir = os.path.join(SOUNDS_DIR, category)

        for i, url in enumerate(urls):
            filename = f"{category}_{i+1:02d}"

            if download_from_youtube(url, output_dir, filename):
                total_downloaded += 1
                time.sleep(2)  # Be nice to YouTube
            else:
                time.sleep(1)

    print(f"""
    ╔══════════════════════════════════════════════════════════╗
    ║                  ✅ DOWNLOAD COMPLETE                    ║
    ╠══════════════════════════════════════════════════════════╣
    ║  📦 Total files:  {total_downloaded:2d} sounds                              ║
    ║  📂 Categories:   5                                      ║
    ╚══════════════════════════════════════════════════════════╝

    ✅ Zvuky staženy z YouTube!
    ✅ Server může nyní přehrávat reakce na detekci!

    Další krok: ./venv/bin/python3 4_main_app_with_sounds.py
    """)

if __name__ == "__main__":
    main()
