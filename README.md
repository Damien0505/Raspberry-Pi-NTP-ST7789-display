# Raspberry-Pi-NTP-ST7789-display
A python script to display NTP data from chrony, GPS data, and system stats on a 284x76 ST7789  TFT LCD.

This was inspired by Dominik Schlösser (https://github.com/domschl/RaspberryNtpServer) and his chronotron code for displaying Raspberry pi NTP server stats on a 20x4 LCD.  Thank you to Dominik for his NTP server setup guidance, and his inspiration.

As I wanted to rackmount my Pi in 1RU, the 20x4 LCD was too big.  Not being able to source a smaller 20x4 LCD my next option was a 284x76 TFT LCD display.
These are cheaply available on AliExpress (https://www.aliexpress.com/item/1005008945269187.html) for a few dollars, and no doubt elsewhere.
Having a matrix display I thought why not add some extra data to be displayed, and I have added 5 pages of display:
1. NTP data, this is the same as Dominik's 20x4 LCD display, but with a graph added to the right hand side showing the difference values.
2. GPS data, this displays Fix, lattitude/longditude, altitude, number of satellites used/seen, HDOP, TDOP and a mini constellation sky view on the right
3. 'chronyc sources', this displayssome data of 4 NTP sources
4. 'chronyc sourcestats', this displays some data of 4 NTP sources stats
5. System status, this displays load, RAM/Disk used, CPU temp and uptime.  On the right hadn side are 4 bars showing each CPU core load

My setup is using a Raspberry Pi 3B+, obviously the 284x76 ST7789  TFT LCD, and a Neo M9N GPS module and a momentary pushbutton switch.
Setup for the GPS module and chrony are as in https://github.com/domschl/RaspberryNtpServer


### Enable SPI:
sudo raspi-config -> 3. Interface Options -> I4. SPI Enable

### I have used SPI1, as SPI0 was causing issues with the GPIO pin used for PPS sensing.  Changes to be made to /boot/firmware/config.txt:
##Enable SPI1, set CS to pin 17  
dtparam=spi=on  
dtoverlay=spi1-1cs,cs0_pin=17  
##Disable video (we are running headless!)  
#dtoverlay=vc4-kms-v3d  
max_framebuffers=0  
##Disable Bluetooth/WiFi (we are connected via ethernet)  
dtoverlay=disable-wifi  
dtoverlay=disable-bt  
enable_uart=1  
##Permanent PPS Lock (didn't really work, hence why we are using SPI1)  
gpio=4=ip,pud_off  
dtoverlay=pps-gpio,gpiopin=4  
##Disable HDMI/Video output to save power & reduce jitter  
hdmi_blanking=2  
force_turbo=1  

### Install required dependencies:  
gpsd gpsd-clients chrony python3-pip python3-dev libffi-dev libssl-dev libjpeg-dev zlib1g-dev i2c-tools -y
(Some of these may need to be installed in a Python virtual environment, that is currently how I have this working.)

### Wiring connections (display)
| Display Pin | Pi Physical Pin | BCM / Function |
| :--- | :--- | :--- |
| VCC (3.3V) | Pin 17 | 3.3V Power |
| GND | Pin 20 | Ground |
| DC (Data/Cmd) | Pin 15 | GPIO 22 |
| RES (Reset) | Pin 36 | GPIO 27 |
| SDA (Data) | Pin 38 | GPIO 20 (SPI1 MOSI) |
| SCL (Clock) | Pin 40 | GPIO 21 (SPI1 SCLK) |
| BLK (Backlight) | Pin 1 | 3.3V (Always On) |

### Wiring connections (momentary switch)
| Pushbutton | Pi Physical Pin | BCM / Function |
| :--- | :--- | :--- |
| Leg A | Pin 16 | GPIO 23 |
| Leg B | Pin 14 | Ground |

### Things to do
1. Add STL file for 3D printed 1RU modular mount.  
2. Web interface for changing colours and selecting details about pages to display - maybe  
3. Change switch for rotary encoder - maybe

