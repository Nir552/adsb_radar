# ADS-B Radar (RTL-SDR 1090MHz)

This project is a **from-scratch ADS-B receiver and decoder**, written entirely in Python, processing raw RF signals from an RTL-SDR at 1090 MHz.

The goal:  
Understand and implement the full **physical layer** of ADS-B — from I/Q samples → magnitude → pulse detection → PPM demodulation → CRC → message decoding → live radar display.

---

## ✈️ Features

### ✔ Real-time SDR capture  
- RTL-SDR direct sampling at **2 MSPS**  
- Gain control optimized for weak / strong signals  
- Large buffer reads to avoid packet loss  

### ✔ DSP Pipeline  
- Magnitude extraction  
- Dynamic thresholding  
- Peak detection  
- 112-bit **PPM demodulation**  
- Mode-S CRC check (poly: `0xFFF409`)  

### ✔ ADS-B Message Decoding  
- DF=17 Extended Squitter  
- ICAO  
- Callsign (Type Code 1–4)  
- Altitude (Type Code 9–18)  
- Airborne Velocity (Type Code 19)  
- Local CPR position decoding  

### ✔ Live Terminal Radar  
Displays:  
- ICAO  
- Callsign  
- Altitude  
- Speed / Heading  
- Position (lat/lon)  
- Last seen  
- Packet count (Booster version)

---

## 📁 Repository Structure

```
adsb_radar/
├── adsb_booster_radar.py
├── adsb_shoham_terminal_radar.py
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

Run the optimized Booster version:

```bash
python adsb_booster_radar.py
```

Or run the Shoham Terminal version:

```bash
python adsb_shoham_terminal_radar.py
```

---

## 🗺 Next Steps (Work in Progress)

- GUI Radar (map + tracks)
- Decoder refactor into modules (`decoder/`, `dsp/`, `gui/`)
- Recording I/Q data for offline DSP analysis
- Interactive web dashboard
- Add Docker environment

---

## 📌 Notes

This project is intentionally built **from scratch**, without using any existing ADS-B decoding libraries — to understand every stage of the physical-layer signal chain.

