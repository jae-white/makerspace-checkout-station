#!/usr/bin/env python3
"""Temporary Raspberry Pi 5 + Adafruit NAU7802 scale tester.

Run ``python3 scale_test.py`` after installing Blinka and cedargrove-nau7802.
The program reads channel 1, tares an empty tray, and optionally calibrates
against a known mass. It is independent of the checkout application.
"""

from __future__ import annotations

import json
import statistics
import sys
import time
from pathlib import Path


CALIBRATION_FILE = Path(__file__).with_name("scale_calibration.json")
ADC_ADDRESS = 0x2A
SAMPLES = 20


def read_samples(adc, count: int = SAMPLES) -> list[int]:
    readings = []
    for _ in range(count):
        deadline = time.monotonic() + 5.0
        while not adc.available():
            if time.monotonic() > deadline:
                raise TimeoutError("No NAU7802 reading arrived within 5 seconds")
            time.sleep(0.01)
        readings.append(adc.read())
    return readings


def raw_average(adc, count: int = SAMPLES) -> float:
    return statistics.mean(read_samples(adc, count))


def load_factor() -> float | None:
    try:
        data = json.loads(CALIBRATION_FILE.read_text())
        value = float(data["counts_per_gram"])
        return value if value != 0 else None
    except (FileNotFoundError, KeyError, ValueError, TypeError, json.JSONDecodeError):
        return None


def show_reading(adc, zero: float, factor: float | None) -> None:
    values = read_samples(adc)
    delta = statistics.mean(values) - zero
    noise = statistics.stdev(values)
    if factor is None:
        print(f"Raw change: {delta:+.0f} counts  |  noise: {noise:.0f} counts  |  calibrate with 'c' for grams")
    else:
        grams = delta / factor
        noise_grams = noise / abs(factor)
        print(f"Weight: {grams:+.3f} g  |  raw change: {delta:+.0f} counts  |  sample noise: {noise_grams:.3f} g")


def main() -> int:
    try:
        import board
        from cedargrove_nau7802 import NAU7802
    except ImportError as exc:
        print(f"Missing Raspberry Pi library: {exc}", file=sys.stderr)
        print("Install adafruit-blinka and cedargrove-nau7802; see scale_test_README.md.", file=sys.stderr)
        return 1

    try:
        adc = NAU7802(board.I2C(), address=ADC_ADDRESS, active_channels=1)
        if not adc.enable(True):
            raise RuntimeError("NAU7802 did not enable")
        adc.channel = 1
        adc.gain = 128
        input("Empty the tray, then press Enter to initialize and tare... ")
        for mode in ("INTERNAL", "OFFSET"):
            if not adc.calibrate(mode):
                raise RuntimeError(f"NAU7802 {mode} calibration failed")
        read_samples(adc, 5)  # Discard startup readings.
        zero = raw_average(adc, 30)
        factor = load_factor()
        print(f"Tared at {zero:.0f} raw counts.")
        print("Saved gram calibration loaded." if factor is not None else "No gram calibration yet; raw readings still work.")

        while True:
            command = input("\n[m]easure  [s]tream  [t]are  [c]alibrate  [q]uit > ").strip().lower()
            if command == "m":
                show_reading(adc, zero, factor)
            elif command == "s":
                print("Streaming; press Ctrl+C to return to menu.")
                try:
                    while True:
                        show_reading(adc, zero, factor)
                except KeyboardInterrupt:
                    print("\nStopped streaming.")
            elif command == "t":
                input("Remove the parts but leave the empty tray in place; press Enter... ")
                zero = raw_average(adc, 30)
                print(f"Tared at {zero:.0f} raw counts.")
            elif command == "c":
                try:
                    mass_g = float(input("Known calibration mass in grams (e.g. 50): "))
                except ValueError:
                    print("Enter a number in grams.")
                    continue
                if mass_g <= 0:
                    print("The mass must be greater than zero.")
                    continue
                input("Empty the tray; press Enter to measure zero... ")
                zero = raw_average(adc, 30)
                input(f"Place the {mass_g:g} g known weight on the tray; press Enter once stable... ")
                loaded = raw_average(adc, 30)
                delta = loaded - zero
                if abs(delta) < 100:
                    print("Signal change is too small. Check the wiring and load direction; calibration not saved.")
                    continue
                factor = delta / mass_g
                CALIBRATION_FILE.write_text(json.dumps({"counts_per_gram": factor}, indent=2) + "\n")
                print(f"Calibrated: {factor:.1f} counts/g. Remove the weight and press 'm' to check zero.")
            elif command == "q":
                return 0
            else:
                print("Choose m, s, t, c, or q.")
    except (OSError, RuntimeError, TimeoutError) as exc:
        print(f"Scale error: {exc}", file=sys.stderr)
        print("Check Pi I2C, 0x2A detection, NAU7802 wiring, and load-cell wiring.", file=sys.stderr)
        return 1
    except (KeyboardInterrupt, EOFError):
        print("\nStopped.")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
