# Raspberry-Pi-NTP-ST7789-display
A python script to display NTP data from chrony, GPS data, and system stats on a 284x76 ST7789  TFT LCD.

This was inspired by Dominik Schlösser (https://github.com/domschl/RaspberryNtpServer) and his chronotron code for displaying Raspberry pi NTP server stats on a 20x4 LCD

As I wanted to rackmount my Pi in 1RU, the 20x4 LCD was too big.  Not being able to source a smaller 20x4 LCD my next option was a 284x76 TFT LCD display.
These are cheaply available on AliExpress (https://www.aliexpress.com/item/1005008945269187.html) for a few dollars, and no doubt elsewhere.
Having a matrix display I thought why not add some extra data to be displayed, and I have added 5 pages of display:
1. NTP data, this is the same as Dominik's 20x4 LCD display, but with a graph added to the right hand side showing the difference values.
2. GPS data, this displays Fix, lattitude/longditude, altitude, number of satellites used/seen, HDOP, TDOP and a mini constellation sky view on the right
3. 'chronyc sources', this displayssome data of 4 NTP sources
4. 'chronyc sourcestats', this displays some data of 4 NTP sources stats
5. System status, this displays load, RAM/Disk used, CPU temp and uptime.  On the right hadn side are 4 bars showing each CPU core load

My setup is using a Raspberry Pi 3B+, obviously the 284x76 ST7789  TFT LCD, and a Neo M9N GPS module.
Setup for the GPS module and chrony are as in https://github.com/domschl/RaspberryNtpServer


Enable SPI:
sudo raspi-config -> 3. Interface Options -> I4. SPI Enable

I have used SPI1, as SPI0 was causing issues with the GPIO pin used for PPS sensing.  Changes to be made to /boot/firmware/config.txt:
># Enable SPI1, set CS to pin 17
>dtparam=spi=on
>dtoverlay=spi1-1cs,cs0_pin=17
># Disable video (we are running headless!)
>#dtoverlay=vc4-kms-v3d
>max_framebuffers=0
># Disable Bluetooth/WiFi (we are connected via ethernet)
>dtoverlay=disable-wifi
>dtoverlay=disable-bt
>enable_uart=1
># Permanent PPS Lock (didn't really work, hence why we are using SPI1)
>gpio=4=ip,pud_off
>dtoverlay=pps-gpio,gpiopin=4
># Disable HDMI/Video output to save power & reduce jitter
>hdmi_blanking=2
>force_turbo=1

Install required dependencies:
>sudo apt update
>sudo apt install gpsd gpsd-clients chrony python3-pip python3-dev libffi-dev libssl-dev libjpeg-dev zlib1g-dev i2c-tools -y
