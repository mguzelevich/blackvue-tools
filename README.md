# blackvue tools

##

```
python3 blackvue.py --debug --src ./examples --merge-gps > /tmp/out.json
```

## set label to card

```
...
```

## mount 

```
sudo mount -t vfat -o rw,codepage=866,iocharset=utf8,uid=1000,gid=1000,fmask=0111  /dev/sdb1 /mnt/ext
```

## sync

```
sudo rsync -a /mnt/ext /home/pub/blackvue
```

## Firmware Upgrade Guide

STEP-1

Access the BlackVue homepage (www.blackvue.com/downloads) from your computer browser.

STEP-2

Download the latest firmware for your model from the DOWNLOADS page (https://www.blackvue.com/downloads/)

STEP-3

Unzip the downloaded firmware (Zip file)

STEP-4

Insert the BlackVue SD card in your computer using the USB reader provided with your dashcam.

STEP-5

Format the microSD card in the Viewer.
On Mac, after clicking the Format button, choose MS-DOS (FAT) in the Disk Utility.

STEP-6

Copy the BlackVue folder to the SD card.

STEP-7

Insert the SD card in your BlackVue dashcam and turn the power on to apply the upgrade

STEP-8

The dashcam will reboot automatically after applying the upgrade, and start recording.

IMPORTANT
1. Please backup all necessary files before formatting the SD card.
2. The SD card must be formatted in FAT32 format. If you format the card from the BlackVue Viewer, it will be formatted automatically in FAT32.
3. After the firmware upgrade, please use the latest version of the BlackVue Viewer and/or App.
4. After firmware upgrade Wi-Fi login information will be reinitialized. To connect using the BlackVue App, use the default password “blackvue“.
5. MicroSD Card support: DR650GW, DR650S, DR450, DR430 Series models support up to 128GB cards, and DR750LW-2CH supports up to 64GB cards.
Note: compatibility is guaranteed only with the official BlackVue microSD cards.

About microSD cards
Note that we recommend using BlackVue microSD cards for optimal performance.

The reason is that dashcams put microSD cards under higher stress than most electronic products such as action cameras or DSLRs due to their constant loop recording. We test our cards extensively before selecting them for inclusion in our products, to make sure that their performance is good and degrades as little as possible over time.
Using third party microSD cards can affect dashcams’ performance and in some cases, force the dashcam to reboot randomly during recording. Although the basic requirement of the microSD cards for BlackVue dashcams is Class 10 or U1 and that the SD card should be formatted as FAT32 [Windows] or MS-DOS (FAT) [Mac OS], we cannot guarantee the perfect performance of cards from other manufacturers, as even cards with same specifications may vary from batch to batch.

Every BlackVue dashcam comes with an original BlackVue microSD card. In case it is missing or replaced by a third-party microSD card at the time of purchase, please contact the seller to make sure you get a genuine BlackVue microSD card.

# links

http://aprs.gids.nl/nmea/