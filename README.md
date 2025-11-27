```markdown
# ✈️ ADS-B RADAR — Full End-to-End System  
RTL-SDR → DSP → Decoding → UDP JSON → GUI Radar Map

This project builds a complete real-time ADS-B receiver **from scratch**:
- Full RAW DSP (power extraction, smoothing, thresholding)
- Preamble detection (Mode-S)
- PPM bit decoding (112 bits)
- CRC validation + ADS-B message parsing  
- CPR local position decoding  
- UDP real-time aircraft stream  
- GUI radar with map, icons, trails, intelligence module  
- Research dashboard & FFT tools

---

# 📂 Project Structure

```
adsb_radar/
│
├── CORE.py     # Backend DSP + ADS-B decoder + UDP sender
├── MAIN.py     # Frontend GUI radar + map + plane visualization
├── README.md
└── archive/    # Old versions
```

---

# 🧠 System Architecture

```
+---------------------------- UDP JSON ----------------------------+
|                                                                 |
|                       (broadcasted every ~1s)                   |
+-----------------------------------------------------------------+

    +----------------------+                       +----------------------+
    |      CORE.py        | --------------------> |       MAIN.py        |
    +----------------------+                       +----------------------+
    | RTL-SDR capture      |                       | Radar GUI + map      |
    | Threshold detect     |                       | Aircraft markers     |
    | Preamble find        |                       | Trails + icons       |
    | Bit decoding (PPM)   |                       | Plane intelligence   |
    | CRC validation       |                       | Research dashboard   |
    | ADS-B message parse  |                       | FFT visualization    |
    | CPR local position   |                       | Data overlays        |
    +----------------------+                       +----------------------+
```

CORE.py continuously decodes aircraft and sends each one as a JSON packet via UDP.  
MAIN.py listens to UDP, draws the aircraft on a map GUI, and enriches data with intelligence.

---

# 🚀 Installation

## 1. Clone project
```bash
git clone <your-repo-url>
cd adsb_radar
```

---

## 2. Create virtual environment
```bash
python3 -m venv venv
source venv/bin/activate
```

---

## 3. Create `requirements.txt`
```txt
numpy
pillow
matplotlib
customtkinter
tkintermapview
requests
rtlsdr
```

Install:
```bash
pip install -r requirements.txt
```

---

## 4. Install RTL-SDR drivers (Linux)
```bash
sudo apt install rtl-sdr librtlsdr-dev
```

(Optional but recommended)
```bash
sudo apt install rtl-sdr-blacklist-dkms
```

---

# 🏃‍♂️ Running the System

## 🖥️ Terminal 1 — Backend (CORE)
```bash
cd adsb_radar
source venv/bin/activate
python3 CORE.py
```

### Expected output:
```
✅ SDR Connected.
🚀 DEBUG MODE: Starting Radar Loop...
✈️ NEW ICAO: 4XABC1 (RSSI: -47.2)
📍 LOC FIX...
📡 SENDING PLANES TO GUI
```

---

## 🖥️ Terminal 2 — Frontend (MAIN)
```bash
cd adsb_radar
source venv/bin/activate
python3 MAIN.py
```

### Expected GUI:
- Map centered on your location  
- Aircraft icons updated live  
- Trails behind each plane  
- Intelligence (airline / type / flags)  
- Live data table and speed/alt overlays  

---

# 📡 How the DSP Works (CORE.py)

### 1. Capture I/Q from RTL-SDR  
- tuned to 1090 MHz  
- 2 MHz samplerate  
- DC offset removal  

### 2. Convert complex IQ → power  
`power = I² + Q²`

### 3. Smooth power (moving average)  
Reduces noise enough to identify bursts.

### 4. Threshold detection (adaptive)  
MAD/STD based threshold:
- identifies bursts  
- isolates candidate messages  

### 5. Preamble search  
8-pulse Mode-S structure  
checks timing correctness

### 6. Bit decoding (PPM)  
112 bits extracted based on pulse timing.

### 7. CRC + ADS-B parse  
- DF17/DF18  
- ICAO  
- callsign  
- altitude  
- typecode  
- position (CPR)  
- velocity  

### 8. Send aircraft JSON via UDP  
Sent to MAIN.py every ~1s.

---

# 🗺️ GUI Features (MAIN.py)

- Real-time map (OpenStreetMap tiles)
- Aircraft icons (rotated by track angle)
- Trails (last positions)
- Plane intelligence:
  - airline lookup  
  - type lookup  
  - image fetch  
- Data overlays (speed, altitude, distance)
- FFT spectrum window
- Research dashboard:
  - counters  
  - RSSI charts  
  - ICAO logs  

---

# 🧪 Example UDP Packet

```json
{
    "icao": "4XABC1",
    "callsign": "ELY315",
    "lat": 32.0521,
    "lon": 34.8512,
    "alt": 11250,
    "speed": 455,
    "track": 278,
    "timestamp": 1732671927
}
```

---

# 🛠️ Notes

- Works with all RTL-SDR dongles (including Blog V4)
- Supports spider / ground plane / cantenna antennas
- GUI uses `customtkinter` for dark mode + performance
- CORE DSP is fully independent of dump1090  
  (no external decoders — everything custom)

---

# 📜 License
This project is for learning, research, and personal use.

---

# 🛰️ Credits
Built entirely from scratch as part of a full DSP learning journey.

```
