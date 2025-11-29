import subprocess
import time
import sys
import os

# הגדרת הפקודה (python או python3 בהתאם למערכת)
PYTHON_EXEC = sys.executable

print("🚀 Starting PySDR-ADSB System...")

try:
    # 1. הרצת ה-CORE (תהליך ברקע)
    print("📡 Initializing DSP Backend (CORE.py)...")
    core_process = subprocess.Popen([PYTHON_EXEC, "CORE.py"])
    
    # המתנה שה-SDR יתחבר ויתחיל לשדר UDP
    time.sleep(2)

    # 2. הרצת ה-MAIN (ה-GUI)
    print("🖥  Launching Radar Visualization (MAIN.py)...")
    main_process = subprocess.Popen([PYTHON_EXEC, "MAIN.py"])

    # המתנה לסיום ה-GUI (כשהמשתמש סוגר את החלון)
    main_process.wait()

except KeyboardInterrupt:
    print("\n🛑 Stopping system...")

finally:
    # סגירה נקייה של כל התהליכים
    try:
        core_process.terminate()
        main_process.terminate()
    except:
        pass
    print("✅ System Shutdown Complete.")

