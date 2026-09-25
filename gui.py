"""
gui.py
Gaming-themed desktop app for Lenovo LOQ Backlight with Custom Image Logo,
System Tray integration, and Persistent State Caching.
"""

import threading
import time
import json
import os
import sys
import webbrowser
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
import pythoncom
import pystray
from PIL import Image, ImageTk

from kb_backlight import Backlight, OFF, LOW, HIGH

# Theme Configuration
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

# Palette Constants
BG_COLOR = "#121418"
CARD_BG = "#1A1D23"
ACCENT_BLUE = "#00E5FF"
TEXT_MUTED = "#8A92A6"
CONFIG_FILE = "config.json"

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# Automatically locate the logo file (.jpg, .png, .jpeg)
LOGO_FILE = None
for ext in ["jpg", "png", "jpeg"]:
    path = resource_path(f"logo.{ext}")
    if os.path.exists(path):
        LOGO_FILE = path
        break

# Automatically generate a Windows .ico file for the taskbar/titlebar if available
ICO_FILE = resource_path("logo.ico")
if LOGO_FILE and not os.path.exists(ICO_FILE):
    try:
        img_temp = Image.open(LOGO_FILE)
        img_temp.save(ICO_FILE, format="ICO", sizes=[(256, 256), (128, 128), (64, 64), (32, 32)])
    except Exception:
        pass


def create_icon(icon_type):
    """Generates fallback vector-style icons if needed."""
    img = Image.new("RGBA", (28, 28), (0, 0, 0, 0))
    from PIL import ImageDraw
    draw = ImageDraw.Draw(img)

    if icon_type == "off":
        draw.ellipse([4, 4, 24, 24], outline="#8A92A6", width=2)
        draw.line([8, 20, 20, 8], fill="#FF5252", width=2)
    elif icon_type == "low":
        draw.rectangle([10, 8, 18, 18], outline="#00E5FF", width=2)
        draw.line([14, 4, 14, 6], fill="#00E5FF", width=2)
    elif icon_type == "high":
        draw.rectangle([8, 8, 20, 20], outline="#00E5FF", width=2)
        draw.line([14, 2, 14, 6], fill="#00E5FF", width=2)
        draw.line([14, 22, 14, 26], fill="#00E5FF", width=2)
        draw.line([2, 14, 6, 14], fill="#00E5FF", width=2)
        draw.line([22, 14, 26, 14], fill="#00E5FF", width=2)
    elif icon_type == "breath":
        draw.ellipse([8, 8, 20, 20], outline="#00E5FF", width=2)
        draw.ellipse([4, 4, 24, 24], outline="#00E5FF", width=1)
    elif icon_type == "click":
        draw.rectangle([6, 8, 22, 20], outline="#00E5FF", width=2)
        draw.point([(14, 14), (12, 14), (16, 14)], fill="#FFFFFF")
    elif icon_type == "audio":
        draw.rectangle([6, 16, 9, 22], fill="#00E5FF")
        draw.rectangle([12, 10, 15, 22], fill="#00E5FF")
        draw.rectangle([18, 6, 21, 22], fill="#00E5FF")

    return ctk.CTkImage(light_image=img, dark_image=img, size=(22, 22))


class LOQBacklightApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("LOQ Backlight // Gaming Suite")
        self.geometry("780x450")
        self.resizable(False, False)
        self.configure(fg_color=BG_COLOR)

        # Set Taskbar & Title Bar Icon cleanly via .ico
        if os.path.exists(ICO_FILE):
            try:
                self.iconbitmap(ICO_FILE)
            except Exception:
                pass

        try:
            self.kb = Backlight()
        except Exception as e:
            messagebox.showerror(
                "Backlight Error",
                f"Could not connect to keyboard backlight:\n\n{e}\n\nMake sure you run as Administrator."
            )
            self.destroy()
            sys.exit(1)

        self.stop_event = threading.Event()
        self.worker = None
        self.tray_icon = None

        # Load UI Button Icons Dictionary
        self.icons = {
            "off": create_icon("off"),
            "low": create_icon("low"),
            "high": create_icon("high"),
            "breath": create_icon("breath"),
            "click": create_icon("click"),
            "audio": create_icon("audio"),
        }

        # --- Layout Grid ---
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Header Frame
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", padx=25, pady=(15, 5))

        if LOGO_FILE and os.path.exists(LOGO_FILE):
            try:
                pil_logo = Image.open(LOGO_FILE)
                ctk_logo = ctk.CTkImage(light_image=pil_logo, dark_image=pil_logo, size=(32, 32))
                logo_label = ctk.CTkLabel(header_frame, text="", image=ctk_logo)
                logo_label.pack(side="left", padx=(0, 10))
            except Exception:
                pass
        
        title_box = ctk.CTkFrame(header_frame, fg_color="transparent")
        title_box.pack(side="left")

        title_label = ctk.CTkLabel(
            title_box, text="⚡ LOQ BACKLIT // MATRIX", 
            font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"),
            text_color="#FFFFFF"
        )
        title_label.pack(anchor="w")

        sub_header = ctk.CTkLabel(
            title_box, text="HARDWARE LIGHTING CONTROL V2.0", 
            font=ctk.CTkFont(family="Segoe UI", size=9, weight="bold"),
            text_color=ACCENT_BLUE
        )
        sub_header.pack(anchor="w")

        # Content Container
        content_frame = ctk.CTkFrame(self, fg_color="transparent")
        content_frame.grid(row=1, column=0, sticky="nsew", padx=25, pady=(0, 15))
        content_frame.grid_columnconfigure(0, weight=3)
        content_frame.grid_columnconfigure(1, weight=3)
        content_frame.grid_rowconfigure(0, weight=1)

        # --- Section 1: Static Backlight Customization Card ---
        bc_card = ctk.CTkFrame(content_frame, fg_color=CARD_BG, corner_radius=12, border_width=1, border_color="#2A2F3B")
        bc_card.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        
        bc_title = ctk.CTkLabel(
            bc_card, text="⚙ BACKLIGHT CUSTOMIZATION", 
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color=TEXT_MUTED
        )
        bc_title.pack(anchor="w", padx=15, pady=(15, 8))

        btn_grid1 = ctk.CTkFrame(bc_card, fg_color="transparent")
        btn_grid1.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        self.create_gaming_button(btn_grid1, "BACKLIGHT OFF", "Level 0 // Disabled", self.icons["off"], lambda: self.set_static(OFF, save=True))
        self.create_gaming_button(btn_grid1, "LOW INTENSITY", "Level 1 // Dim Mode", self.icons["low"], lambda: self.set_static(LOW, save=True))
        self.create_gaming_button(btn_grid1, "HIGH INTENSITY", "Level 2 // Max Brightness", self.icons["high"], lambda: self.set_static(HIGH, save=True))

        # --- Section 2: Dynamic Effects Card ---
        fx_card = ctk.CTkFrame(content_frame, fg_color=CARD_BG, corner_radius=12, border_width=1, border_color="#2A2F3B")
        fx_card.grid(row=0, column=1, sticky="nsew", padx=(10, 0))

        fx_title = ctk.CTkLabel(
            fx_card, text="🔥 EFFECTS TAB", 
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color=TEXT_MUTED
        )
        fx_title.pack(anchor="w", padx=15, pady=(15, 8))

        btn_grid2 = ctk.CTkFrame(fx_card, fg_color="transparent")
        btn_grid2.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        self.create_gaming_button(btn_grid2, "1. BREATH", "Pulsing ambient fade", self.icons["breath"], lambda: self.start_effect("breathe", save=True))
        self.create_gaming_button(btn_grid2, "2. CLICK", "Flash on keystroke input", self.icons["click"], lambda: self.start_effect("click", save=True))
        self.create_gaming_button(btn_grid2, "3. AUDIO SYNC", "Visualizer beat reaction", self.icons["audio"], lambda: self.start_effect("audio", save=True))

        # --- Status & Footer Bar ---
        status_frame = ctk.CTkFrame(self, fg_color=CARD_BG, corner_radius=10, border_width=1, border_color="#2A2F3B")
        status_frame.grid(row=2, column=0, sticky="ew", padx=25, pady=(0, 20))
        status_frame.grid_columnconfigure(1, weight=1)

        self.stop_btn = ctk.CTkButton(
            status_frame, text="⏹ STOP EFFECT", command=self.stop_effect, 
            fg_color="#3A1F24", hover_color="#4E272E", text_color="#FF5252",
            state="disabled", width=120, height=32, font=("Segoe UI", 10, "bold")
        )
        self.stop_btn.grid(row=0, column=0, padx=10, pady=10, sticky="w")

        self.status_label = ctk.CTkLabel(status_frame, text="STATUS: SYSTEM IDLE", text_color=TEXT_MUTED, font=("Segoe UI", 10, "bold"))
        self.status_label.grid(row=0, column=1, sticky="w", padx=10)

        # Instagram Credits Link (Bottom Right)
        insta_label = ctk.CTkLabel(
            status_frame, 
            text="📷 @Kartik.codes.dev", 
            text_color=ACCENT_BLUE, 
            cursor="hand2",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold")
        )
        insta_label.grid(row=0, column=2, padx=15, sticky="e")
        insta_label.bind("<Button-1>", lambda e: webbrowser.open("https://instagram.com/Kartik.codes.dev"))

        self.protocol("WM_DELETE_WINDOW", self.hide_to_tray)

        threading.Thread(target=self.setup_tray, daemon=True).start()
        self.after(500, self.load_saved_preference)

    def create_gaming_button(self, parent, title_text, desc_text, icon, command):
        btn = ctk.CTkButton(
            parent, 
            text=f"  {title_text}\n  {desc_text}", 
            image=icon,
            compound="left",
            command=command,
            corner_radius=8,
            height=60,
            anchor="w",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            fg_color="#212630",
            hover_color="#2E3544",
            text_color="#FFFFFF",
            border_width=1,
            border_color="#323B4D"
        )
        btn.pack(fill="x", pady=4)

    def save_preference(self, mode, value):
        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump({"mode": mode, "value": value}, f)
        except Exception:
            pass

    def load_saved_preference(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    data = json.load(f)
                    mode = data.get("mode")
                    val = data.get("value")
                    if mode == "static":
                        self.set_static(val, save=False)
                    elif mode == "effect":
                        self.start_effect(val, save=False)
            except Exception:
                pass

    def setup_tray(self):
        """Creates the system tray icon using your custom logo."""
        if os.path.exists(ICO_FILE):
            image = Image.open(ICO_FILE).resize((64, 64), Image.Resampling.LANCZOS)
        elif LOGO_FILE and os.path.exists(LOGO_FILE):
            image = Image.open(LOGO_FILE).resize((64, 64), Image.Resampling.LANCZOS)
        else:
            image = Image.new("RGBA", (64, 64), (0, 0, 0, 0))

        menu = pystray.Menu(
            pystray.MenuItem("Open LOQ Backlight", self.show_window, default=True),
            pystray.MenuItem("Exit Completely", self.exit_app)
        )
        self.tray_icon = pystray.Icon("LOQBacklight", image, "LOQ Backlight Suite", menu)
        self.tray_icon.run()

    def hide_to_tray(self):
        self.withdraw()

    def show_window(self, icon=None, item=None):
        self.deiconify()
        self.lift()
        self.focus_force()

    def exit_app(self, icon=None, item=None):
        self.stop_worker_thread()
        try:
            self.kb.set_level(OFF)
        except Exception:
            pass
        if self.tray_icon:
            self.tray_icon.stop()
        self.destroy()

    def stop_worker_thread(self):
        if self.worker and self.worker.is_alive():
            self.stop_event.set()
            self.worker.join(timeout=1.0)
        self.stop_event.clear()

    def set_static(self, level, save=True):
        self.stop_worker_thread()
        try:
            self.kb.set_level(level)
            name = {OFF: "OFF", LOW: "LOW", HIGH: "HIGH"}.get(level)
            self.status_label.configure(text=f"STATUS: LEVEL LOCKED [{name}]", text_color="#00E5FF")
            self.stop_btn.configure(state="disabled")
            if save:
                self.save_preference("static", level)
        except Exception as e:
            self.status_label.configure(text=f"ERROR: {e}", text_color="#FF5252")

    def start_effect(self, mode, save=True):
        self.stop_worker_thread()
        self.stop_event.clear()

        if mode == "breathe":
            self.worker = threading.Thread(target=self.run_breathe, daemon=True)
        elif mode == "click":
            self.worker = threading.Thread(target=self.run_click, daemon=True)
        elif mode == "audio":
            self.worker = threading.Thread(target=self.run_audio, daemon=True)

        self.worker.start()
        self.stop_btn.configure(state="normal")
        names = {"breathe": "BREATHING", "click": "KEY-CLICK", "audio": "AUDIO-SYNC"}
        self.status_label.configure(text=f"STATUS: RUNNING EFFECT [{names[mode]}]", text_color="#00E5FF")
        if save:
            self.save_preference("effect", mode)

    def stop_effect(self):
        self.stop_worker_thread()
        self.stop_btn.configure(state="disabled")
        self.status_label.configure(text="STATUS: SYSTEM IDLE", text_color=TEXT_MUTED)
        try:
            self.kb.set_level(OFF)
        except Exception:
            pass
        if os.path.exists(CONFIG_FILE):
            os.remove(CONFIG_FILE)

    # --- Background Loops ---
    def run_breathe(self):
        pythoncom.CoInitialize()
        try:
            kb = Backlight()
            sequence = [OFF, LOW, HIGH, LOW]
            weights = [1.4, 0.8, 1.4, 0.8]
            total = sum(weights)
            while not self.stop_event.is_set():
                for level, w in zip(sequence, weights):
                    if self.stop_event.is_set():
                        break
                    kb.set_level(level)
                    time.sleep(1.5 * (w / total))
            kb.set_level(OFF)
        finally:
            pythoncom.CoUninitialize()

    def run_click(self):
        from pynput import keyboard
        pythoncom.CoInitialize()
        try:
            kb = Backlight()
            idle, flash, hold = LOW, HIGH, 0.15
            last_press = [0.0]
            pressed = [False]
            current = [idle]

            def on_press(key):
                last_press[0] = time.time()
                pressed[0] = True

            listener = keyboard.Listener(on_press=on_press)
            listener.start()
            kb.set_level(idle)
            while not self.stop_event.is_set():
                time.sleep(0.02)
                if pressed[0]:
                    pressed[0] = False
                    if current[0] != flash:
                        kb.set_level(flash)
                        current[0] = flash
                elif current[0] != idle and (time.time() - last_press[0]) > hold:
                    kb.set_level(idle)
                    current[0] = idle
            listener.stop()
            kb.set_level(OFF)
        finally:
            pythoncom.CoUninitialize()

    def run_audio(self):
        import numpy as np
        import pyaudiowpatch as pyaudio
        pythoncom.CoInitialize()
        try:
            kb = Backlight()
            p = pyaudio.PyAudio()
            wasapi_info = p.get_host_api_info_by_type(pyaudio.paWASAPI)
            default_speakers = p.get_device_info_by_index(wasapi_info["defaultOutputDevice"])
            if not default_speakers.get("isLoopbackDevice", False):
                for loopback in p.get_loopback_device_info_generator():
                    if default_speakers["name"] in loopback["name"]:
                        default_speakers = loopback
                        break
            stream = p.open(
                format=pyaudio.paInt16,
                channels=int(default_speakers["maxInputChannels"]),
                rate=int(default_speakers["defaultSampleRate"]),
                frames_per_buffer=1024,
                input=True,
                input_device_index=default_speakers["index"],
            )
            rolling_avg, last_beat, current = 0.0, 0.0, [OFF]
            while not self.stop_event.is_set():
                data = stream.read(1024, exception_on_overflow=False)
                samples = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0
                volume = float(np.sqrt(np.mean(samples ** 2)))
                now = time.time()
                rolling_avg = rolling_avg * 0.97 + volume * 0.03
                if volume > 0.02 and volume > rolling_avg * 1.15:
                    last_beat = now
                target = OFF if (volume < 0.02 and rolling_avg < 0.02) else (HIGH if now - last_beat < 0.12 else LOW)
                if target != current[0]:
                    kb.set_level(target)
                    current[0] = target
            stream.stop_stream()
            stream.close()
            p.terminate()
            kb.set_level(OFF)
        finally:
            pythoncom.CoUninitialize()


if __name__ == "__main__":
    app = LOQBacklightApp()
    app.mainloop()