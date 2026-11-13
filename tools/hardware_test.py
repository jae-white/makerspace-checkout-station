import time
import threading
import queue
import tkinter as tk
import json
import statistics
from collections import deque
from pathlib import Path
from tkinter import messagebox, simpledialog
from tkinter.scrolledtext import ScrolledText

from smbus2 import SMBus
from gpiozero import Button

import board
from cedargrove_nau7802 import NAU7802


# ---------------------------------------------------------
# Hardware configuration
# ---------------------------------------------------------

I2C_BUS = 1
DPAD_ADDRESS = 0x20
DPAD_INPUT_REGISTER = 0x00

RECOVERY_GPIO = 15

DPAD_BITS = {
    0: "UP",
    1: "DOWN",
    2: "RIGHT",
    3: "LEFT",
    4: "CENTER",
}


# ---------------------------------------------------------
# Event queue
# ---------------------------------------------------------

events = queue.Queue()
scale_commands = queue.Queue()
running = True
CALIBRATION_FILE = Path(__file__).with_name("scale_calibration.json")


# ---------------------------------------------------------
# D-pad
# ---------------------------------------------------------

def dpad_worker():
    try:
        bus = SMBus(I2C_BUS)
        last_buttons = []

        while running:
            value = bus.read_byte_data(
                DPAD_ADDRESS,
                DPAD_INPUT_REGISTER
            )

            pressed = []

            for bit, name in DPAD_BITS.items():
                if not (value & (1 << bit)):
                    pressed.append(name)

            if pressed != last_buttons:
                if pressed:
                    events.put(("dpad", " + ".join(pressed)))
                else:
                    events.put(("dpad", "READY"))

                last_buttons = pressed

            time.sleep(0.05)

    except Exception as e:
        events.put(("error", f"D-Pad: {e}"))


# ---------------------------------------------------------
# Load cell / NAU7802
# ---------------------------------------------------------

def scale_worker():
    try:
        i2c = board.I2C()
        nau = NAU7802(i2c, address=0x2A, active_channels=1)
        if not nau.enable(True):
            raise RuntimeError("NAU7802 did not enable")
        nau.channel = 1
        nau.gain = 128
        nau.poll_rate = 10
        for mode in ("INTERNAL", "OFFSET"):
            if not nau.calibrate(mode):
                raise RuntimeError(f"NAU7802 {mode} calibration failed")

        def average(count=60):
            values = []
            for _ in range(count):
                deadline = time.monotonic() + 5
                while running and not nau.available():
                    if time.monotonic() > deadline:
                        raise TimeoutError("No NAU7802 reading arrived")
                    time.sleep(0.01)
                if not running:
                    return None
                values.append(nau.read())
            return statistics.mean(values)

        try:
            factor = float(json.loads(CALIBRATION_FILE.read_text())["counts_per_gram"])
            if factor == 0:
                factor = None
        except (FileNotFoundError, KeyError, ValueError, TypeError):
            factor = None

        average(5)  # Discard readings made during ADC initialization.
        zero = average()
        recent_readings = deque(maxlen=10)
        waiting_for_mass = False
        events.put(("scale_status", "Scale ready; empty tray was tared at startup."))

        while running:
            try:
                command, mass_g = scale_commands.get_nowait()
            except queue.Empty:
                command, mass_g = None, None

            if command == "tare":
                zero = average()
                recent_readings.clear()
                events.put(("scale_status", "Empty tray tared."))
            elif command == "calibrate_zero":
                zero = average()
                recent_readings.clear()
                waiting_for_mass = True
                events.put(("calibration_zero_done", mass_g))
            elif command == "calibrate_weight":
                loaded = average()
                delta = loaded - zero
                waiting_for_mass = False
                recent_readings.clear()
                if abs(delta) < 100:
                    events.put(("error", "Calibration signal too small; check cell wiring and load direction."))
                else:
                    factor = delta / mass_g
                    CALIBRATION_FILE.write_text(
                        json.dumps({"counts_per_gram": factor}, indent=2) + "\n"
                    )
                    events.put(("scale_status", f"Scale calibrated with {mass_g:g} g."))
            elif not waiting_for_mass:
                recent_readings.append(average(5))
                reading = statistics.mean(recent_readings)
                if factor is None:
                    text = f"{reading - zero:+.0f} raw counts (averaged, uncalibrated)"
                else:
                    text = f"{(reading - zero) / factor:+.3f} g ({reading - zero:+.0f} raw counts, averaged)"
                events.put(("scale", text))
            else:
                time.sleep(0.05)

    except Exception as e:
        events.put(("error", f"Scale: {e}"))


# ---------------------------------------------------------
# Recovery button
# ---------------------------------------------------------

def recovery_pressed():
    events.put(("recovery", "PRESSED"))


def recovery_worker():
    try:
        recovery_button = Button(
            RECOVERY_GPIO,
            pull_up=True,
            bounce_time=0.05
        )
        recovery_button.when_pressed = recovery_pressed
        while running:
            time.sleep(0.1)
        recovery_button.close()
    except Exception as e:
        events.put(("error", f"Recovery button: {e}"))


# ---------------------------------------------------------
# GUI
# ---------------------------------------------------------

root = tk.Tk()

root.title("Makerspace Hardware Test")
root.geometry("800x480")

# Fullscreen on the Adafruit display
root.attributes("-fullscreen", True)

root.bind("<Escape>", lambda event: root.destroy())


title = tk.Label(
    root,
    text="MAKERSPACE HARDWARE TEST",
    font=("Arial", 24, "bold")
)

title.pack(pady=8)


status_frame = tk.Frame(root)
status_frame.pack(fill="x", padx=25)


# D-pad
tk.Label(
    status_frame,
    text="D-PAD",
    font=("Arial", 15, "bold")
).grid(row=0, column=0, sticky="w")

dpad_label = tk.Label(
    status_frame,
    text="READY",
    font=("Arial", 15)
)

dpad_label.grid(row=0, column=1, sticky="w", padx=20)


# Recovery
tk.Label(
    status_frame,
    text="RECOVERY BUTTON",
    font=("Arial", 15, "bold")
).grid(row=1, column=0, sticky="w")

recovery_label = tk.Label(
    status_frame,
    text="READY",
    font=("Arial", 15)
)

recovery_label.grid(row=1, column=1, sticky="w", padx=20)


# Scale
tk.Label(
    status_frame,
    text="LOAD CELL",
    font=("Arial", 15, "bold")
).grid(row=2, column=0, sticky="w")

scale_label = tk.Label(
    status_frame,
    text="---",
    font=("Arial", 15)
)

scale_label.grid(row=2, column=1, sticky="w", padx=20)


def tare_scale():
    messagebox.showinfo("Tare scale", "Remove the parts, leaving the empty tray. Click OK when stable.")
    scale_commands.put(("tare", None))


def calibrate_scale():
    mass_g = simpledialog.askfloat(
        "Calibrate scale", "Known calibration mass in grams:",
        parent=root, minvalue=0.001
    )
    if mass_g is None:
        return
    messagebox.showinfo(
        "Calibrate scale",
        "Remove the parts, leaving the empty tray. Click OK when stable."
    )
    scale_commands.put(("calibrate_zero", mass_g))


scale_controls = tk.Frame(status_frame)
scale_controls.grid(row=3, column=0, columnspan=2, sticky="w", pady=6)
tk.Button(scale_controls, text="TARE", command=tare_scale).pack(side="left", padx=(0, 8))
tk.Button(scale_controls, text="CALIBRATE", command=calibrate_scale).pack(side="left")


# HID section
tk.Label(
    root,
    text="USB / WIRELESS HID INPUT",
    font=("Arial", 15, "bold")
).pack(pady=(15, 4))


hid_log = ScrolledText(
    root,
    height=8,
    font=("Courier", 13)
)

hid_log.pack(
    fill="both",
    expand=True,
    padx=25,
    pady=(0, 15)
)

hid_log.insert(
    "end",
    "Swipe card or scan a barcode...\n"
)


# ---------------------------------------------------------
# HID keyboard-style input
# ---------------------------------------------------------

hid_buffer = ""
last_key_time = 0


def finish_hid_input():
    global hid_buffer

    if hid_buffer.strip():

        timestamp = time.strftime("%H:%M:%S")

        hid_log.insert(
            "end",
            f"[{timestamp}] {hid_buffer}\n"
        )

        hid_log.see("end")

    hid_buffer = ""


def keyboard_input(event):
    global hid_buffer
    global last_key_time

    # Escape exits fullscreen
    if event.keysym == "Escape":
        return

    # Most scanners send Enter after a scan
    if event.keysym in ("Return", "KP_Enter"):
        finish_hid_input()
        return

    # Ignore modifier keys
    if event.keysym in (
        "Shift_L",
        "Shift_R",
        "Control_L",
        "Control_R",
        "Alt_L",
        "Alt_R"
    ):
        return

    if event.char and event.char.isprintable():
        hid_buffer += event.char
        last_key_time = time.time()


root.bind_all("<Key>", keyboard_input)


# Automatically finish a HID message if the device
# doesn't send Enter after the scan/swipe
def check_hid_timeout():

    global hid_buffer

    if hid_buffer:

        if time.time() - last_key_time > 0.5:
            finish_hid_input()

    root.after(100, check_hid_timeout)


# ---------------------------------------------------------
# Process hardware events
# ---------------------------------------------------------

def process_events():

    try:

        while True:

            event = events.get_nowait()

            kind = event[0]

            if kind == "dpad":

                dpad_label.config(
                    text=event[1]
                )

            elif kind == "scale":

                scale_label.config(
                    text=event[1]
                )

            elif kind == "calibration_zero_done":

                mass_g = event[1]
                messagebox.showinfo(
                    "Calibrate scale",
                    f"Put the {mass_g:g} g known weight on the tray. Click OK when stable."
                )
                scale_commands.put(("calibrate_weight", mass_g))

            elif kind == "scale_status":

                hid_log.insert("end", f"SCALE: {event[1]}\n")
                hid_log.see("end")

            elif kind == "recovery":

                recovery_label.config(
                    text="PRESSED"
                )

                root.after(
                    750,
                    lambda:
                    recovery_label.config(
                        text="READY"
                    )
                )

            elif kind == "error":

                hid_log.insert(
                    "end",
                    f"ERROR: {event[1]}\n"
                )

                hid_log.see("end")

    except queue.Empty:
        pass

    root.after(
        50,
        process_events
    )


# ---------------------------------------------------------
# Start hardware threads
# ---------------------------------------------------------

threading.Thread(
    target=dpad_worker,
    daemon=True
).start()

threading.Thread(
    target=scale_worker,
    daemon=True
).start()

threading.Thread(
    target=recovery_worker,
    daemon=True
).start()


process_events()
check_hid_timeout()

root.mainloop()

running = False

