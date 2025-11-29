📡 PySDR-ADSB: Full-Stack Real-Time Radar & RF Lab

A "From Scratch" Software Defined Radio Implementation in Pure Python

Core Philosophy: No dump1090. No external C libraries. No black boxes. This project implements the entire receiver chain—from raw I/Q samples to a complex research dashboard—entirely in Python to demonstrate mastery of the RF Physical Layer.

📸 System Overview

The system features a dual-view interface: a tactical map for tracking and a dedicated research dashboard for signal analysis.

### Advanced RF Lab (DSP Analysis) / Tactical Radar View (Live Tracking)
- Real-time FFT, Doppler, and Path Loss analysis  
- Live aircraft tracking over the Mediterranean

⚡ **Key Engineering Capabilities**

## 🧠 1. The DSP Engine (CORE.py)

A custom-built signal processing pipeline handling **2,000,000 samples per second** in real-time:

- **Signal Conditioning:** DC offset removal & dynamic noise floor calculation  
- **Burst Detection:** Adaptive thresholding using statistical analysis (MAD/STD)  
- **Demodulation:** Custom implementation of PPM slicing  
- **Data Integrity:** Manual bitwise implementation of Mode-S CRC  
- **Navigation Logic:** Full CPR decoding to resolve global coordinates  

---

## 🔬 2. The RF Laboratory (MAIN.py)

Advanced physics and RF analysis tools:

- **Doppler Shift Analysis**  
- **Path Loss Validation** with Friis Equation  
- **Antenna Pattern Mapping**  
- **Time-Domain Fading Visualization**  
- **Real-time FFT** for the 1090 MHz band  

---

## 🕵️ 3. Hybrid Intelligence

- **OSINT Integration:** ICAO lookups  
- **Visual Confirmation:** Real-time aircraft imagery  

---

## 🛠 System Architecture

```
graph LR
    subgraph "Backend (DSP Process)"
        A[RTL-SDR USB] -->|I/Q Samples @ 2MSPS| B(Signal Conditioner)
        B -->|Magnitiude| C{Threshold Detect}
        C -->|Preamble Found| D[PPM Demodulator]
        D -->|Bits| E[CRC & Hex Decoder]
        E -->|Valid Message| F[CPR & Physics Engine]
    end

    subgraph "Network Layer"
        F -->|JSON Packet| G((UDP Socket 5005))
    end

    subgraph "Frontend (Visualization)"
        G -->|Stream| H[Main GUI Thread]
        H -->|Render| I[Map & Icons]
        H -->|Calc| J[RF Analytics Plots]
        H -.->|Async API| K[Cloud Data Source]
    end
```

---

## 🚀 Installation & Setup

### 1. Prerequisites

**Hardware:** RTL-SDR (Blog V3/V4 recommended) + 1090MHz antenna  
**Drivers:**  
```
sudo apt install librtlsdr-dev
```

---

### 2. Clone & Install

```bash
git clone https://github.com/your-username/PySDR-ADSB.git
cd PySDR-ADSB

python3 -m venv venv
source venv/bin/activate

pip install -r requirements.txt
```

---

### 3. ⚙ Configuration (Important)

Open `CORE.py` and `MAIN.py` and update:

```python
REF_LAT = 32.000
REF_LON = 34.000
```

---

## 🏃‍♂️ Usage

Start DSP + GUI:

```bash
python3 launcher.py
```

---

## 📂 Project Structure

| File | Description |
|------|-------------|
| CORE.py | DSP backend: I/Q, demod, decoding |
| MAIN.py | GUI frontend: mapping, analytics |
| launcher.py | Process orchestrator |
| requirements.txt | Dependencies |

---

## 📜 License

Educational & Research Use Only.  
Created as part of an Electrical Engineering DSP portfolio.
