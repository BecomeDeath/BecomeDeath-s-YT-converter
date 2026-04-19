# Help — BecomeDeath's YT-Converter (standalone `.exe`)

This file is for people running the **built Windows executable**, not the Python source tree.

## First launch

- **Windows SmartScreen** may say the app is from an “unknown publisher.” That is normal for unsigned builds. You can still choose “More info” → “Run anyway” if you trust the file.
- The **installer** (`BecomeDeathsYTConverterSetup.exe`) must sit in the **same folder** as the **`BecomeDeathsYTConverter`** directory (the one that contains `BecomeDeathsYTConverter.exe`). If you only copied the setup program, it will say it cannot find that folder.

## Common errors and what to do

### “FFmpeg not found” or merge / MP3 / WAV fails

The app needs **FFmpeg** to merge video+audio and to export MP3/WAV.

**Fix:** Install FFmpeg and either:

- add its folder to your **PATH**, or  
- set the environment variable **`YOUTUBEGRAB_FFMPEG`** to the full path of `ffmpeg.exe` or to the folder that contains it (or `bin\ffmpeg.exe` under a full FFmpeg tree), or  
- copy **`ffmpeg.exe`** into the **same folder** as `BecomeDeathsYTConverter.exe`, or  
- put a folder named like **`ffmpeg-*`** next to the app with `bin\ffmpeg.exe` inside.

If your build was made **without** bundling FFmpeg, you must do one of the above.

### “Output folder does not exist”

The path in the UI is not a valid directory (typo, drive missing, or folder was deleted).

**Fix:** Click **Browse** and pick an existing folder (e.g. Downloads).

### Download fails, “Video unavailable”, “Private video”, HTTP 403, or similar

Usually the **URL**, **region**, **age restriction**, or **YouTube / yt-dlp** changes.

**Fix:** Confirm the video plays in a browser while logged in (if it needs an account, this app does not log you in). Update yt-dlp if you run from source (`pip install -U yt-dlp`). For a frozen `.exe`, you need a **rebuild** from the maintainer with a newer yt-dlp.

### Very slow start of the `.exe` (one-file builds)

A single-file PyInstaller build extracts to a temp folder on each run; first launch can feel slow. This project’s default release layout is **onedir** (a folder + `.exe`), which starts faster.

### Taskbar / Explorer shows the wrong icon

Windows **caches** icons aggressively.

**Fix:** Rename the `.exe` once, or sign out and back in, or clear the icon cache (search for instructions for your Windows version).

### Antivirus quarantines the `.exe`

Some scanners flag PyInstaller apps as generic “PUA” or trojan-like.

**Fix:** Restore the file from quarantine and add an **exclusion** for the install folder if your AV product allows it. Only do this if you trust the publisher.

### “Could not find BecomeDeathsYTConverter” (setup wizard)

The installer only copies files; it does not download the app from the internet. It looks for a sibling folder named **`BecomeDeathsYTConverter`** containing **`BecomeDeathsYTConverter.exe`**.

**Fix:** Extract your zip so both the setup `.exe` and that folder sit together, then run setup again.

### Install says the folder already exists

The wizard refuses to overwrite an existing install directory.

**Fix:** Delete or rename the old **`BecomeDeathsYTConverter`** folder under the path you chose, or pick another location.

### Disk full or “Access denied” during install

Copying the app needs several hundred MB free. Installing under **`Program Files`** may require running the setup **as Administrator**.

**Fix:** Free disk space, run as admin, or install under your user profile (e.g. `Documents\BecomeDeathsYTConverter`).

## Legal reminder

Only download content you are **allowed** to save. You are responsible for copyright, site terms, and local law.
