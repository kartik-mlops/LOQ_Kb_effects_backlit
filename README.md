# LOQ Backlight Effects

Custom keyboard backlight effects for Lenovo LOQ laptops — **breathing**, **click-react**, and **audio-sync (beat reactive)** — built from scratch because Lenovo Vantage doesn't offer any of these for the plain white, non-RGB keyboard.

Works by talking directly to the same Windows WMI interface Lenovo's own software uses (`LENOVO_LIGHTING_METHOD`), so no extra drivers are needed — just Python (or the packaged `.exe`).

![status](https://img.shields.io/badge/status-working-brightgreen) ![platform](https://img.shields.io/badge/platform-Windows-blue)

## Download

**[⬇ Download the latest .exe](https://github.com/<your-username>/loq-backlight-effects/releases/latest)** — no Python, no setup. Just download and run it.

> Windows may show a "Windows protected your PC" SmartScreen warning since this isn't code-signed. Click **More info → Run anyway**. This is normal for small unsigned tools and not a sign anything's wrong.

## Features

- **Breathing** — smoothly pulses off → low → high → low on a loop
- **Click-react** — keyboard sits at low brightness, flashes to high on every keypress
- **Audio-sync** — reacts to music/system audio in real time, flashing on detected beats using an adaptive volume-spike detector (not just a fixed loudness threshold)
- Ships as both a **command-line tool** and a **desktop GUI app** with sliders to tune sensitivity/speed live
- Can be packaged into a standalone `.exe` (no Python install required to run it)

## Why this exists

The Lenovo LOQ's white backlight only supports **off / low / high** — no per-key RGB, no built-in effects. Lenovo Vantage doesn't expose any dynamic lighting modes for it. This project reverse-engineers the WMI method Vantage itself uses under the hood and builds real effects on top of those 3 states.

## Requirements

Windows 10/11, a Lenovo LOQ (or similar Lenovo/Legion laptop) with the white 2-level keyboard backlight, and Administrator privileges (the backlight control needs elevation). That's it — download and run.

<details>
<summary><strong>For developers: running or building from source</strong> (click to expand — most people can skip this)</summary>

```bash
git clone https://github.com/<your-username>/loq-backlight-effects.git
cd loq-backlight-effects
pip install -r requirements.txt
```

**GUI:**
```bash
python gui.py
```
Run as Administrator. Pick an effect, adjust the slider, hit Start. Minimizes to the system tray.

**Command line:**
```bash
python effects.py breathe --speed 0.6
python effects.py click
python effects.py audio --beat-ratio 1.15 --baseline-decay 0.85
```

**Building your own .exe:**
```bash
pip install pyinstaller
pyinstaller --onefile --noconsole --uac-admin --name "LOQ Backlight" gui.py
```
Output lands in `dist/`.

</details>

## How it works

The keyboard backlight is controlled through the `LENOVO_LIGHTING_METHOD` WMI class under `root\WMI`, using `Set_Lighting_Current_Status(Current_Brightness_Level, Current_State_Type, Lighting_ID)`. On this hardware:

| Brightness value | Result |
|---|---|
| 1 | Off |
| 2 | Low |
| 3 | High |

Audio-sync uses WASAPI loopback (via `pyaudiowpatch`) to capture system audio output, tracks a rolling average of recent loudness, and flags a "beat" when the current volume spikes meaningfully above that average — rather than reacting to raw volume, which would just latch to "high" for the whole song.

## Disclaimer

Built by reverse-engineering an undocumented WMI interface — it works reliably on the tested hardware but isn't officially supported by Lenovo. Use at your own discretion. No warranty.

## License

MIT
