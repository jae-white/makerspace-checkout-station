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

`hardware_test.py` is a basic integration/smoke test.

It is intended to verify:

- D-pad input
- Recovery button input
- Raw load-cell response
- USB/HID input from card readers and scanners
- Multiple hardware interfaces operating simultaneously
- Output on the 5-inch display

This is not intended to be the final application architecture.

## Raspberry Pi Setup

Enable I2C:

```bash
sudo raspi-config
