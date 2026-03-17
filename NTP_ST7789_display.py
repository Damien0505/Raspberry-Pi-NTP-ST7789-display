# =======================================================================
# GPS CLOCK DASHBOARD - VERSION 1.0 (Pi 3B+)
# Features: NTP Jitter Graph, GNSS Skyview, Peer Stats, & System Health
#
# Copyright (C) 2026  Damien Beeby
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
# =======================================================================


import time
import os
import subprocess
import threading
import socket
import json
import math
import psutil
from gpiozero import Button
from collections import deque
from luma.core.interface.serial import spi
from luma.lcd.device import st7789
from luma.core.render import canvas
from PIL import ImageFont

# --- HARDWARE CONFIGURATION ---
# Button connected between GPIO 23 and GND
BUTTON_PIN = 23
# SPI Display Pins for Pi 3B+
RST_GPIO, DC_GPIO = 27, 22
# Layout Constraints for the white display bar
X, Y = 12, 82
GRAPH_WIDTH = 100
SCALE = 10

# --- LCD & BUTTON INITIALIZATION ---
# button = Button(BUTTON_PIN)
# bounce_time=0.2 adds a 200ms software delay to ignore rapid 'chatter'
button = Button(BUTTON_PIN, bounce_time=0.2)

serial = spi(port=1, device=0, gpio_DC=DC_GPIO, gpio_RST=RST_GPIO, baudrate=8000000)
device = st7789(serial, width=320, height=240, rotate=0)
device.command(0x20) # Essential for correct color/inversion on this panel (0x20 or 0x21)

try:
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", 12)
    font_sm = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", 10)
except:
    font = font_sm = None

# --- STATE MANAGEMENT ---
class GlobalState:
    page = 0
    heartbeat = False
    history = deque([0] * GRAPH_WIDTH, maxlen=GRAPH_WIDTH)
    gps_data = {'mode':0, 'lat':0.0, 'lon':0.0, 'alt':0.0, 'sats':[], 'hdop':0.0, 'tdop':0.0}
    lock = threading.Lock()

state = GlobalState()

def next_page():
    state.page = (state.page + 1) % 5

# Set up button to cycle pages
button.when_pressed = next_page

# --- GPSD DATA BACKGROUND THREAD ---
# Pulls JSON data from the local gpsd socket to keep Skyview updated
def gps_thread():
    while True:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(5)
            s.connect(('127.0.0.1', 2947))
            s.sendall(b'?WATCH={"enable":true,"json":true}\n')
            with s.makefile() as f:
                for line in f:
                    data = json.loads(line)
                    with state.lock:
                        if data.get('class') == 'TPV':
                            state.gps_data.update({
                                'mode': data.get('mode', 0),
                                'lat': data.get('lat', 0.0),
                                'lon': data.get('lon', 0.0),
                                'alt': data.get('alt', 0.0)
                            })
                        elif data.get('class') == 'SKY':
                            state.gps_data.update({
                                'sats': data.get('satellites', []),
                                'hdop': data.get('hdop', 0.0),
                                'tdop': data.get('tdop', 0.0)
                            })
        except: time.sleep(2)

threading.Thread(target=gps_thread, daemon=True).start()

# --- DRAWING UTILITIES ---
def get_sat_color(sat):
    """Returns color based on GNSS constellation and lock status"""
    if not sat.get('used'): return "red"
    svid, gnssid = sat.get('PRN', 0), sat.get('gnssid', 0)
    if gnssid == 0 or (1 <= svid <= 32): return "green"   # GPS
    if gnssid == 2 or (65 <= svid <= 96): return "cyan"    # GLONASS
    if gnssid == 3 or (svid > 300): return "magenta"      # Galileo
    if gnssid == 5 or (200 <= svid <= 299): return "orange" # BeiDou
    return "blue"

def draw_common(draw):
    """Clears the bar and toggles the activity heartbeat dot"""
    draw.rectangle((X, Y, X + 296, Y + 76), fill="white")
    state.heartbeat = not state.heartbeat
    if state.heartbeat:
        draw.ellipse((X + 285, Y + 5, X + 289, Y + 9), fill="red")

# --- PAGE RENDERERS ---

def render_ntp(draw):
    """PAGE 0: Main NTP Tracking Dashboard with Jitter Graph"""
    stats = {'time': time.strftime("%H:%M:%S %d/%m/%y"), 'strat': '?',
             'sys_offset': '0ns', 'lock': ' ', 'ref_id': 'None', 'raw_nano': 0, 'sats': '0/0'}
    try:
        track = subprocess.check_output(["chronyc", "-n", "tracking"], timeout=0.5).decode().splitlines()
        for line in track:
            if "Stratum" in line: stats['strat'] = line.split(":")[1].strip()
            if "System time" in line:
                p = line.split(":")[1].strip().split()
                nano = int(float(p[0]) * 1e9)
                stats['sys_offset'] = f"{'-' if 'slow' in p else '+'}{abs(nano)}ns"
                stats['raw_nano'] = -nano if "slow" in p else nano

        with state.lock:
            used = sum(1 for s in state.gps_data['sats'] if s.get('used'))
            stats['sats'] = f"{used}/{len(state.gps_data['sats'])}"

        sources = subprocess.check_output(["chronyc", "-n", "sources"], timeout=0.5).decode().splitlines()
        for line in sources:
            if line.startswith(('*', '#*')):
                stats['lock'] = "*"; stats['ref_id'] = "PPS" if "PPS" in line else line[3:15].strip()
    except: pass

    state.history.append(stats['raw_nano'])
    abs_diff = abs(stats['raw_nano'])
    text_col = "red" if abs_diff > 1000 else "orange" if abs_diff > 500 else "black"

    draw.text((X+10, Y+6), stats['time'], fill=text_col, font=font)
    draw.text((X+10, Y+24), f"S[{stats['strat']}] Diff: {stats['sys_offset']}", fill=text_col, font=font)
    draw.text((X+10, Y+42), f"L[{stats['lock']}] Ref: {stats['ref_id']}", fill="black", font=font)
    draw.text((X+10, Y+58), f"Sats: {stats['sats']} Off: {stats['sys_offset']}", fill="navy", font=font)

    gx, gy, mid_y = X+185, Y+8, Y+38
    draw.rectangle((gx, gy, gx+100, gy+60), outline="gray")
    h_list = list(state.history)
    for i in range(len(h_list)-1):
        y1, y2 = mid_y - (h_list[i]//SCALE), mid_y - (h_list[i+1]//SCALE)
        y1, y2 = max(gy, min(y1, gy+60)), max(gy, min(y2, gy+60))
        dist = abs(mid_y - y1)
        l_col = "red" if dist > 22.5 else "orange" if dist > 7.5 else "green"
        draw.line((gx+i, y1, gx+i+1, y2), fill=l_col)

def render_gps_sky(draw):
    """PAGE 1: GPS Fix Info and Satellite Skyview Map"""
    with state.lock: d = state.gps_data.copy()
    draw.text((X+8, Y+5), f"Mode: {d['mode']}D Fix", fill="black", font=font)
    draw.text((X+8, Y+22), f"Lat: {d['lat']:.5f}", fill="black", font=font)
    draw.text((X+8, Y+39), f"Lon: {d['lon']:.5f}", fill="black", font=font)
    draw.text((X+8, Y+56), f"Alt: {d['alt']:.1f}m", fill="black", font=font)

    used = sum(1 for s in d['sats'] if s.get('used'))
    draw.text((X+115, Y+5), f"Sats: {used}/{len(d['sats'])}", fill="navy", font=font)
    draw.text((X+115, Y+30), f"HDOP: {d['hdop']:.2f}", fill="black", font=font)
    draw.text((X+115, Y+50), f"TDOP: {d['tdop']:.2f}", fill="black", font=font)

    cx, cy, r = X + 245, Y + 38, 30
    draw.ellipse((cx-r, cy-r, cx+r, cy+r), outline="gray")
    for s in d['sats']:
        if 'el' in s and 'az' in s:
            rs = r * (1 - (s['el']/90.0))
            ar = math.radians(s['az'] - 90)
            sx, sy = cx + rs*math.cos(ar), cy + rs*math.sin(ar)
            color = get_sat_color(s)
            dot = 3 if s.get('used') else 2
            draw.ellipse((sx-dot, sy-dot, sx+dot, sy+dot), fill=color)

def render_sources(draw):
    """PAGE 2: Instantaneous Chrony Peer Sources"""
    try:
        raw = subprocess.check_output(["chronyc", "-n", "sources"], timeout=0.5).decode().splitlines()
        draw.text((X+5, Y+5), f"{'MS':<3} {'Address':<15} {'St':<2} {'Offset'}", fill="navy", font=font)
        draw.line((X+5, Y+18, X+290, Y+18), fill="gray")
        row_y = Y+22
        for line in raw[3:7]:
            p = line.split()
            if len(p) >= 6:
                col = "darkgreen" if "*" in p[0] else "black"
                draw.text((X+5, row_y), f"{p[0]:<3} {p[1][:15]:<15} {p[2]:<2} {p[-1]}", fill=col, font=font)
                row_y += 13
    except: pass

def render_sourcestats(draw):
    """PAGE 3: Long-term Peer Statistics (Drift & Error)"""
    try:
        raw = subprocess.check_output(["chronyc", "-n", "sourcestats"], timeout=0.5).decode().splitlines()
        draw.text((X+5, Y+5), f"{'Address':<15} {'NP':<4} {'Offset':<8} {'StdDev'}", fill="navy", font=font)
        draw.line((X+5, Y+19, X+290, Y+18), fill="gray")
        row_y = Y+24
        for line in raw[3:7]:
            p = line.split()
            if len(p) >= 6:
                draw.text((X+5, row_y), f"{p[0]:<15} {p[1]:<4} {p[4]:<8} {p[5]}", fill="black", font=font)
                row_y += 12
    except: pass

def render_system(draw):
    """PAGE 4: Hardware Monitor (Load, RAM, Temp, Core Utilization)"""
    load = os.getloadavg()
    with open("/sys/class/thermal/thermal_zone0/temp", "r") as f: cpu_temp = int(f.read())/1000.0
    ram, disk = psutil.virtual_memory(), psutil.disk_usage('/')
    cores = psutil.cpu_percent(percpu=True)
    with open('/proc/uptime', 'r') as f: ut = float(f.readline().split()[0])
    uptime_str = f"{int(ut//3600)}h {int((ut%3600)//60)}m {int(ut%60)}s"

    draw.text((X+8, Y+5),  f"Load: {load[0]:.2f} {load[1]:.2f} {load[2]:.2f}", fill="black", font=font)
    draw.text((X+8, Y+20), f"RAM:  {ram.percent}% ({ram.available//1024**2}M free)", fill="black", font=font)
    draw.text((X+8, Y+35), f"Disk: {disk.percent}% ({disk.free//1024**3}G free)", fill="black", font=font)
    t_col = "red" if cpu_temp > 60 else "orange" if cpu_temp > 50 else "darkgreen"
    draw.text((X+8, Y+50), f"CPU Temp: {cpu_temp:.1f}°C", fill=t_col, font=font)
    draw.text((X+8, Y+64), f"UP: {uptime_str}", fill="navy", font=font)

    for i in range(min(len(cores), 4)):
        bx, pct = X+195 + (i*24), cores[i]
        bh = int((pct/100)*45)
        draw.rectangle((bx, Y+18, bx+16, Y+65), outline="gray")
        f_col = "red" if pct > 85 else "orange" if pct > 60 else "green"
        draw.rectangle((bx+1, Y+65-bh, bx+15, Y+65), fill=f_col)
        draw.text((bx+2, Y+5), f"C{i}", fill="black", font=font_sm)

# --- EXECUTION ENGINE ---
page_map = {0: render_ntp, 1: render_gps_sky, 2: render_sources, 3: render_sourcestats, 4: render_system}

try:
    while True:
        with canvas(device) as draw:
            draw_common(draw)
            page_map[state.page](draw)
        time.sleep(1)
except KeyboardInterrupt:
    print("\nDashboard Stopped.")
