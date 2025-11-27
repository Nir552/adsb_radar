# ==============================================================================
# 📡 PROJECT: radar_ADS-B (גרסה סופית עם מרחק וחישובים משופרים)
# ==============================================================================

import numpy as np
import time
import math
import sys
from rtlsdr import RtlSdr

# --- הגדרות ---
REF_LAT = 31.999   # עוגן שוהם
REF_LON = 34.946   # עוגן שוהם

# --- חיבור לחומרה (SDR) ---
try:
    if 'sdr' in globals():
        try: sdr.close(); del sdr
        except: pass
    sdr = RtlSdr()
    sdr.sample_rate = 2e6
    sdr.center_freq = 1090e6
    sdr.freq_correction = 1
    sdr.gain = 49.6
except:
    print("SDR Not Found! בדוק חיבור USB."); sys.exit(1)

# --- עזרים מתמטיים ---
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

def calc_distance(lat1, lon1, lat2, lon2):
    """ חישוב מרחק בקילומטרים בין שתי נקודות (Haversine) """
    R = 6371.0 # רדיוס כדור הארץ בק"מ
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return round(R * c, 1)

# --- מפענחים (DECODERS) ---
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
    q_bit = bits[8] # ביט האיכות/סוג קידוד
    
    # תיקון: אם Q=0 זה קידוד ישן (Gray Code) שהקוד שלנו לא תומך בו כרגע
    if q_bit == 0:
        return None 
        
    val = bits_to_int(bits[:8] + bits[9:]) 
    alt_ft = val * 25 
    return int(alt_ft * 0.3048) # המרה למטרים

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

# --- תצוגת לוח מחוונים (DASHBOARD) ---
def update_dashboard(db):
    sys.stdout.write("\033[H\033[J")
    
    # הוספנו עמודת DST (מרחק)
    header = f"{'ICAO':<7} | {'CALLSIGN':<8} | {'ALT(m)':<6} | {'SPD':<4} | {'HDG':<3} | {'DST(km)':<7} | {'SEEN':<4} | {'LAT, LON'}"
    print("=" * 95)
    print("📡  ADS-B RADAR - SHOHAM STATION")
    print("-" * 95)
    print(header)
    print("-" * 95)
    
    sorted_p = sorted(db.items(), key=lambda x: x[1]['last'], reverse=True)
    current = time.time()
    
    for icao, p in sorted_p:
        ago = int(current - p['last'])
        if ago > 120: continue 
        
        color_on = "\033[92m" if ago < 5 else "\033[0m"
        color_off = "\033[0m"
        
        # טיפול בנתונים חסרים לתצוגה
        alt_str = str(p['alt']) if p['alt'] is not None else "?"
        spd_str = str(p['spd']) if p['spd'] != '?' else "?"
        hdg_str = str(p['hdg']) if p['hdg'] != '?' else "?"
        
        # חישוב מרחק אם יש מיקום
        dist_str = "?"
        loc_str = "Waiting for GPS..."
        if p['lat']:
            dist = calc_distance(REF_LAT, REF_LON, p['lat'], p['lon'])
            dist_str = str(dist)
            loc_str = f"{p['lat']:.4f}, {p['lon']:.4f}"

        line = f"{icao:<7} | {p['cs']:<8} | {alt_str:<6} | {spd_str:<4} | {hdg_str:<3} | {dist_str:<7} | {color_on}{ago}s{color_off}   | {loc_str}"
        print(line)

# --- לולאה ראשית ---
db = {}
last_screen = time.time()
print("מאתחל רדאר... נא להמתין")

try:
    while True:
        # תיקון 1: קריאת כמות גדולה של דגימות כדי לא לפספס הודעות
        raw = sdr.read_samples(256 * 1024)
        mag = np.abs(raw)
        
        mean_level = np.mean(mag)
        thresh = mean_level * 4.5
        peaks = np.where(mag > thresh)[0]
        last_p = -1
        
        for p in peaks:
            if p < last_p + 240 or p + 240 > len(mag): continue
            
            bits = []
            try:
                for n in range(112): 
                    bits.append(1 if mag[p+16+2*n] > mag[p+17+2*n] else 0)
            except: continue

            if bits_to_int(bits[0:5]) != 17: continue
            if modes_checksum(bits) != 0: continue
            
            icao = format(bits_to_int(bits[8:32]), '06X')
            tc = bits_to_int(bits[32:37])
            
            if icao not in db: 
                db[icao] = {'cs':'?', 'alt':None, 'spd':'?', 'hdg':'?', 'lat':None, 'lon':None, 'last':0}
            db[icao]['last'] = time.time()
            
            if 1 <= tc <= 4:
                db[icao]['cs'] = decode_callsign(bits)
            elif 9 <= tc <= 18:
                alt = decode_alt(bits)
                if alt is not None: # רק אם הקידוד תקין
                    db[icao]['alt'] = alt
                
                me = bits[32:88]
                try:
                    lat, lon = decode_cpr_local(bits_to_int(me[22:39]), bits_to_int(me[39:56]), me[21])
                    db[icao]['lat'] = lat
                    db[icao]['lon'] = lon
                except: pass
            elif tc == 19:
                spd, hdg = decode_velocity_and_heading(bits)
                if spd is not None and spd < 1500: 
                    db[icao]['spd'] = spd
                    db[icao]['hdg'] = hdg
            
            last_p = p
            
        if time.time() - last_screen > 0.5:
            update_dashboard(db)
            last_screen = time.time()

except KeyboardInterrupt:
    print("\nRadar OFF.")
    sdr.close()
