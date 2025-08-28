# scrcpy-wireless
Tools to make wireless connection through adb and thus scrcpy more convinent

Python and Android Debug Tools need to be preinstalled. You need to have already connected your phone manually through adb, and saved the device on the phone, and to have wireless debugging enabled on the Android device.

### scrcpy-wireless.sh
Use `chmod +x scrcpy-wireless.sh` to make the script executable, then run with `./scrcpy-wireless.sh`. The script will automatically start scrcpy if you're already connected to a device through adb, or search the network for devices open to wireless debugging. Make sure the devices are on the same network and not using a VPN!
