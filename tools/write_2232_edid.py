#!/usr/bin/env python3
"""
Program the Adafruit TFP401/2232 EDID EEPROM at I2C address 0x50
with Adafruit's official 800x480 EDID block.

Source:
https://learn.adafruit.com/adafruit-tfp401-hdmi-slash-dvi-decoder-to-40-pin-ttl-display/editing-the-edid

This script uses the i2c-tools commands already available on Raspberry Pi OS,
so it does not require any extra Python package.

Safety:
- HDMI must be disconnected from the display while programming.
- The display EDID EEPROM must be connected to Pi I2C bus 1.
- The script refuses to overwrite a non-blank, non-matching EEPROM unless
  --force is supplied.
"""

import argparse
import shutil
import subprocess
import sys
import time

BUS = 1
ADDR = 0x50

EDID = bytes([
    0x00, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0x00, 0x04, 0x81, 0x04, 0x00, 0x01, 0x00, 0x00, 0x00,
    0x01, 0x11, 0x01, 0x03, 0x80, 0x0F, 0x0A, 0x00, 0x0A, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01,
    0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x80, 0x0C, 0x20, 0x80, 0x30, 0xE0, 0x2D, 0x10, 0x28, 0x30,
    0xD3, 0x00, 0x6C, 0x44, 0x00, 0x00, 0x00, 0x18, 0x00, 0x00, 0x00, 0x10, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x10, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x10,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x17,
])

assert len(EDID) == 128
assert sum(EDID) & 0xFF == 0


def run(cmd):
    return subprocess.run(cmd, check=True, text=True, capture_output=True).stdout.strip()


def read_byte(offset):
    out = run([
        "i2cget", "-y", str(BUS), hex(ADDR), hex(offset), "b"
    ])
    return int(out, 16)


def write_byte(offset, value):
    subprocess.run([
        "i2cset", "-y", str(BUS), hex(ADDR), hex(offset), hex(value), "b"
    ], check=True)
    time.sleep(0.01)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--force",
        action="store_true",
        help="overwrite even if EEPROM is not blank or already matching",
    )
    args = parser.parse_args()

    if shutil.which("i2cget") is None or shutil.which("i2cset") is None:
        sys.exit("ERROR: i2c-tools not found (need i2cget and i2cset).")

    if hasattr(sys, "getuid") and __import__("os").getuid() != 0:
        sys.exit("ERROR: run with sudo.")

    print("Reading current EDID EEPROM at I2C address 0x50...")
    try:
        current = bytes(read_byte(i) for i in range(128))
    except subprocess.CalledProcessError as exc:
        sys.exit(f"ERROR: could not read 0x50 on I2C bus {BUS}: {exc}")

    if current == EDID:
        print("EDID already matches Adafruit's official 800x480 data. Nothing to do.")
        return

    blank = all(b == 0xFF for b in current)
    if not blank and not args.force:
        sys.exit(
            "ERROR: EEPROM is not blank and does not match the target EDID.\n"
            "Refusing to overwrite it. Re-run with --force only if you intentionally want that."
        )

    if blank:
        print("EEPROM is blank (all FF).")
    else:
        print("WARNING: --force supplied; overwriting existing EDID.")

    print("Writing Adafruit official 800x480 EDID...")
    for offset, value in enumerate(EDID):
        write_byte(offset, value)

    print("Verifying...")
    verify = bytes(read_byte(i) for i in range(128))

    if verify != EDID:
        for i, (expected, actual) in enumerate(zip(EDID, verify)):
            if expected != actual:
                print(f"Mismatch at 0x{i:02X}: expected 0x{expected:02X}, got 0x{actual:02X}")
        sys.exit("ERROR: verification failed.")

    print("SUCCESS: EDID written and verified.")
    print("Shut the Pi down, disconnect the STEMMA/QT EDID cable, reconnect HDMI, then cold boot.")


if __name__ == "__main__":
    main()
