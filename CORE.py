#!/usr/bin/env python
# coding: utf-8

# In[ ]:


# ==============================================================================
# 📡 ADS-B BACKEND: DIAGNOSTIC MODE
# ==============================================================================
import numpy as np
import time
import math
import sys
import socket
import json
from rtlsdr import RtlSdr

# --- רשת ---
UDP_IP = "127.0.0.1"
UDP_PORT = 5005
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

REF_LAT = 31.999
REF_LON = 34.946

# --- חומרה ---
try:
    if 'sdr' in globals():
        try: sdr.close(); del sdr
        except: pass
    sdr = RtlSdr()
    sdr.sample_rate = 2e6
    sdr.center_freq = 1090e6
    sdr.freq_correction = 1
    sdr.gain = 49.6
    print("✅ SDR Connected.")
except:
    print("❌ SDR Error."); sys.exit(1)

# --- פענוח (הקוד שלך) ---
def bits_to_int(bits):
    v = 0
    for b in bits: v = (v << 1) | int(b)
    return v

def modes_checksum(data_bits):
    poly = [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 1, 0, 0, 0, 0, 0, 0, 1, 0, 0, 1]
    bits = list(data_bits)
    for i in range(len(bits) - 24):
        if bits[i] == 1:
            for j in range(len(poly)): bits[i+j] ^= poly[j]
    return bits_to_int(bits[-24:])

def decode_callsign(data_bits):
    chars = "#ABCDEFGHIJKLMNOPQRSTUVWXYZ#####_###############0123456789######"
    me = data_bits[32:88]
    cs_bits = me[8:56]
    res = []
    for i in range(8):
        val = bits_to_int(cs_bits[i*6:(i+1)*6])
        res.append(chars[val] if val < len(chars) else ' ')
    return "".join(res).strip().replace("#", "").replace("_", "")

def decode_alt(data_bits):
    bits = data_bits[40:52]
    q_bit = bits[8]
    if q_bit == 0: return None
    val = bits_to_int(bits[:8] + bits[9:])
    alt_ft = val * 25
    return int(alt_ft * 0.3048)

def decode_velocity_and_heading(data_bits):
    me = data_bits[32:88]
    subtype = bits_to_int(me[5:8])
    if subtype in (1, 2):
        v_ew_raw = bits_to_int(me[14:24])
        v_ns_raw = bits_to_int(me[25:35])
        if v_ew_raw and v_ns_raw:
            v_ew = (v_ew_raw - 1) * (-1 if me[13] else 1)
            v_ns = (v_ns_raw - 1) * (-1 if me[24] else 1)
            speed_kts = math.sqrt(v_ew**2 + v_ns**2)
            speed_kmh = int(speed_kts * 1.852)
            heading_deg = math.degrees(math.atan2(v_ew, v_ns))
            if heading_deg < 0: heading_deg += 360
            return speed_kmh, int(heading_deg)
    return None, None

def cpr_mod(a, b): res = a % b; return res if res >= 0 else res + b

def decode_cpr_local(lat_raw, lon_raw, is_odd):
    dlat = 360.0 / (59.0 if is_odd else 60.0)
    j = math.floor(REF_LAT / dlat) + math.floor(0.5 + cpr_mod(REF_LAT, dlat) / dlat - lat_raw / 131072.0)
    lat_res = dlat * (j + lat_raw / 131072.0)
    try:
        numerator = 1 - math.cos(math.pi / 30.0)
        denominator = (math.cos(math.pi / 180.0 * lat_res)) ** 2 - numerator
        nl = math.floor(2 * math.pi / math.acos(1 - numerator/denominator)) if denominator > 0 else 1
    except: nl = 1
    nl = max(nl, 1)
    dlon = 360.0 / max(nl - (1 if is_odd else 0), 1)
    lon_base = (lon_raw / 131072.0) * dlon
    closest_offset = round((REF_LON - lon_base) / dlon) * dlon
    lon_res = lon_base + closest_offset
    return round(lat_res, 5), round(lon_res, 5)

# --- לולאה ראשית ---
db = {}
last_transmit = time.time()
print("📡 DEBUG MODE: Starting Radar Loop...")

try:
    while True:
        raw = sdr.read_samples(256 * 1024)
        mag = np.abs(raw)
        thresh = np.mean(mag) * 4.5
        peaks = np.where(mag > thresh)[0]
        last_p = -1

        for p in peaks:
            if p < last_p + 240 or p + 240 > len(mag): continue

            bits = []
            try:
                for n in range(112): bits.append(1 if mag[p+16+2*n] > mag[p+17+2*n] else 0)
            except: continue

            if bits_to_int(bits[0:5]) != 17: continue
            if modes_checksum(bits) != 0: continue

            # --- פענוח ---
            icao = format(bits_to_int(bits[8:32]), '06X')
            tc = bits_to_int(bits[32:37])
            rssi = float(np.mean(mag[p:p+200]))

            if icao not in db: 
                # מטוס חדש!
                print(f"✈️ NEW ICAO: {icao} (RSSI: {rssi:.1f})")
                db[icao] = {'icao': icao, 'cs':'?', 'alt':0, 'spd':0, 'hdg':0, 'lat':None, 'lon':None, 'last':0, 'rssi': rssi, 'msgs':0}

            db[icao]['last'] = time.time()
            db[icao]['msgs'] += 1

            if 1 <= tc <= 4:
                db[icao]['cs'] = decode_callsign(bits)
            elif 9 <= tc <= 18:
                alt = decode_alt(bits)
                if alt is not None: db[icao]['alt'] = alt
                me = bits[32:88]
                try:
                    lat, lon = decode_cpr_local(bits_to_int(me[22:39]), bits_to_int(me[39:56]), me[21])
                    db[icao]['lat'] = lat
                    db[icao]['lon'] = lon
                    print(f"📍 LOC FIX: {icao} -> {lat:.4f}, {lon:.4f}")
                except: pass
            elif tc == 19:
                spd, hdg = decode_velocity_and_heading(bits)
                if spd:
                    db[icao]['spd'] = spd
                    db[icao]['hdg'] = hdg

            last_p = p

        # שידור - פעם בשנייה נדפיס סטטוס
        if time.time() - last_transmit > 1.0:
            current = time.time()
            # כמה מטוסים פעילים יש בכלל?
            total_active = len([v for k, v in db.items() if current - v['last'] < 60])
            # כמה מהם יש להם מיקום?
            with_loc = [v for k, v in db.items() if (current - v['last'] < 60) and (v['lat'] is not None)]

            if len(with_loc) > 0:
                print(f"📤 SENDING {len(with_loc)} PLANES TO GUI (Total Visible: {total_active})")
                try:
                    message = json.dumps(with_loc)
                    sock.sendto(message.encode(), (UDP_IP, UDP_PORT))
                except Exception as e:
                    print(f"❌ UDP ERROR: {e}")
            else:
                if total_active > 0:
                    print(f"⚠️ Tracking {total_active} planes, but NO LOCATION yet. Waiting for CPR...")
                else:
                    print(f"📡 Scanning... (No targets)")

            last_transmit = time.time()

except KeyboardInterrupt:
    print("Stopped.")
    sdr.close()
    sock.close()

