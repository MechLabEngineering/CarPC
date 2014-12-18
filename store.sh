#!/bin/sh

rsync -rvtW --include='*.zip' --exclude='*.csv' /home/pi/CarPC/DataLogs/ /mnt/storage/
