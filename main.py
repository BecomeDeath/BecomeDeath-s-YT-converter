"""BecomeDeath's YT-Converter: local YouTube grabber using yt-dlp.

MP4 merges re-encode audio to AAC (Windows players often choke on Opus-in-MP4).
FFmpeg is picked up from PATH, YOUTUBEGRAB_FFMPEG, next to the executable, or a ffmpeg-*/bin layout.
"""

from __future__ import annotations

import os
import shutil
import sys
import threading
import traceback
import tkinter as tk
from datetime import datetime
from pathlib import Path

import customtkinter as ctk
from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError

APP_NAME = "BecomeDeath's YT-Converter"
APP_TAGLINE = "Download or convert YouTube links on your machine."

# Modern neutral dark theme
C_BG = "#0c0c0f"
C_SURFACE = "#141418"
C_SURFACE_ELEVATED = "#1a1a20"
C_BORDER = "#2e2e38"
C_BORDER_SUBTLE = "#232328"
C_TEXT = "#f4f4f5"
C_TEXT_MUTED = "#8b8b98"
C_ACCENT = "#e84855"
C_ACCENT_HOVER = "#ff5c6a"
C_FIELD = "#1e1e26"
C_WARN = "#fbbf24"
C_LOG_BG = "#0a0a0d"
C_LOG_TEXT = "#c4c4ce"
C_TRACK = "#2a2a32"
C_FILL = C_ACCENT

VIDEO_QUALITIES: list[tuple[str, int | None]] = [
    ("Best (merge streams)", None),
    ("2160p (4K)", 2160),
    ("1440p", 1440),
    ("1080p", 1080),
    ("720p", 720),
    ("480p", 480),
    ("360p", 360),
]

AUDIO_BITRATE_LABELS: list[tuple[str, str]] = [
    ("320 kbps", "320"),
    ("256 kbps", "256"),
    ("192 kbps", "192"),
    ("160 kbps", "160"),
    ("128 kbps", "128"),
    ("96 kbps", "96"),
    ("64 kbps", "64"),
]

SEGMENT_LABELS = ["MP4", "WebM", "MP3", "WAV"]
SEGMENT_TO_KIND = {"MP4": "mp4", "WebM": "webm", "MP3": "mp3", "WAV": "wav"}
KIND_TO_SEGMENT = {v: k for k, v in SEGMENT_TO_KIND.items()}


def default_download_dir() -> Path:
    home = Path.home()
    for name in ("Downloads", "Download"):
        p = home / name
        if p.is_dir():
            return p
    return home


def _app_icon_candidates() -> list[Path]:
    here = Path(__file__).resolve().parent
    cand: list[Path] = []

    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            cand.append(Path(meipass) / "app_icon.png")
        exedir = Path(sys.executable).resolve().parent
        cand.append(exedir / "app_icon.png")
        cand.append(exedir / "_internal" / "app_icon.png")

    cand.extend(
        [
            here / "app_icon.png",
            here / "_internal" / "app_icon.png",
            here / "dist" / "BecomeDeathsYTConverter" / "app_icon.png",
            here / "dist" / "BecomeDeathsYTConverter" / "_internal" / "app_icon.png",
            here / "assets" / "app_icon.png",
        ]
    )

    seen: set[str] = set()
    out: list[Path] = []
    for p in cand:
        key = str(p)
        if key in seen:
            continue
        seen.add(key)
        out.append(p)
    return out


def _app_icon_path() -> Path | None:
    for path in _app_icon_candidates():
        if path.is_file():
            return path
    return None


def _app_ico_candidates() -> list[Path]:
    here = Path(__file__).resolve().parent
    cand: list[Path] = []

    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            cand.append(Path(meipass) / "app_icon.ico")
        exedir = Path(sys.executable).resolve().parent
        cand.append(exedir / "app_icon.ico")
        cand.append(exedir / "_internal" / "app_icon.ico")

    cand.extend(
        [
            here / "app_icon.ico",
            here / "_internal" / "app_icon.ico",
            here / "dist" / "BecomeDeathsYTConverter" / "app_icon.ico",
            here / "dist" / "BecomeDeathsYTConverter" / "_internal" / "app_icon.ico",
            here / "assets" / "app_icon.ico",
        ]
    )

    seen: set[str] = set()
    out: list[Path] = []
    for p in cand:
        key = str(p)
        if key in seen:
            continue
        seen.add(key)
        out.append(p)
    return out


def _app_ico_path() -> Path | None:
    for path in _app_ico_candidates():
        if path.is_file():
            return path
    return None


def _apply_window_icon(root: ctk.CTk) -> None:
    ico_path = _app_ico_path()
    if ico_path is not None:
        try:
            root.wm_iconbitmap(str(ico_path))
        except Exception:
            try:
                root.iconbitmap(default=str(ico_path))
            except Exception:
                pass

    path = _app_icon_path()
    try:
        from PIL import Image, ImageTk

        if path is None and ico_path is None:
            return
        img = Image.open(path or ico_path)
        root._wm_icon = ImageTk.PhotoImage(img)  # type: ignore[attr-defined]
        root.iconphoto(True, root._wm_icon)  # type: ignore[attr-defined]
    except Exception:
        if path is None:
            return
        try:
            root._wm_icon = tk.PhotoImage(file=str(path))  # type: ignore[attr-defined]
            root.iconphoto(True, root._wm_icon)  # type: ignore[attr-defined]
        except Exception:
            pass


def _ffmpeg_dir_scan(root: Path) -> Path | None:
    exe = root / "ffmpeg.exe"
    if exe.is_file():
        return exe.parent
    nested = root / "bin" / "ffmpeg.exe"
    if nested.is_file():
        return nested.parent
    try:
        for sub in root.iterdir():
            if not sub.is_dir():
                continue
            if not sub.name.lower().startswith("ffmpeg"):
                continue
            cand = sub / "bin" / "ffmpeg.exe"
            if cand.is_file():
                return cand.parent
    except OSError:
        pass
    return None


def _ffmpeg_dir() -> str | None:
    env = os.environ.get("YOUTUBEGRAB_FFMPEG", "").strip()
    if env:
        p = Path(env).expanduser()
        if p.is_file() and p.name.lower() == "ffmpeg.exe":
            return str(p.parent)
        if (p / "ffmpeg.exe").is_file():
            return str(p)
        bin_exe = p / "bin" / "ffmpeg.exe"
        if bin_exe.is_file():
            return str(bin_exe.parent)

    which = shutil.which("ffmpeg")
    if which:
        return str(Path(which).parent)

    roots: list[Path] = []
    script_home = Path(__file__).resolve().parent
    roots.append(script_home)
    roots.append(script_home / "build" / "YouTubeGrab")
    roots.append(script_home / "build" / "Nexa")
    roots.append(script_home / "build" / "BecomeDeathsYTConverter")
    if getattr(sys, "frozen", False):
        roots.append(Path(sys.executable).resolve().parent)

    seen: set[Path] = set()
    for root in roots:
        if not root.is_dir():
            continue
        try:
            key = root.resolve()
        except OSError:
            continue
        if key in seen:
            continue
        seen.add(key)
        found = _ffmpeg_dir_scan(key)
        if found:
            return str(found)

    return None


def build_video_format_selector(height: int | None) -> str:
    if height is None:
        return "bestvideo+bestaudio/best/bestvideo+bestaudio"
    return (
        f"bestvideo[height<={height}]+bestaudio/best[height<={height}]/"
        f"bestvideo[height<={height}]+bestaudio/best/best"
    )


class _YtdlpLogAdapter:
    def __init__(self, app: "App") -> None:
        self._app = app

    def debug(self, _msg: str) -> None:
        pass

    def info(self, _msg: str) -> None:
        pass

    def warning(self, msg: str) -> None:
        self._app._log(f"[warn] {msg}")

    def error(self, msg: str) -> None:
        self._app._log(f"[error] {msg}")


class App(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.title(APP_NAME)
        self.minsize(520, 640)
        self.geometry("560x720")
        self.configure(fg_color=C_BG)

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")

        self._download_dir = tk.StringVar(value=str(default_download_dir()))
        self._busy = False
        self._ytdlp_logger = _YtdlpLogAdapter(self)
        self._progress_log_bucket = -1
        self._format_segment_value = tk.StringVar(value="MP4")

        self._brand = None
        icon_path = _app_icon_path()
        if icon_path is not None:
            try:
                from PIL import Image

                self._brand = ctk.CTkImage(Image.open(icon_path), size=(56, 56))
            except Exception:
                self._brand = None

        _apply_window_icon(self)
        self._build_ui()
        self._refresh_ffmpeg_hint()

    def _caption(self, parent: ctk.CTkFrame, text: str) -> ctk.CTkLabel:
        return ctk.CTkLabel(
            parent,
            text=text,
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color=C_TEXT_MUTED,
            anchor="center",
        )

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=0, minsize=500)
        self.grid_columnconfigure(2, weight=1)
        self.grid_rowconfigure(0, weight=1)

        shell = ctk.CTkFrame(self, fg_color="transparent")
        shell.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)

        header = ctk.CTkFrame(shell, fg_color="transparent")
        header.pack(fill="x", pady=(0, 18))
        header.grid_columnconfigure(0, weight=1)
        header.grid_columnconfigure(1, weight=0)
        header.grid_columnconfigure(2, weight=1)
        brand_col = ctk.CTkFrame(header, fg_color="transparent")
        brand_col.grid(row=0, column=1, sticky="n")

        if self._brand is not None:
            ctk.CTkLabel(brand_col, image=self._brand, text="").pack()
        ctk.CTkLabel(
            brand_col,
            text=APP_NAME,
            font=ctk.CTkFont(family="Segoe UI", size=24, weight="bold"),
            text_color=C_TEXT,
            anchor="center",
            justify="center",
        ).pack(pady=(10, 0))
        ctk.CTkLabel(
            brand_col,
            text=APP_TAGLINE,
            font=ctk.CTkFont(family="Segoe UI", size=13),
            text_color=C_TEXT_MUTED,
            anchor="center",
            justify="center",
        ).pack(pady=(6, 0))

        card = ctk.CTkFrame(
            shell,
            fg_color=C_SURFACE,
            corner_radius=16,
            border_width=1,
            border_color=C_BORDER,
        )
        card.pack(fill="both", expand=True)

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=22, pady=22)

        self._caption(inner, "YouTube URL").pack(fill="x", pady=(0, 6))
        self.url_entry = ctk.CTkEntry(
            inner,
            placeholder_text="https://www.youtube.com/watch?v=…",
            height=44,
            font=ctk.CTkFont(family="Segoe UI", size=14),
            corner_radius=10,
            border_width=1,
            border_color=C_BORDER,
            fg_color=C_FIELD,
            text_color=C_TEXT,
            placeholder_text_color=C_TEXT_MUTED,
        )
        self.url_entry.pack(fill="x", pady=(0, 18))

        self._caption(inner, "Output folder").pack(fill="x", pady=(0, 6))
        out_row = ctk.CTkFrame(inner, fg_color="transparent")
        out_row.pack(fill="x", pady=(0, 18))
        path_box = ctk.CTkFrame(
            out_row,
            fg_color=C_FIELD,
            corner_radius=10,
            border_width=1,
            border_color=C_BORDER_SUBTLE,
        )
        path_box.pack(side="left", fill="x", expand=True, padx=(0, 10))
        ctk.CTkLabel(
            path_box,
            textvariable=self._download_dir,
            font=ctk.CTkFont(family="Consolas", size=11),
            text_color=C_TEXT_MUTED,
            anchor="center",
            justify="center",
        ).pack(fill="x", padx=12, pady=10)
        ctk.CTkButton(
            out_row,
            text="Browse",
            width=100,
            height=40,
            corner_radius=10,
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            fg_color=C_SURFACE_ELEVATED,
            hover_color=C_BORDER,
            text_color=C_TEXT,
            border_width=1,
            border_color=C_BORDER,
            command=self._browse_folder,
        ).pack(side="right")

        self._caption(inner, "Output format").pack(fill="x", pady=(0, 8))
        self.format_segment = ctk.CTkSegmentedButton(
            inner,
            values=SEGMENT_LABELS,
            variable=self._format_segment_value,
            command=self._on_format_segment,
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            height=36,
            corner_radius=8,
            selected_color=C_ACCENT,
            selected_hover_color=C_ACCENT_HOVER,
            unselected_color=C_FIELD,
            unselected_hover_color=C_SURFACE_ELEVATED,
            text_color=C_TEXT,
            text_color_disabled=C_TEXT_MUTED,
        )
        self.format_segment.pack(fill="x", pady=(0, 18))
        self.format_segment.set("MP4")

        self._caption(inner, "Quality").pack(fill="x", pady=(0, 6))
        self.quality_combo = ctk.CTkComboBox(
            inner,
            values=self._quality_labels_video(),
            font=ctk.CTkFont(family="Segoe UI", size=13),
            height=40,
            corner_radius=10,
            state="readonly",
            dropdown_font=ctk.CTkFont(family="Segoe UI", size=13),
            fg_color=C_FIELD,
            border_color=C_BORDER,
            button_color=C_SURFACE_ELEVATED,
            button_hover_color=C_BORDER,
            text_color=C_TEXT,
        )
        self.quality_combo.pack(fill="x", pady=(0, 20))
        self.quality_combo.set(self._quality_labels_video()[0])

        self.download_btn = ctk.CTkButton(
            inner,
            text="Download",
            height=48,
            corner_radius=10,
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            fg_color=C_ACCENT,
            hover_color=C_ACCENT_HOVER,
            text_color="#ffffff",
            command=self._on_download,
        )
        self.download_btn.pack(fill="x", pady=(0, 14))

        self.progress = ctk.CTkProgressBar(
            inner,
            height=6,
            corner_radius=3,
            progress_color=C_FILL,
            fg_color=C_TRACK,
        )
        self.progress.pack(fill="x", pady=(0, 10))
        self.progress.set(0)

        self.status = ctk.CTkLabel(
            inner,
            text="Ready — paste a URL to begin.",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=C_TEXT_MUTED,
            wraplength=480,
            anchor="center",
            justify="center",
        )
        self.status.pack(fill="x", pady=(0, 16))

        self._caption(inner, "Activity log").pack(fill="x", pady=(0, 6))
        self.log_box = ctk.CTkTextbox(
            inner,
            height=200,
            font=ctk.CTkFont(family="Consolas", size=11),
            corner_radius=10,
            border_width=1,
            border_color=C_BORDER,
            fg_color=C_LOG_BG,
            text_color=C_LOG_TEXT,
            wrap="word",
        )
        self.log_box.pack(fill="both", expand=True, pady=(0, 12))
        self._log(
            "Log output appears here. "
            "FFmpeg: use PATH, set YOUTUBEGRAB_FFMPEG, place ffmpeg.exe beside the app, "
            "or ship ffmpeg under a ffmpeg-* folder next to the executable."
        )

        self.ffmpeg_warn = ctk.CTkLabel(
            inner,
            text="",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=C_WARN,
            wraplength=480,
            anchor="center",
            justify="center",
        )
        self.ffmpeg_warn.pack(fill="x")

    def _kind_from_ui(self) -> str:
        label = self._format_segment_value.get()
        return SEGMENT_TO_KIND.get(label, "mp4")

    def _quality_labels_video(self) -> list[str]:
        return [label for label, _ in VIDEO_QUALITIES]

    def _quality_labels_audio(self) -> list[str]:
        return [label for label, _ in AUDIO_BITRATE_LABELS]

    def _on_format_segment(self, _choice: str) -> None:
        kind = self._kind_from_ui()
        if kind in ("mp4", "webm"):
            self.quality_combo.configure(values=self._quality_labels_video())
            self.quality_combo.set(self._quality_labels_video()[0])
        elif kind == "mp3":
            self.quality_combo.configure(values=self._quality_labels_audio())
            self.quality_combo.set(self._quality_labels_audio()[0])
        else:
            self.quality_combo.configure(values=["Best source audio (PCM WAV)"])
            self.quality_combo.set("Best source audio (PCM WAV)")

    def _browse_folder(self) -> None:
        from tkinter import filedialog

        d = filedialog.askdirectory(initialdir=self._download_dir.get())
        if d:
            self._download_dir.set(d)

    def _refresh_ffmpeg_hint(self) -> None:
        if _ffmpeg_dir():
            self.ffmpeg_warn.configure(text="")
        else:
            self.ffmpeg_warn.configure(
                text="FFmpeg not found — video merge and audio export need FFmpeg. "
                "Add it to PATH, set YOUTUBEGRAB_FFMPEG, or place ffmpeg.exe next to this app."
            )

    def _log(self, message: str) -> None:
        line = f"{datetime.now().strftime('%H:%M:%S')}  {message}\n"

        def append() -> None:
            self.log_box.configure(state="normal")
            self.log_box.insert("end", line)
            self.log_box.see("end")
            self.log_box.configure(state="disabled")

        try:
            self.after(0, append)
        except tk.TclError:
            pass

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        state = tk.DISABLED if busy else tk.NORMAL
        self.download_btn.configure(state=state)
        self.url_entry.configure(state=state)
        self.quality_combo.configure(state=tk.DISABLED if busy else "readonly")
        self.format_segment.configure(state=tk.DISABLED if busy else "normal")

    def _set_status(self, text: str, progress: float | None = None) -> None:
        def apply() -> None:
            self.status.configure(text=text)
            if progress is not None:
                self.progress.set(max(0.0, min(1.0, progress)))

        self.after(0, apply)

    def _progress_hook(self, d: dict) -> None:
        if d.get("status") == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate")
            done = d.get("downloaded_bytes") or 0
            name = d.get("filename", "?")
            short = name if len(name) < 72 else "…" + name[-68:]
            if total:
                pct = 100.0 * done / total
                self._set_status(f"Downloading… {pct:.1f}%", done / total)
                bucket = min(9, int(pct // 10))
                if bucket != self._progress_log_bucket:
                    self._progress_log_bucket = bucket
                    mb_done = done / (1024 * 1024)
                    mb_tot = total / (1024 * 1024)
                    self._log(f"~{bucket * 10}% ({mb_done:.1f} / {mb_tot:.1f} MiB) — {short}")
            else:
                self._set_status("Downloading… (size unknown)", None)
        elif d.get("status") == "finished":
            self._set_status("Post-processing (FFmpeg)…", 0.92)
            self._log("File received; merging or converting with FFmpeg…")

    def _base_opts(self, out: Path) -> dict:
        ff = _ffmpeg_dir()
        opts: dict = {
            "outtmpl": str(out / "%(title)s.%(ext)s"),
            "windowsfilenames": True,
            "restrictfilenames": True,
            "noplaylist": True,
            "progress_hooks": [self._progress_hook],
            "logger": self._ytdlp_logger,
            "quiet": True,
            "no_warnings": False,
        }
        if ff:
            opts["ffmpeg_location"] = ff
        return opts

    def _require_ffmpeg(self, for_what: str) -> bool:
        if _ffmpeg_dir():
            return True
        self._log(f"ERROR: FFmpeg is required for {for_what} but was not found.")
        self._set_status(f"FFmpeg missing — cannot create {for_what}.", 0.0)
        self.progress.set(0)
        return False

    def _on_download(self) -> None:
        if self._busy:
            return
        url = self.url_entry.get().strip()
        if not url:
            self._set_status("Please paste a URL.", 0.0)
            self._log("No URL entered.")
            return

        out = Path(self._download_dir.get())
        if not out.is_dir():
            self._set_status("Output folder does not exist.", 0.0)
            self._log(f"Folder missing: {out}")
            return

        kind = self._kind_from_ui()
        choice = self.quality_combo.get()

        if kind in ("mp4", "webm") and not self._require_ffmpeg(f".{kind} merge"):
            return
        if kind in ("mp3", "wav") and not self._require_ffmpeg(f".{kind} export"):
            return

        try:
            if kind in ("mp4", "webm"):
                height = next(h for lab, h in VIDEO_QUALITIES if lab == choice)
                opts = self._opts_video(out, height, merge_ext=kind)
            elif kind == "mp3":
                kbps = next(k for lab, k in AUDIO_BITRATE_LABELS if lab == choice)
                opts = self._opts_audio_extract(out, "mp3", kbps)
            else:
                opts = self._opts_audio_extract(out, "wav", None)
        except StopIteration:
            self._log("ERROR: Could not match quality choice.")
            self._set_status("Invalid quality selection.", 0.0)
            return

        self._set_busy(True)
        self.progress.set(0.02)
        self._set_status("Starting…", 0.05)
        self._log("---")
        self._log(f"Started: {kind.upper()} → {out}")
        if kind == "mp4":
            self._log("MP4: audio re-encoded to AAC (192 kbps) for reliable playback on Windows.")

        def work() -> None:
            self._progress_log_bucket = -1
            try:
                self._log("Resolving media and starting transfer…")
                with YoutubeDL(opts) as ydl:
                    ret = ydl.download([url])
                if ret != 0:
                    self._log(f"yt-dlp exit code {ret} (non-zero usually indicates failure).")
                    self._set_status("Something went wrong — check the activity log.", 0.0)
                    self.after(0, lambda: self.progress.set(0))
                else:
                    self._set_status(f"Done. Saved under: {out}", 1.0)
                    self._log("Finished successfully.")
            except DownloadError as e:
                self._log(f"Download error: {e}")
                self._set_status("Download failed — see activity log.", 0.0)
                self.after(0, lambda: self.progress.set(0))
            except Exception as e:
                self._log(f"Error: {e}")
                self._log(traceback.format_exc())
                self._set_status("Error — see activity log for details.", 0.0)
                self.after(0, lambda: self.progress.set(0))
            finally:
                self.after(0, lambda: self._set_busy(False))

        threading.Thread(target=work, daemon=True).start()

    def _opts_video(self, out: Path, height: int | None, merge_ext: str) -> dict:
        opts = self._base_opts(out)
        opts["format"] = build_video_format_selector(height)
        opts["merge_output_format"] = merge_ext
        if merge_ext == "mp4":
            opts["postprocessor_args"] = {
                "merger+ffmpeg_o": ["-c:v", "copy", "-c:a", "aac", "-b:a", "192k"],
            }
        return opts

    def _opts_audio_extract(self, out: Path, codec: str, kbps: str | None) -> dict:
        opts = self._base_opts(out)
        opts["format"] = "bestaudio/best"
        pp: dict = {
            "key": "FFmpegExtractAudio",
            "preferredcodec": codec,
        }
        if kbps is not None:
            pp["preferredquality"] = kbps
        opts["postprocessors"] = [pp]
        return opts


def main() -> None:
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
