# BecomeDeath's YT-Converter

A small Windows desktop app for downloading YouTube videos or extracting audio. It runs **locally** on your PC using [yt-dlp](https://github.com/yt-dlp/yt-dlp) and optional [FFmpeg](https://ffmpeg.org/) for merging and audio conversion.

## Features

- **Formats:** MP4, WebM, MP3, WAV  
- **Video quality:** presets from 360p up to best available (including 4K when offered)  
- **MP4 audio:** re-encoded to **AAC (192 kbps)** on merge for reliable playback in common Windows players (avoids Opus-in-MP4 issues).  
- **Activity log** with timestamps and coarse download progress.

## Requirements

- **Windows 10 or later** (the provided build is a `.exe`).  
- **FFmpeg** - required for:
- merging separate video + audio into **MP4** or **WebM**  
- **MP3** / **WAV** extraction  

If FFmpeg is missing, the app will warn you and those modes will not work until FFmpeg is available.

### Where FFmpeg is looked for

1. **`YOUTUBEGRAB_FFMPEG`** environment variable — path to `ffmpeg.exe` or to a folder that contains it (or `bin\ffmpeg.exe`).  
2. **`ffmpeg` on your PATH**  
3. **`ffmpeg.exe` next to the application** (same folder as the `.exe`)  
4. Under a folder named like **`ffmpeg-*`** next to the app, with `bin\ffmpeg.exe` inside (typical full build layout).

## Running from source

1. Install [Python 3.11+](https://www.python.org/downloads/) (check “Add Python to PATH” on Windows).  
2. In this folder:

   ```text
   pip install -r requirements.txt
   python make_icon.py
   python main.py
   ```

## Building the standalone `.exe`

1. Put **`ffmpeg.exe`** in this project folder (the spec bundles it next to the built executable).  
2. Run **`build_exe.bat`**. It installs dependencies, generates **`app_icon.ico`** / **`app_icon.png`**, and runs PyInstaller.  
3. Output: **`dist\BecomeDeathsYTConverter.exe`**

If the taskbar or Explorer icon looks stale after a rebuild, rename the `.exe` once or sign out and back in; Windows caches icons aggressively.

## Usage

1. Paste a **YouTube** URL.  
2. Choose **output folder** (defaults to your Downloads folder).  
3. Pick **format** (MP4 / WebM / MP3 / WAV) and **quality**.  
4. Click **Download** and watch the status line and activity log.

Only single videos are targeted (`noplaylist`); playlists are not downloaded as a batch from this UI.

## Legal note

Only download or convert content you are **allowed** to save (copyright, terms of service, and local laws apply). This tool is a technical convenience; you are responsible for how you use it.

## Troubleshooting

| Issue | What to try |
|--------|-------------|
| “FFmpeg not found” | Install FFmpeg, add it to PATH, or set `YOUTUBEGRAB_FFMPEG`, or copy `ffmpeg.exe` beside the `.exe`. |
| Download fails | Check the activity log; update yt-dlp (`pip install -U yt-dlp`) if YouTube changes often break older versions. |
| MP4 has no sound | Often a player codec issue; this app re-encodes audio to AAC for MP4 merges to reduce that. |

## License

Respect the licenses of **yt-dlp**, **CustomTkinter**, **FFmpeg**, and any content you download.
