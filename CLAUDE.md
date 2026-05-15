# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This repository contains a Linux kernel module and a Qt5 utility for controlling keyboard backlighting on Clevo SM/EM/ZM/DM series laptops. It is based on tuxedo-wmi by TUXEDO Computers GmbH.

## Build Commands

### Kernel Module

```bash
# Build
cd module && make

# Install (standard)
cd module && sudo make install

# Ubuntu (unsigned module workaround)
sudo install -m644 clevo-xsm-wmi.ko /lib/modules/$(uname -r)/extra && sudo depmod

# Quick rebuild and reload (development)
cd module && bash b.sh
```

The `b.sh` script does: `make clean && make`, copies to `/lib/modules/$(uname -r)/updates/`, runs `depmod -a`, then reloads the module.

Enable debug logging by uncommenting `#CFLAGS_clevo-xsm-wmi.o := -DDEBUG` in the Makefile.

### Qt5 Utility

```bash
cd utility && qmake && make
# Fedora: use qmake-qt5 instead
sudo install -Dm755 clevo-xsm-wmi /usr/bin/clevo-xsm-wmi
sudo install -Dm755 systemd/clevo-xsm-wmi.service /usr/lib/systemd/system/clevo-xsm-wmi.service
```

## Architecture

### Kernel Module (`module/clevo-xsm-wmi.c`)

The module uses ACPI/WMI to communicate with the laptop firmware via three GUIDs:
- `CLEVO_EVENT_GUID` — WMI event notifications (hotkeys)
- `CLEVO_GET_GUID` — WMI method calls (`clevo_xsm_wmi_evaluate_wmbb_method`)

**Backlight ops abstraction**: Device-specific behavior is isolated behind `struct kb_backlight_ops` with function pointers for `set_state`, `set_color`, `set_brightness`, `set_mode`, and `init`. Two implementations exist:
- `kb_8_color_ops` — 8 fixed colors (older P15SM/P17SM/P150EM models)
- `kb_full_color_ops` / `kb_full_color_with_extra_ops` — full RGB (P370SM-A, P7xxDM, P750ZM, etc.; `_with_extra` adds a 4th "extra" zone for touchpad/front LED bar)

The correct ops struct is selected at `__init` time via DMI table matching (`clevo_xsm_dmi_table`). If no DMI match is found, `kb_backlight.ops` stays NULL and keyboard control is unavailable.

**Sub-drivers registered at init:**
- `clevo_xsm_rfkill` — WWAN rfkill (disabled unless `rfkill=1` module param)
- `clevo_xsm_input` — airplane mode hotkey via EC polling thread
- `clevo_xsm_led` — airplane mode LED (`clevo_xsm::airplane` led class)
- `clevo_kbd_led` — keyboard backlight as `clevo::kbd_backlight` LED class (added in Dec 2025, allows standard Linux backlight control via `/sys/class/leds/clevo::kbd_backlight/brightness`)

**Sysfs interface** at `/sys/devices/platform/clevo_xsm_wmi/`:
- `kb_brightness` — integer 0–10
- `kb_state` — 0 or 1
- `kb_mode` — integer 0–7 (random_color, custom, breathe, cycle, wave, dance, tempo, flash)
- `kb_color` — color name(s) separated by spaces (black, blue, red, magenta, green, cyan, yellow, white)

**Module parameters**: `kb_color`, `kb_brightness`, `kb_off`, `kb_cycle_colors`, `poll_freq`, `led_invert`, `rfkill`.

### Qt5 Utility (`utility/`)

A GUI front-end that reads/writes the sysfs attributes. `main.cpp` handles `-r` (restore) and `-s` (save) command-line flags. `mainwindow.cpp/h` is the Qt widget. Settings are persisted to a file for the systemd service to restore at boot.

### Systemd Service (`utility/systemd/clevo-xsm-wmi.service`)

Runs `clevo-xsm-wmi -r` on start and `clevo-xsm-wmi -s` on stop to restore/save keyboard state across reboots.

## Debugging

```bash
# Check module loaded and model detected
sudo modprobe clevo_xsm_wmi
dmesg | grep clevo

# Test brightness via LED class (Dec 2025 addition)
bash module/r.sh  # cycles brightness 0-10 and shows dmesg

# Runtime sysfs control
echo "blue" | sudo tee /sys/devices/platform/clevo_xsm_wmi/kb_color
echo 5 | sudo tee /sys/devices/platform/clevo_xsm_wmi/kb_brightness
echo 1 | sudo tee /sys/devices/platform/clevo_xsm_wmi/kb_state
```

## Adding New Device Support

Add a new entry to `clevo_xsm_dmi_table[]` in `clevo-xsm-wmi.c` with a `DMI_MATCH` on `DMI_PRODUCT_NAME` and assign the appropriate `kb_*_ops` struct as `driver_data`. Use `sudo dmidecode | grep -i product` to find the exact product name string reported by the firmware.
