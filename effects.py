"""
effects.py
Breathing / click-react / audio-react effects for the Lenovo LOQ keyboard backlight.

Only 3 real states exist: off (1), low (2), high (3) — no smooth dimming — so
"breathing" steps through these with varying pause times rather than fading.

Install:
    pip install wmi pywin32 pynput PyAudioWPatch numpy

Run:
    python effects.py breathe
    python effects.py click
    python effects.py audio
"""

import argparse
import time

from kb_backlight import Backlight, OFF, LOW, HIGH


def run_breathe(kb: Backlight, cycle_seconds: float = 2.0):
    sequence = [OFF, LOW, HIGH, LOW]
    weights = [1.4, 0.8, 1.4, 0.8]
    total_weight = sum(weights)
    print("Breathing effect running. Ctrl+C to stop.")
    try:
        while True:
            for level, w in zip(sequence, weights):
                kb.set_level(level)
                time.sleep(cycle_seconds * (w / total_weight))
    except KeyboardInterrupt:
        pass
    finally:
        kb.set_level(OFF)


def run_click(kb: Backlight, idle_level: int = LOW, flash_level: int = HIGH, hold_seconds: float = 0.15):
    from pynput import keyboard

    print("Click-react effect running. Keyboard stays low; flashes high on each key. Ctrl+C to stop.")

    last_press = [0.0]
    pressed_since_check = [False]
    current = [idle_level]

    # Runs on pynput's own thread — must not touch `kb` directly (COM/WMI
    # objects aren't safe across threads). It only sets a flag.
    def on_press(key):
        last_press[0] = time.time()
        pressed_since_check[0] = True

    listener = keyboard.Listener(on_press=on_press)
    listener.start()

    try:
        while True:
            time.sleep(0.02)
            if pressed_since_check[0]:
                pressed_since_check[0] = False
                if current[0] != flash_level:
                    kb.set_level(flash_level)
                    current[0] = flash_level
            elif current[0] != idle_level and (time.time() - last_press[0]) > hold_seconds:
                kb.set_level(idle_level)
                current[0] = idle_level
    except KeyboardInterrupt:
        pass
    finally:
        listener.stop()
        kb.set_level(idle_level)


def run_audio(
    kb: Backlight,
    noise_floor: float = 0.02,     # below this = treated as silence -> off
    beat_ratio: float = 1.35,      # volume must exceed recent average by this factor to count as a "beat"
    baseline_decay: float = 0.97,  # how slowly the rolling average adapts (higher = slower/smoother)
    flash_hold: float = 0.12,      # how long a beat flash stays at HIGH before dropping to baseline
    debug: bool = True,
):
    import numpy as np
    import pyaudiowpatch as pyaudio

    p = pyaudio.PyAudio()

    try:
        wasapi_info = p.get_host_api_info_by_type(pyaudio.paWASAPI)
    except OSError:
        print("WASAPI is not available on this system.")
        p.terminate()
        return

    default_speakers = p.get_device_info_by_index(wasapi_info["defaultOutputDevice"])

    if not default_speakers.get("isLoopbackDevice", False):
        match = None
        for loopback in p.get_loopback_device_info_generator():
            if default_speakers["name"] in loopback["name"]:
                match = loopback
                break
        if match is None:
            print("Could not find a loopback device matching your default speakers.")
            p.terminate()
            return
        default_speakers = match

    channels = int(default_speakers["maxInputChannels"])
    rate = int(default_speakers["defaultSampleRate"])

    print(f"Capturing system audio from: {default_speakers['name']}")
    print("Play some music. Ctrl+C to stop.")
    print(f"(beat_ratio={beat_ratio}, noise_floor={noise_floor}, flash_hold={flash_hold}s — tune these)")

    stream = p.open(
        format=pyaudio.paInt16,
        channels=channels,
        rate=rate,
        frames_per_buffer=1024,
        input=True,
        input_device_index=default_speakers["index"],
    )

    current = [OFF]
    rolling_avg = 0.0
    last_beat_time = 0.0
    last_print = 0.0

    try:
        while True:
            data = stream.read(1024, exception_on_overflow=False)
            samples = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0
            volume = float(np.sqrt(np.mean(samples ** 2)))
            now = time.time()

            # Update the rolling "how loud has it generally been lately" baseline
            rolling_avg = rolling_avg * baseline_decay + volume * (1 - baseline_decay)

            is_beat = volume > noise_floor and volume > rolling_avg * beat_ratio
            if is_beat:
                last_beat_time = now

            if volume < noise_floor and rolling_avg < noise_floor:
                target = OFF
            elif now - last_beat_time < flash_hold:
                target = HIGH
            else:
                target = LOW

            if debug and now - last_print > 0.15:
                print(f"vol: {volume:.4f}  avg: {rolling_avg:.4f}  level: {current[0]}   ", end="\r")
                last_print = now

            if target != current[0]:
                kb.set_level(target)
                current[0] = target
    except KeyboardInterrupt:
        pass
    finally:
        print()
        stream.stop_stream()
        stream.close()
        p.terminate()
        kb.set_level(OFF)


def main():
    parser = argparse.ArgumentParser(description="Lenovo LOQ keyboard backlight effects")
    parser.add_argument("mode", choices=["breathe", "click", "audio"])
    parser.add_argument(
        "--speed", type=float, default=2.0,
        help="Breathing: seconds per full cycle (lower = faster). Default 2.0.",
    )
    parser.add_argument(
        "--beat-ratio", type=float, default=1.15,
        help="Audio: how far above the recent average volume must be to count as a beat "
             "(lower = more sensitive/frequent flashes). Default 1.15.",
    )
    args = parser.parse_args()

    kb = Backlight()
    try:
        if args.mode == "breathe":
            run_breathe(kb, cycle_seconds=args.speed)
        elif args.mode == "click":
            run_click(kb)
        elif args.mode == "audio":
            run_audio(kb, beat_ratio=args.beat_ratio)
    finally:
        kb.close()


if __name__ == "__main__":
    main()