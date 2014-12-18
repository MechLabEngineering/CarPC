CarPC Software
=================

![Logo](Logo.png)

Software zur Nutzung des RaspberryPi und Tinkerforge Sensoren als CarPC

## TinkerDataLogger

Kompilierte Python Scripts zum Loggen von

* Beschleunigungen (in x-, y-, z-Achse)
* Drehraten (um x-, y-, z-Achse)
* Lage (roll, pitch, yaw) aus [Sensordatenfusion](http://www.tinkerforge.com/de/doc/Hardware/Bricks/IMU_Brick.html#funktionsweise)
* Position (Lon, Lat)
* Positionsgenauigkeit (EPE, HDOP, VDOP)
* Geschwindigkeit
* Fahrtrichtung

aus Tinkerforge [GPS](http://www.tinkerforge.com/de/doc/Hardware/Bricklets/GPS.html#gps-bricklet) und [IMU](http://www.tinkerforge.com/de/doc/Hardware/Bricks/IMU_Brick.html#imu-brick) Bricks.

### Dependencies

* Tinkerforge [BrickDaemon](http://www.tinkerforge.com/de/doc/Software/Brickd.html)
* Python [API Bindings](http://www.tinkerforge.com/de/doc/Downloads.html#bindings-und-beispiele)

### HowTo?

* `$ python logAccPos.pyc`

### Was passiert?

* Es wird gewartet, bis GPS Lock mindestens 2D fix hat
* Systemzeit wird aus GPS Zeit gesetzt
* dann werden Werte von GPS mit 10Hz und IMU mit 50Hz erfasst
* und in `.csv` in Ordner `DataLogs/` geschrieben
* alle alten `.csv` werden zu `.zip` komprimiert
* auf `/mnt/storage/` verschoben (Windows Partition)

#### Autostart: Linux Cronjobs

Diese Cronjobs laufen als Admin (`sudo crontab -e`) auf dem RaspberryPi:

```
@reboot su -c '/bin/sleep 5 ; python /home/pi/CarPC/logAccPos.pyc 2>&1 >> /home/pi/crontab-log.log' -s /bin/sh pi
@reboot su -c '/bin/sleep 125 ; python /home/pi/CarPC/zipdata.pyc 2>&1 > /home/pi/crontab-zip.log' -s /bin/sh pi
@reboot su -c '/bin/sleep 125 ; /home/pi/CarPC/store.sh' -s /bin/sh pi
```

## MHS CAN-Logger

_Kein Support für [MHS tinyCAN-1XL](http://www.mhs-elektronik.de/index.php?module=content&action=show&page=tinycan_hardware)_

Beispielcode: `canpi.py` loggt in `CANlog.txt`

