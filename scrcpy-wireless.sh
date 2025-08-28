#!/bin/bash

output=$(adb devices)

if ! echo "$output" | grep -q "device$"; then
  python3 adb_quick_connect_wireless.py
  sleep .1
else
  echo "Devices already connected through adb."
fi


#python3 adb_quick_connect_wireless.py
#sleep .1
scrcpy --select-tcpip --stay-awake --turn-screen-off --screen-off-timeout=600 --power-off-on-close
