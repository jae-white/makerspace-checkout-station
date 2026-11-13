# Makerspace Checkout Station

Raspberry Pi 5 hardware prototype for a Makerspace checkout and internal inventory system.

This repository currently contains hardware validation code. It is intended to verify that the station's peripherals can operate together before development of the final checkout/inventory application.

## Current Hardware

- Raspberry Pi 5
- Adafruit 2232 5-inch HDMI display
- ID TECH MiniMag Duo student ID reader
- DFRobot GM73 / SEN0544 fixed barcode/QR scanner
- Adesso NuScan 2900 2D wireless handheld scanner
- SparkFun Qwiic Directional Pad PRT-26851
- Adafruit 4538 NAU7802 load-cell ADC
- Adafruit 4540 1 kg load cell
- E-Switch RP3502ABLK emergency recovery button

## Interfaces

### USB

- ID TECH MiniMag Duo
- DFRobot GM73 / SEN0544
- Adesso NuScan 2900 receiver

### HDMI

- Adafruit 2232 display

### I2C

Raspberry Pi 5 -> Adafruit 4397 -> Qwiic Directional Pad -> Adafruit 4210 -> NAU7802

Known addresses:

- `0x20` - SparkFun Qwiic Directional Pad
- `0x2A` - Adafruit NAU7802

### GPIO

Emergency recovery button:

- BCM GPIO15
- GND
- Uses an internal pull-up

## Hardware Test

`tools/hardware_test.py` is a basic integration/smoke test with scale tare and calibration controls.

It is intended to verify:

- D-pad input
- Recovery button input
- Raw load-cell response and calibrated gram readings
- USB/HID input from card readers and scanners
- Multiple hardware interfaces operating simultaneously
- Output on the 5-inch display

This is not intended to be the final application architecture.

## Raspberry Pi Setup

Enable I2C:

```bash
sudo raspi-config
```

Install dependencies from the repository root:

```bash
sudo apt install python3-venv python3-tk i2c-tools
python3 -m venv --system-site-packages .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
i2cdetect -y 1  # Confirm that 2a appears for the NAU7802
```

## Engineering Console

On the Raspberry Pi, install a desktop shortcut from the repository root after completing the setup above:

```bash
bash tools/install_engineering_console_shortcut.sh
```

Double-click **Makerspace Engineering Console** on the Pi desktop. The console tests the D-pad, recovery button, scale, and USB/HID devices. For the scale, leave the tray empty and press **TARE**; press **CALIBRATE** and follow the prompts with a known mass in grams. Readings show raw counts until calibration is saved, then grams. The live display averages recent readings, so wait about five seconds after adding or removing a small item before judging the value. The calibration factor is stored locally in `tools/scale_calibration.json`.

You can also launch it from the repository root with `bash tools/launch_engineering_console.sh`.

## Temporary Scale Calibration

Run the standalone test program on the Raspberry Pi:

```bash
. .venv/bin/activate
python tools/scale_test.py
```

The program tares an empty tray at startup. Press `m` for one reading, `s` for live readings, `t` to tare again, `c` to calibrate with a known mass in grams, or `q` to quit. Raw readings work before gram calibration. The calibration factor is saved locally to `tools/scale_calibration.json`, which is ignored by Git.

For the Adafruit NAU7802, use the load-cell terminals marked `A+`, `A-`, `E+`, and `E-` and verify the wiring against the actual cell. The common Adafruit example is green → `A+`, white → `A-`, red → `E+`, and black → `E-`.

A temporary fixture can reveal whether batches of small parts produce a repeatable change. Calibrate again after the load cell and tray are mounted in the finished enclosure; this program does not establish final scale accuracy on its own.
