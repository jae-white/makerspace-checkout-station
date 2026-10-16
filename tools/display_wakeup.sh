#!/usr/bin/env bash

# Workaround for the Adafruit 2232 display occasionally failing to come up
# correctly during a cold boot. Run this after the Wayland desktop starts.
#
# The Pi is configured for HDMI0 at 800x480. This toggles the HDMI output
# after boot, which mimics the hot-plug behavior that reliably wakes the panel.

OUTPUT="${1:-HDMI-A-1}"

sleep 5
wlr-randr --output "$OUTPUT" --off
sleep 2
wlr-randr --output "$OUTPUT" --on --custom-mode 800x480@60
