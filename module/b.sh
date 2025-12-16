#!/bin/bash

make clean && make
sudo cp clevo-xsm-wmi.ko /lib/modules/$(uname -r)/updates/
sudo depmod -a
sudo modprobe -r clevo_xsm_wmi
sudo modprobe clevo_xsm_wmi

