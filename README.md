# ADS-B Radar (RTL-SDR 1090MHz)

A **from-scratch ADS-B receiver and decoder**, written entirely in Python, processing raw RF samples from an RTL-SDR.

The goal is to understand and implement the full **physical layer** of ADS-B —  
from raw IQ samples → magnitude → pulse detection → bitstream → full message decoding.

---

## ✈ Features

### ✔ Real-time SDR capture
- RTL-SDR sampling at **2 MSPS**
- Configurable gain
- Large buffered reads to avoid packet loss

### ✔ DSP Pipeline
- IQ → magnitude
- Dynamic thresholding
- Peak detection
- 112-bit **PPM demodulation**
- Full Mode-S CRC check (`0xFFF409`)

### ✔ ADS-B Message Decoding
- DF=17 Extended Squitter
- ICAO address
- Callsign (TC 1–4)
- Altitude (TC 9–18)
- Airborne velocity + heading (TC 19)
- Local CPR position decoding (Shoham-anchored reference)

### ✔ Live Terminal Radar
Displays:
- ICAO  
- Callsign  
- Altitude  
- Speed  
- Heading  
- Latitude/Longitude  
- Distance from station  
- Last seen time  

---

## 📁 Repository Structure

```
/adsb_radar
├── radar_adsb.py                 # Main radar script (distance, velocity, heading, CPR, improved decoding)
├── archive/                      # Older versions kept for history
│   ├── adsb_booster_radar.py
│   └── adsb_shoham_terminal_radar.py
├── README.md
└── .gitignore
```

---

## 🔧 Requirements

Install dependencies:

```bash
pip install numpy pyrtlsdr
```

---

## 🚀 Running the Radar

Start live decoding:

```bash
python3 radar_adsb.py
```

---

## 📡 Hardware Requirements
- RTL-SDR Blog V3/V4 (or any compatible 1090 MHz receiver)
- Python 3.8+
- Modules: `pyrtlsdr`, `numpy`

---

## 🛰 Project Philosophy

This project focuses on **understanding ADS-B at the physical layer**, without shortcuts:

- No `dump1090`
- No pre-made decoders
- Manual PPM pulse extraction
- Bit slicing
- CRC validation
- Local CPR decoding
- Velocity / heading reconstruction

Everything here is implemented by hand from raw RF → decoded messages.

---

## 🗺 Next Steps (Work in Progress)

- GUI Radar (map + aircraft tracks)
- Split project into modules (`dsp/`, `decoder/`, `gui/`)
- I/Q recording for offline DSP experiments
- Interactive web dashboard
