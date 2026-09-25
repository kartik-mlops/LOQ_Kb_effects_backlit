"""
kb_backlight.py
Controls the Lenovo LOQ white keyboard backlight via WMI (LENOVO_LIGHTING_METHOD),
confirmed working on this machine.

Levels:
    1 = off
    2 = low
    3 = high

Install first:
    pip install wmi pywin32

Usage:
    from kb_backlight import Backlight
    kb = Backlight()
    kb.set_level(3)   # high
    kb.set_level(1)   # off
"""

import wmi

OFF, LOW, HIGH = 1, 2, 3


class Backlight:
    def __init__(self):
        self._c = wmi.WMI(namespace="root/WMI")
        self._lm = self._c.LENOVO_LIGHTING_METHOD()[0]

    def set_level(self, level: int, state_type: int = 0):
        if level not in (OFF, LOW, HIGH):
            raise ValueError("level must be 1 (off), 2 (low), or 3 (high)")
        self._lm.Set_Lighting_Current_Status(
            Current_Brightness_Level=level,
            Current_State_Type=state_type,
            Lighting_ID=0,
        )

    def get_level(self) -> int:
        level, _state = self._lm.Get_Lighting_Current_Status(Lighting_ID=0)
        return level

    def close(self):
        pass  # nothing to clean up, no background process anymore

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


if __name__ == "__main__":
    import time
    kb = Backlight()
    print("Current level:", kb.get_level())
    for lvl in (OFF, LOW, HIGH, LOW, OFF):
        print("Setting", lvl)
        kb.set_level(lvl)
        time.sleep(0.6)
