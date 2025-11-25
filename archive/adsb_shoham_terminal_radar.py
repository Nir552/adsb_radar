# ==============================================================================
# 📡 PROJECT ADS-B: SHOHAM TERMINAL RADAR
# ==============================================================================
# Focus: Pure RF & DSP Processing + Text Dashboard
# Logic: Fixed Local CPR (Shoham Anchor)
# ==============================================================================

import numpy as np
import time
import math
import sys
import os
from rtlsdr import RtlSdr

# --- CONFIGURATION ---
REF_LAT = 32.00   # Shoham / Center Israel
REF_LON = 34.88   # Shoham / Center Israel

# --- HARDWARE SETUP ---
try:
    if 'sdr' in globals():
        try: sdr.close(); del sdr
        except: pass
    sdr = RtlSdr()
    sdr.sample_rate = 2e6
    sdr.center_freq = 1090e6
    sdr.freq_correction = 1
    sdr.gain = 49.6
    sdr.read_samples(4096) # Warmup
    print("✅ Hardware Connected. Starting Radar...")
except Exception as e:
    print(f"❌ Hardware Error: {e}"); sys.exit(1)

# --- DECODING LOGIC ---

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
    val = bits_to_int(bits[:8] + bits[9:]) 
    alt_ft = val * 25 if q_bit else val * 100
    return int(alt_ft * 0.3048)

def decode_velocity(data_bits):
    me = data_bits[32:88]
    subtype = bits_to_int(me[5:8])
    v_ew_raw = bits_to_int(me[14:24])
    v_ns_raw = bits_to_int(me[25:35])
    
    if subtype in (1, 2) and v_ew_raw and v_ns_raw:
        v_ew = (v_ew_raw - 1) * (-1 if me[13] else 1)
        v_ns = (v_ns_raw - 1) * (-1 if me[24] else 1)
        
        # חישוב זווית טיסה (Heading)
        heading = math.degrees(math.atan2(v_ew, v_ns))
        if heading < 0: heading += 360
        
        # חישוב מהירות
        speed = math.sqrt(v_ew**2 + v_ns**2) * 1.852  # המרה לקמ"ש
        return int(speed), int(heading)
    return None, None

# --- LOCAL CPR SOLVER (The Fix) ---
def cpr_mod(a, b): res = a % b; return res if res >= 0 else res + b

def decode_cpr_local(lat_raw, lon_raw, is_odd):
    # Latitude
    dlat = 360.0 / (59.0 if is_odd else 60.0)
    j = math.floor(REF_LAT / dlat) + math.floor(0.5 + cpr_mod(REF_LAT, dlat) / dlat - lat_raw / 131072.0)
    lat_res = dlat * (j + lat_raw / 131072.0)
    
    # Longitude
    try:
        numerator = 1 - math.cos(math.pi / 30.0)
        denominator = (math.cos(math.pi / 180.0 * lat_res)) ** 2 - numerator
        nl = math.floor(2 * math.pi / math.acos(1 - numerator/denominator)) if denominator > 0 else 1
    except: nl = 1
    nl = max(nl, 1)
    dlon = 360.0 / max(nl - (1 if is_odd else 0), 1)
    
    # Snap to Anchor (Shoham Fix)
    lon_base = (lon_raw / 131072.0) * dlon
    closest_offset = round((REF_LON - lon_base) / dlon) * dlon
    lon_res = lon_base + closest_offset

    return round(lat_res, 5), round(lon_res, 5)

# --- DASHBOARD DISPLAY ---
def update_dashboard(db):
    # ניקוי מסך חלק (ללא הבהוב)
    buf = "\033[H\033[J"
    buf += f"=== 📡 SHOHAM RADAR STATUS | Tracking: {len(db)} ===\n"
    buf += "-" * 95 + "\n"
    buf += f"{'ICAO':<8} | {'CALLSIGN':<10} | {'ALT (m)':<8} | {'SPD':<5} | {'HDG':<4} | {'SEEN':<5} | {'POSITION'}\n"
    buf += "-" * 95 + "\n"
    
    current = time.time()
    # מיון: הכי חדש למעלה
    sorted_planes = sorted(db.items(), key=lambda x: x[1]['last'], reverse=True)
    
    for icao, p in sorted_planes:
        ago = int(current - p['last'])
        if ago > 120: continue # הסתרת ישנים
        
        # צבע ירוק למידע טרי (פחות מ-5 שניות)
        color = "\033[92m" if ago < 5 else "\033[0m"
        
        loc = f"{p['lat']:.4f}, {p['lon']:.4f}" if p['lat'] else "Calculating..."
        hdg_str = f"{int(p['hdg'])}°" if p['hdg'] else "-"
        
        buf += f"{icao:<8} | {p['cs']:<10} | {p['alt']:<8} | {p['spd']:<5} | {hdg_str:<4} | {color}{ago}s\033[0m    | {loc}\n"
    
    sys.stdout.write(buf)
    sys.stdout.flush()

# --- MAIN LOOP ---

db = {}
last_screen_update = time.time()

try:
    while True:
        # 1. קליטת דגימות
        raw = sdr.read_samples(256 * 1024)
        mag = np.abs(raw)
        thresh = np.mean(mag) * 4.0
        peaks = np.where(mag > thresh)[0]
        last_p = -1
        
        # 2. עיבוד האותות
        for p in peaks:
            if p < last_p + 240 or p + 240 > len(mag): continue
            
            bits = []
            try:
                for n in range(112): bits.append(1 if mag[p+16+2*n] > mag[p+17+2*n] else 0)
            except: continue

            if bits_to_int(bits[0:5]) != 17: continue
            if modes_checksum(bits) != 0: continue
            
            icao = format(bits_to_int(bits[8:32]), '06X')
            tc = bits_to_int(bits[32:37])
            
            if icao not in db:
                db[icao] = {'cs': '?', 'alt': '?', 'spd': '?', 'hdg': None, 'lat': None, 'lon': None, 'last': 0}
            
            db[icao]['last'] = time.time()
            
            if 1 <= tc <= 4:
                db[icao]['cs'] = decode_callsign(bits)
            elif 9 <= tc <= 18:
                db[icao]['alt'] = decode_alt(bits)
                me = bits[32:88]
                try:
                    lat, lon = decode_cpr_local(bits_to_int(me[22:39]), bits_to_int(me[39:56]), me[21])
                    db[icao]['lat'] = lat
                    db[icao]['lon'] = lon
                except: pass
            elif tc == 19:
                spd, hdg = decode_velocity(bits)
                if spd: 
                    db[icao]['spd'] = spd
                    db[icao]['hdg'] = hdg
            
            last_p = p

        # 3. עדכון תצוגה כל 0.5 שניות
        if time.time() - last_screen_update > 0.5:
            # מחיקת מטוסים שנעלמו (אחרי דקה)
            current = time.time()
            clean_db = {k: v for k, v in db.items() if current - v['last'] < 60}
            db = clean_db
            
            update_dashboard(db)
            last_screen_update = time.time()

except KeyboardInterrupt:
    print("\nRadar Closed.")
    sdr.close()
