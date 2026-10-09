import time
import threading
import queue
import tkinter as tk
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
running = True


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

        nau = NAU7802(
            i2c,
            address=0x2A,
            active_channels=1
        )

        nau.enable(True)
        nau.channel = 1

        while running:

            if nau.available():
                reading = nau.read()
                events.put(("scale", str(reading)))

            time.sleep(0.10)

    except Exception as e:
        events.put(("error", f"Scale: {e}"))


# ---------------------------------------------------------
# Recovery button
# ---------------------------------------------------------

def recovery_pressed():
    events.put(("recovery", "PRESSED"))


recovery_button = Button(
    RECOVERY_GPIO,
    pull_up=True,
    bounce_time=0.05
)

recovery_button.when_pressed = recovery_pressed


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
    text="LOAD CELL RAW",
    font=("Arial", 15, "bold")
).grid(row=2, column=0, sticky="w")

scale_label = tk.Label(
    status_frame,
    text="---",
    font=("Arial", 15)
)

scale_label.grid(row=2, column=1, sticky="w", padx=20)


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


process_events()
check_hid_timeout()

root.mainloop()

running = False
