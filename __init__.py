import getpass
import re
import subprocess
from concurrent.futures import as_completed
from concurrent.futures.thread import ThreadPoolExecutor

import requests
import m3u8

print("Program Started")

# Load playlist
ffmpeg_path = rf"C:\Users\{getpass.getuser()}\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg.Essentials_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-7.1.1-essentials_build\bin\ffmpeg.exe"

# token = "sjwt=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1cmlfc3ViIjoiLzg3MDdmZjk1LWNhNjctMjE1Ny0wNDVjLWQ4Mjc4YWFkODVkYi8iLCJ1aWQiOiIwMTk3YmU1Zi1jZGE0LTc0MDEtYTczZi0zYmNlYzUxOWQwODIiLCJyYXUiOm51bGwsImJleSI6ZmFsc2UsImlpcCI6ZmFsc2UsIm5iZiI6MTc1MTI0NTYzOSwiaWF0IjoxNzUxMjQ1NjM5LCJleHAiOjE3NTEzMzIwMzksImp0aSI6IjAxOTdiZTVmLWNkYTQtNzQwMS1hNzNmLTNiY2VjNTE5ZDA4MiIsImlzcyI6IlNwYWxsYSJ9.99LJXl2iNbsoW8_cxcvAD3wvIjFXOfC7eyczTt0-tbo"

classes = {
    # "FileName":    "http link .m3u8",
}

num_threads = 8  # Tune this based on your connection and CPU

output_ts = "combined.ts"

for name, url in classes.items():
    print(f"Searching for playlist {name}...")

    # m3u8_obj = m3u8.load(f"{url}?{token}")
    m3u8_obj = m3u8.load(url)

    segment_urls = [segment.absolute_uri for segment in m3u8_obj.segments]

    # Download function
    def download_segment(index_url_tuple):
        index, url = index_url_tuple
        try:
            r = requests.get(url, timeout=10)
            r.raise_for_status()
            return index, r.content
        except Exception as e:
            print(f"Failed to download segment {index}: {e}")
            return index, b''

    downloaded_segments = [None] * len(segment_urls)

    print("Downloading...")
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        future_to_index = {
            executor.submit(download_segment, (i, u)): i for i, u in enumerate(segment_urls)
        }
        for future in as_completed(future_to_index):
            idx, data = future.result()
            downloaded_segments[idx] = data

    if m3u8_obj.keys and any(k for k in m3u8_obj.keys):
        print("[WARNING] Playlist uses encryption. Decryption is required.")
        continue  # or handle decryption logic here

    # Combine segments
    with open(output_ts, "wb") as f:
        for data in downloaded_segments:
            if data:
                f.write(data)

    print("Downloaded successfully!")

    # Step 2: Convert to MP4 using ffmpeg
    name = re.sub(r'[<>:"/\\|?*]', '', name)
    print(f"Converting to MP4...")
    try:
        subprocess.run([
            ffmpeg_path, "-y",  # Overwrite output file
            "-i", output_ts,
            "-c", "copy",
            f"{name}.mp4"
        ],
            shell=True,
            check=True
        )
        print(f"Conversion successful! Saved as: {name}")
    except subprocess.CalledProcessError as e:
        print("ffmpeg failed:", e)
