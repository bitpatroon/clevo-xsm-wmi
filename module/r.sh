#!/bin/bash

for i in 0 2 4 6 8 10; do
  echo $i | sudo tee /sys/class/leds/clevo::kbd_backlight/brightness
  sleep 1
done

sudo dmesg | grep -E "clevo_xsm_wmi" | tail -n 90
