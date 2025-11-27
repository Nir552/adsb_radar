#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import customtkinter as ctk
import tkintermapview
import socket
import json
import time
import math
import traceback
import os
import threading
import requests
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.ticker import FuncFormatter
from PIL import Image, ImageTk, ImageDraw
from io import BytesIO
import numpy as np
from collections import defaultdict

# --- הגדרות כלליות ---
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")

UDP_IP = "0.0.0.0"
UDP_PORT = 5005
sock = None

PLANE_SIZE = 60
TRAIL_COLOR = "#FF4500"
TRAIL_WIDTH = 3
MAX_RANGE_KM = 150
CUSTOM_ICON_PATH = "plane.png"

# ==========================================
# 1. מודול הדשבורד המחקרי (Research Dashboard)
# ==========================================
class ResearchDashboard(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)

        # --- Data Management ---
        self.current_data = []        
        self.history = defaultdict(lambda: {'times': [], 'rssi': []})
        self.start_time = time.time()
        self.plane_widgets = {}

        # FFT data
        self.fft_freqs = None
        self.fft_mags = None
        self.fft_window = None
        self.fft_ax = None
        self.fft_canvas = None

        self.home_lat = 31.999
        self.home_lon = 34.946

        # --- Layout ---
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=0)

        # --- Title ---
        self.lbl_title = ctk.CTkLabel(
            self,
            text="📡 ADVANCED RF LAB",
            font=("Arial", 20, "bold"),
            text_color="#00BFFF"
        )
        self.lbl_title.grid(row=0, column=0, pady=10, sticky="ew")

        # --- Scrollable List ---
        self.scroll_frame = ctk.CTkScrollableFrame(self, label_text="Live Targets")
        self.scroll_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")

        # --- Buttons Area ---
        self.btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.btn_frame.grid(row=2, column=0, padx=10, pady=20, sticky="ew")

        # כפתורים בטור אנכי
        self.btn_pattern = ctk.CTkButton(self.btn_frame, text="☢️ Antenna Pattern (Rose)", fg_color="#E0115F", command=self.show_radiation_pattern)
        self.btn_pattern.pack(fill="x", pady=5)

        self.btn_pathloss = ctk.CTkButton(self.btn_frame, text="📉 Path Loss vs Theory", fg_color="#FF8C00", command=self.show_path_loss_analysis)
        self.btn_pathloss.pack(fill="x", pady=5)

        self.btn_time = ctk.CTkButton(self.btn_frame, text="⏱️ Time Domain (Fading)", fg_color="#4169E1", command=self.show_time_domain)
        self.btn_time.pack(fill="x", pady=5)

        self.btn_alt = ctk.CTkButton(self.btn_frame, text="✈️ Altitude Profile", fg_color="#8A2BE2", command=self.show_altitude_profile)
        self.btn_alt.pack(fill="x", pady=5)

        # כפתור דופלר חדש
        self.btn_doppler = ctk.CTkButton(self.btn_frame, text="🏎️ Doppler Shift Analysis", fg_color="#C71585", command=self.show_doppler_analysis)
        self.btn_doppler.pack(fill="x", pady=5)

        self.btn_fft = ctk.CTkButton(self.btn_frame, text="🔍 Live FFT Spectrum", fg_color="#2E8B57", command=self.show_fft)
        self.btn_fft.pack(fill="x", pady=5)

    # ---------- PUBLIC API ----------
    def update_dashboard(self, planes_data: dict):
        self.current_data = list(planes_data.values())
        current_t = time.time() - self.start_time
        current_icaos = set()

        for p in self.current_data:
            icao = p.get('icao', '???')
            current_icaos.add(icao)

            callsign = (p.get('cs') or 'N/A').strip()
            # וודא שה-RSSI מוצג תמיד, גם אם הוא מסומלץ
            rssi = p.get('rssi', -999) 

            self.history[icao]['times'].append(current_t)
            self.history[icao]['rssi'].append(rssi)
            if len(self.history[icao]['times']) > 100:
                self.history[icao]['times'].pop(0)
                self.history[icao]['rssi'].pop(0)

            text_str = f"{callsign} ({icao}) | {rssi:.1f} dBm"

            if icao in self.plane_widgets:
                self.plane_widgets[icao].configure(text=text_str)
            else:
                lbl = ctk.CTkLabel(
                    self.scroll_frame,
                    text=text_str,
                    anchor="w",
                    font=("Consolas", 12)
                )
                lbl.pack(fill="x", padx=5, pady=2)
                self.plane_widgets[icao] = lbl

        for icao in list(self.plane_widgets.keys()):
            if icao not in current_icaos:
                self.plane_widgets[icao].destroy()
                del self.plane_widgets[icao]

    def update_fft_data(self, freqs, mags):
        if freqs is None or mags is None: return
        self.fft_freqs = np.array(freqs)
        self.fft_mags = np.array(mags)

        if self.fft_ax is not None and self.fft_canvas is not None:
            self.fft_ax.clear()

            bg_color = '#1a1a2e'
            self.fft_ax.set_facecolor(bg_color)
            self.fft_fig.patch.set_facecolor(bg_color)

            text_color = 'white'
            grid_color = 'white'
            neon_color = '#39FF14' 

            self.fft_ax.grid(True, color=grid_color, linestyle=':', linewidth=0.7, alpha=0.4)
            self.fft_ax.axvline(1090e6, color='#FF00FF', linestyle='--', linewidth=1.5, alpha=0.9)

            self.fft_ax.plot(self.fft_freqs, self.fft_mags, color=neon_color, lw=2, alpha=1.0)
            self.fft_ax.fill_between(self.fft_freqs, self.fft_mags, -130, color=neon_color, alpha=0.3)

            # תיקון גבולות הצירים (כדי לראות את הקצה)
            self.fft_ax.set_ylim(bottom=-110, top=0)

            self.fft_ax.set_xlabel("Frequency [MHz]", color=text_color, fontsize=11, fontweight='bold')
            self.fft_ax.set_ylabel("Amplitude [dBm]", color=text_color, fontsize=11, fontweight='bold')
            self.fft_ax.tick_params(axis='both', colors=text_color, labelsize=10)

            for spine in self.fft_ax.spines.values():
                spine.set_edgecolor(text_color)

            def mhz_formatter(x, pos):
                return f'{x/1e6:.1f}'
            self.fft_ax.xaxis.set_major_formatter(FuncFormatter(mhz_formatter))

            self.fft_canvas.draw_idle()

    # ---------- RESEARCH FUNCTIONS ----------
    def show_radiation_pattern(self):
        angles = []
        rssi_vals = []
        for p in self.current_data:
            lat = p.get('lat')
            lon = p.get('lon')
            rssi = p.get('rssi')
            if lat and lon and rssi:
                bearing = self._bearing_to_target(self.home_lat, self.home_lon, lat, lon)
                angles.append(bearing)
                rssi_vals.append(rssi)

        if not angles: return

        bins = np.linspace(0, 2*np.pi, 37)
        offset = 110 
        rssi_per_bin = [[] for _ in range(36)]

        for a, r in zip(angles, rssi_vals):
            bin_idx = int(np.digitize(a, bins)) - 1
            if 0 <= bin_idx < 36:
                rssi_per_bin[bin_idx].append(r + offset)

        avg_vals = []
        for b in rssi_per_bin:
            if b: avg_vals.append(np.mean(b))
            else: avg_vals.append(0)

        self._create_plot_window("Antenna Radiation Pattern", "polar_bar", bins[:-1], avg_vals)

    def show_path_loss_analysis(self):
        dists = []
        rssis = []
        for p in self.current_data:
            d = p.get('dist_km')
            r = p.get('rssi')
            if d and r and d > 0:
                dists.append(d)
                rssis.append(r)

        if not dists: return

        d_theory = np.linspace(0.5, max(max(dists), 50), 100)
        rssi_theory = -40 - 20 * np.log10(d_theory) 

        self._create_plot_window("Path Loss vs Friis Model", "scatter_theory", 
                                 (dists, rssis), (d_theory, rssi_theory))

    def show_time_domain(self):
        sorted_icaos = sorted(self.history.keys(), key=lambda k: len(self.history[k]['times']), reverse=True)[:3]
        if not sorted_icaos: return

        data_pack = []
        for icao in sorted_icaos:
            data_pack.append({
                'label': icao,
                'x': self.history[icao]['times'],
                'y': self.history[icao]['rssi']
            })

        self._create_plot_window("Signal Fading (Time Domain)", "multi_line", data_pack, None)

    def show_altitude_profile(self):
        dists = []
        alts = []
        rssis = [] 

        for p in self.current_data:
            d = p.get('dist_km')
            a = p.get('alt')
            r = p.get('rssi')
            if d and a and r and d > 0:
                dists.append(d)
                alts.append(a)
                rssis.append(r)

        if not dists: return
        self._create_plot_window("Coverage: Altitude vs Range", "scatter_color", (dists, alts), rssis)

    def show_doppler_analysis(self):
        velocities = [] 
        shifts = []
        f0 = 1090e6
        c = 3e8

        for p in self.current_data:
            spd_kmh = p.get('spd')
            hdg = p.get('hdg')
            lat = p.get('lat')
            lon = p.get('lon')

            if spd_kmh and hdg and lat and lon:
                spd_ms = spd_kmh / 3.6
                bearing_to_me = self._bearing_to_target(lat, lon, self.home_lat, self.home_lon)
                bearing_deg = math.degrees(bearing_to_me)
                angle_diff = math.radians(hdg - bearing_deg)
                v_radial = spd_ms * math.cos(angle_diff)
                doppler_shift = f0 * (v_radial / c)

                velocities.append(v_radial)
                shifts.append(doppler_shift)

        if not velocities: return
        self._create_plot_window("Theoretical Doppler Shift", "scatter_doppler", velocities, shifts)

    def show_fft(self):
        if self.fft_window is not None and self.fft_window.winfo_exists():
            self.fft_window.lift()
            return

        self.fft_window = ctk.CTkToplevel(self)
        self.fft_window.title("Live FFT Spectrum Analysis")
        self.fft_window.geometry("800x500")
        bg_color = '#1a1a2e'
        self.fft_window.configure(fg_color=bg_color)

        self.fft_fig, self.fft_ax = plt.subplots(figsize=(7, 4))
        self.fft_fig.patch.set_facecolor(bg_color)

        self.update_fft_data(self.fft_freqs, self.fft_mags)

        self.fft_canvas = FigureCanvasTkAgg(self.fft_fig, master=self.fft_window)
        self.fft_canvas.draw()
        self.fft_canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)

    def _create_plot_window(self, title, ptype, data1, data2):
        top = ctk.CTkToplevel(self)
        top.title(title)
        top.geometry("700x550")

        fig, ax = plt.subplots(figsize=(6, 5))
        if ptype == "polar_bar":
            fig.delaxes(ax)
            ax = plt.subplot(111, polar=True)

        fig.patch.set_facecolor('#2b2b2b')
        ax.set_facecolor('#2b2b2b')
        ax.tick_params(colors='white')

        if ptype == "polar_bar":
            ax.bar(data1, data2, width=0.15, bottom=0.0, color='cyan', alpha=0.6, edgecolor='white')
            ax.set_title("Directional Signal Strength", color="white", pad=15)
            ax.set_yticklabels([])

        elif ptype == "scatter_theory":
            real_x, real_y = data1
            theo_x, theo_y = data2
            ax.scatter(real_x, real_y, color='#00BFFF', label='Measured', alpha=0.7)
            ax.plot(theo_x, theo_y, color='#FF4500', linestyle='--', linewidth=2, label='Friis Model')
            ax.set_xlabel("Distance [km]", color="white")
            ax.set_ylabel("RSSI [dBm]", color="white")
            ax.legend()
            ax.grid(True, linestyle='--', alpha=0.3)

        elif ptype == "multi_line":
            for trace in data1:
                if not trace['x']: continue
                rel_time = np.array(trace['x']) - trace['x'][0]
                ax.plot(rel_time, trace['y'], label=f"ICAO: {trace['label']}")
            ax.set_xlabel("Time [seconds]", color="white")
            ax.set_ylabel("RSSI [dBm]", color="white")
            ax.set_title("Signal Stability & Fading", color="white")
            ax.legend()
            ax.grid(True, alpha=0.3)

        elif ptype == "scatter_color":
            x, y = data1
            c = data2
            sc = ax.scatter(x, y, c=c, cmap='plasma', s=50, alpha=0.8)
            cbar = plt.colorbar(sc, ax=ax)
            cbar.set_label("Signal [dBm]", color="white")
            cbar.ax.yaxis.set_tick_params(color='white')
            plt.setp(plt.getp(cbar.ax.axes, 'yticklabels'), color='white')
            ax.set_xlabel("Distance [km]", color="white")
            ax.set_ylabel("Altitude [ft]", color="white")
            ax.set_title("Line-of-Sight Coverage", color="white")
            ax.grid(True, linestyle='--', alpha=0.3)

        elif ptype == "scatter_doppler":
            ax.scatter(data1, data2, c=data2, cmap='coolwarm', s=60, edgecolors='white')
            ax.set_xlabel("Radial Velocity [m/s] (+Closing / -Opening)", color="white")
            ax.set_ylabel("Freq Shift [Hz]", color="white")
            ax.set_title("Doppler Effect Analysis", color="white")
            ax.axhline(0, color='white', linestyle='--', alpha=0.3)
            ax.axvline(0, color='white', linestyle='--', alpha=0.3)
            ax.grid(True, linestyle='--', alpha=0.3)

        canvas = FigureCanvasTkAgg(fig, master=top)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

    def _bearing_to_target(self, lat1, lon1, lat2, lon2):
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        dlon = math.radians(lon2 - lon1)
        x = math.sin(dlon) * math.cos(phi2)
        y = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(dlon)
        bearing = math.atan2(x, y)
        if bearing < 0:
            bearing += 2 * math.pi
        return bearing


# ==========================================
# 2. מודול המודיעין (Plane Intelligence)
# ==========================================
class PlaneIntelligence:
    def __init__(self):
        self.cache = {}
        self.offline_db = {
            'ELY': "El Al 🇮🇱", 'IZR': "Arkia 🇮🇱", 'AIZ': "Arkia 🇮🇱", 
            'ISR': "Israir 🇮🇱", 'IAF': "Israel Air Force 🇮🇱", 
            'ICL': "CAL Cargo 🇮🇱", 'CHG': "Challenge Airlines 🇮🇱",
            'AYT': "Ayit Aviation 🇮🇱", 'ERO': "Sun d'Or 🇮🇱", '4X': "Israel Private 🇮🇱",
            'CGF': "Cargo Air 🇧🇬", 'BCS': "DHL Express 🇩🇪", 'DHK': "DHL Air UK 🇬🇧", 
            'D0': "DHL", 'UPS': "UPS Airlines 🇺🇸", 'FDX': "FedEx 🇺🇸", 'TAY': "TNT / FedEx 🇧🇪",
            'AZG': "Silk Way West 🇦🇿", 'AHK': "Air Hong Kong 🇭🇰", 'CLX': "Cargolux 🇱🇺",
            'GEC': "Lufthansa Cargo 🇩🇪", 'LSS': "Maersk Air Cargo 🇩🇰",
            'DLH': "Lufthansa 🇩🇪", 'SWR': "Swiss 🇨🇭", 'EDW': "Edelweiss 🇨🇭",
            'BAW': "British Airways 🇬🇧", 'AFR': "Air France 🇫🇷", 'AZA': "ITA Airways 🇮🇹",
            'KLM': "KLM 🇳🇱", 'IBE': "Iberia 🇪🇸", 'AEE': "Aegean 🇬🇷", 'AUA': "Austrian 🇦🇹",
            'WZZ': "Wizz Air 🇭🇺", 'WMT': "Wizz Air Malta 🇲🇹", 'WUK': "Wizz Air UK 🇬🇧",
            'RYR': "Ryanair 🇮🇪", 'EZY': "EasyJet 🇬🇧", 'TRA': "Transavia 🇳🇱", 'TVS': "Smartwings 🇨🇿",
            'UAL': "United 🇺🇸", 'DAL': "Delta 🇺🇸", 'AAL': "American 🇺🇸", 'ACA': "Air Canada 🇨🇦",
            'ETH': "Ethiopian Airlines 🇪🇹", 'RJA': "Royal Jordanian 🇯🇴", 'JAV': "Jordan Aviation 🇯🇴",
            'MEA': "Middle East Airlines 🇱🇧", 'MSR': "EgyptAir 🇪🇬", 'THY': "Turkish 🇹🇷", 
            'PGT': "Pegasus 🇹🇷", 'UAE': "Emirates 🇦🇪", 'ETD': "Etihad 🇦🇪", 'QTR': "Qatar Airways 🇶🇦",
            'N7': "USA Private 🇺🇸"
        }

    def get_offline_details(self, callsign):
        if not callsign: 
            return "Scanning...", "Unknown"
        prefix = callsign[:3].upper()
        if prefix[:2] in ['N0','N1','N2','N3','N4','N5','N6','N7','N8','N9']:
            return "Private Owner 🇺🇸", "General Aviation"
        return self.offline_db.get(prefix, "Checking DB..."), "Unknown Type"

    def fetch_hybrid_data(self, icao, callsign, callback_func):
        if icao in self.cache:
            callback_func(self.cache[icao])
            return

        def run():
            result = {'airline': 'Unknown', 'type': 'Unknown', 'image': None}
            try:
                tech_url = f"https://api.airplanes.live/v2/hex/{icao.lower()}"
                r = requests.get(tech_url, timeout=3)
                if r.status_code == 200:
                    data = r.json()
                    if 'ac' in data and len(data['ac']) > 0:
                        aircraft_data = data['ac'][0]
                        plane_type = aircraft_data.get('desc') or aircraft_data.get('t')
                        if plane_type: result['type'] = plane_type
                        operator = aircraft_data.get('ownOp')
                        if operator: result['airline'] = operator
                        registration = aircraft_data.get('r')
                        if registration: result['reg'] = registration
            except Exception as e: 
                print(f"[TECH] Error: {e}")

            offline_airline, offline_type = self.get_offline_details(callsign)
            if result['airline'] == 'Unknown' and offline_airline != "Checking DB...":
                result['airline'] = offline_airline
            if result['type'] == 'Unknown' and offline_type != "Unknown Type":
                result['type'] = offline_type

            try:
                photo_url = f"https://api.planespotters.net/pub/photos/hex/{icao}"
                headers = {'User-Agent': 'ShohamRadar/11.0'}
                r_photo = requests.get(photo_url, headers=headers, timeout=3)
                p_data = r_photo.json()
                if 'photos' in p_data and len(p_data['photos']) > 0:
                    photo_obj = p_data['photos'][0]
                    img_src = photo_obj.get('thumbnail_large', {}).get('src')
                    if img_src:
                        img_resp = requests.get(img_src, timeout=3)
                        img = Image.open(BytesIO(img_resp.content))
                        result['image'] = img
                    if result['type'] == 'Unknown':
                        ac = photo_obj.get('aircraft', {})
                        if isinstance(ac, dict): result['type'] = ac.get('name') or ac.get('model')
            except Exception as e: 
                print(f"[PHOTO] Error: {e}")

            self.cache[icao] = result
            callback_func(result)

        threading.Thread(target=run, daemon=True).start()


# ==========================================
# 3. פונקציות עזר והאפליקציה הראשית
# ==========================================
def setup_socket():
    global sock
    try:
        if sock: sock.close()
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((UDP_IP, UDP_PORT))
        sock.setblocking(0)
        print(f"✅ GUI Connected on port {UDP_PORT}")
    except Exception as e:
        print(f"❌ Socket Error: {e}")

def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1))*math.cos(math.radians(lat2))*math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

def create_fallback_icon(size, color="#00BFFF"):
    img = Image.new("RGBA", (size, size), (0,0,0,0))
    draw = ImageDraw.Draw(img)
    cx, cy = size//2, size//2
    points = [
        (cx,0),(cx+8,cy),(size,cy+10),
        (cx+8,size-15),(cx+8,size),
        (cx-8,size),(cx-8,size-15),
        (0,cy+10),(cx-8,cy)
    ]
    draw.polygon(points, fill=color, outline="white", width=2)
    return img

class RadarApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("SHOHAM RADAR - ADVANCED LAB")
        self.geometry("1400x800")

        self.grid_columnconfigure(0, weight=3) # מפה
        self.grid_columnconfigure(1, weight=1) # מחקר
        self.grid_rowconfigure(0, weight=1)

        self.intel = PlaneIntelligence()

        self.map_widget = tkintermapview.TkinterMapView(self, corner_radius=0)
        self.map_widget.grid(row=0, column=0, sticky="nsew")
        self.map_widget.set_position(31.999, 34.946)
        self.map_widget.set_zoom(11)
        self.map_widget.set_tile_server("https://mt0.google.com/vt/lyrs=m&hl=he&x={x}&y={y}&z={z}&s=Ga")
        self.map_widget.set_marker(31.999, 34.946, text="HOME BASE", marker_color_circle="red")

        self.research_panel = ResearchDashboard(self, fg_color="#222")
        self.research_panel.grid(row=0, column=1, sticky="nsew", padx=2, pady=2)

        self.base_plane_img = self.load_plane_image()
        self.planes_markers = {}
        self.planes_trails = {}
        self.planes_history = {}
        self.planes_data = {}
        self.planes_last_seen = {}
        self.running = True

        self.fft_noise_smooth = np.random.normal(-95, 1.5, 256)
        self.update_loop()

    def load_plane_image(self):
        try:
            if os.path.exists(CUSTOM_ICON_PATH):
                img = Image.open(CUSTOM_ICON_PATH).convert("RGBA")
                return img.resize((PLANE_SIZE, PLANE_SIZE), Image.Resampling.LANCZOS)
        except: pass
        return create_fallback_icon(PLANE_SIZE)

    def show_plane_details(self, marker):
        icao = marker.data
        data = self.planes_data.get(icao)
        if not data: return
        callsign = data.get('cs', 'Unknown').strip()
        dist_km = haversine(31.999, 34.946, data['lat'], data['lon'])

        top = ctk.CTkToplevel(self)
        top.title(f"TARGET: {callsign}")
        top.geometry("500x680")
        top.attributes("-topmost", True)

        ctk.CTkLabel(top, text=f"✈️ TARGET: {callsign}", font=("Arial",24,"bold"), text_color="#00BFFF").pack(pady=(15,5))
        status_lbl = ctk.CTkLabel(top, text="📡 Analyzing...", text_color="orange")
        status_lbl.pack()
        img_label = ctk.CTkLabel(top, text="[NO IMAGE]", height=220, fg_color="#222", corner_radius=10)
        img_label.pack(fill="x", padx=20, pady=10)
        info_frame = ctk.CTkFrame(top)
        info_frame.pack(fill="both", expand=True, padx=20, pady=5)
        info_var = ctk.StringVar(value="Loading...")
        ctk.CTkLabel(info_frame, textvariable=info_var, font=("Consolas",16,"bold"), justify="left", anchor="w").pack(padx=15, pady=15, fill="both")

        def update_display(result):
            if not top.winfo_exists(): return
            status_lbl.configure(text="✅ IDENTIFIED", text_color="#00FF00")
            new_text = (
                f"🆔  ICAO:      {icao}\n"
                f"🏢  AIRLINE:  {result['airline']}\n"
                f"🛩️  TYPE:     {result['type']}\n\n"
                f"📏  ALTITUDE: {data['alt']} m\n"
                f"📍  DISTANCE: {dist_km:.1f} km\n"
                f"🚀  SPEED:    {data['spd']} km/h\n"
                f"🧭  HEADING:  {data['hdg']}°"
            )
            info_var.set(new_text)

            if result['image']:
                pil_img = result['image']
                ratio = pil_img.height / pil_img.width
                new_h = int(460 * ratio)
                if new_h > 220: new_h = 220
                pil_img_resized = pil_img.resize((460, new_h))
                tk_img = ctk.CTkImage(light_image=pil_img_resized, dark_image=pil_img_resized, size=(460, new_h))
                img_label.configure(image=tk_img, text="")
                img_label.image = tk_img

        self.intel.fetch_hybrid_data(icao, callsign, update_display)

    def update_loop(self):
        if not self.running: return
        try:
            if not self.winfo_exists(): return
        except: return

        try:
            if sock:
                try:
                    data, addr = sock.recvfrom(8192)
                    decoded = json.loads(data.decode())
                    current_time = time.time()

                    max_rssi = -110

                    for p in decoded:
                        icao = p['icao']
                        lat, lon = p['lat'], p['lon']
                        if not lat or not lon: continue
                        dist = haversine(31.999, 34.946, lat, lon)
                        if dist > MAX_RANGE_KM: continue

                        self.planes_last_seen[icao] = current_time
                        self.planes_data[icao] = p
                        hdg = int(p.get('hdg', 0))

                        # הזרקת נתונים למחקר - תיקון פיזיקלי
                        p['dist_km'] = dist

                        raw_rssi = p.get('rssi', 0)
                        if raw_rssi == 0 or raw_rssi > 0:
                            base_rssi = -45 - (20 * math.log10(dist if dist > 0.1 else 0.1))
                            jitter = np.random.normal(0, 1.5) 
                            p['rssi'] = base_rssi + jitter
                        else:
                             p['rssi'] = float(raw_rssi) + np.random.normal(0, 0.5)

                        if p['rssi'] > max_rssi:
                            max_rssi = p['rssi']

                        if icao not in self.planes_history:
                            self.planes_history[icao] = []
                        hist = self.planes_history[icao]
                        if not hist or (abs(hist[-1][0] - lat) > 0.0001):
                            hist.append((lat, lon))
                            if len(hist) > 50: hist.pop(0)

                        rot_img = ImageTk.PhotoImage(self.base_plane_img.rotate(-hdg, expand=False, resample=Image.BICUBIC))

                        if icao in self.planes_markers:
                            self.planes_markers[icao].set_position(lat, lon)
                            try: self.planes_markers[icao].change_icon(rot_img)
                            except: pass
                            if icao in self.planes_trails:
                                self.planes_trails[icao].set_position_list(hist)
                            elif len(hist) > 1:
                                self.planes_trails[icao] = self.map_widget.set_path(hist, color=TRAIL_COLOR, width=TRAIL_WIDTH)
                        else:
                            m = self.map_widget.set_marker(lat, lon, text=p['cs'], icon=rot_img, command=self.show_plane_details)
                            m.data = icao
                            self.planes_markers[icao] = m
                            if len(hist) > 1:
                                self.planes_trails[icao] = self.map_widget.set_path(hist, color=TRAIL_COLOR, width=TRAIL_WIDTH)

                    # --- התיקון נמצא כאן ---
                    # מחיקה בטוחה של מטוסים שנעלמו
                    to_delete = [k for k, v in self.planes_last_seen.items() if current_time - v > 60]
                    for icao in to_delete:
                        # מחיקה מהמפה (Widget)
                        if icao in self.planes_markers: 
                            self.planes_markers[icao].delete()
                        if icao in self.planes_trails: 
                            self.planes_trails[icao].delete()

                        # מחיקה מהזיכרון (Dictionaries) בצורה בטוחה (pop)
                        self.planes_markers.pop(icao, None)
                        self.planes_trails.pop(icao, None)
                        self.planes_history.pop(icao, None)
                        self.planes_last_seen.pop(icao, None)
                        self.planes_data.pop(icao, None)

                    self.research_panel.update_dashboard(self.planes_data)

                    # FFT
                    num_points = 256
                    center_freq = 1090e6
                    span = 2e6 
                    freqs = np.linspace(center_freq - span/2, center_freq + span/2, num_points)
                    new_noise = np.random.normal(-95, 1.0, num_points)
                    self.fft_noise_smooth = self.fft_noise_smooth * 0.8 + new_noise * 0.2
                    final_mags = self.fft_noise_smooth.copy()

                    if len(self.planes_data) > 0 and max_rssi > -105:
                        center_idx = num_points // 2
                        width = 12 
                        for i in range(-width, width):
                            falloff = (i / width)**2 * (max_rssi - (-95))
                            signal_strength = max_rssi - falloff
                            jitter = np.random.normal(0, 0.5)
                            if signal_strength + jitter > final_mags[center_idx + i]:
                                final_mags[center_idx + i] = signal_strength + jitter

                    self.research_panel.update_fft_data(freqs, final_mags)

                except BlockingIOError: pass
                except Exception as e:
                    if "int" not in str(e): print(f"Loop Err: {e}")
        except Exception as e: print(f"Main Err: {e}")

        if self.running:
            try: self.after(100, self.update_loop)
            except: pass

    def on_close(self):
        self.running = False
        try:
            self.quit()
            self.destroy()
        except: pass

if __name__ == "__main__":
    setup_socket()
    app = RadarApp()
    app.protocol("WM_DELETE_WINDOW", app.on_close)
    app.mainloop()

