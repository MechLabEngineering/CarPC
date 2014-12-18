#!/bin/sh

rsync -rvtW --include='*.zip' --exclude='*.csv' /home/pi/RaspberryPi-CarPC/TinkerDataLogger/DataLogs/ /mnt/storage/
