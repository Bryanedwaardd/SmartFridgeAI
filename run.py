import subprocess
import sys
import time
import signal
import serial
import serial.tools.list_ports
import threading
import requests

API_URL = "http://127.0.0.1:8000"

processes = {}
door_state = "UNKNOWN"

# Kirim status pintu (OPEN/CLOSED) ke API server backend
def send_door_state(state):
    try:
        requests.post("http://127.0.0.1:8000/api/door-state", json={"state": state}, timeout=1)
    except:
        pass

# Deteksi otomatis port USB tempat Arduino terhubung
def find_arduino():
    ports = serial.tools.list_ports.comports()
    for p in ports:
        desc = p.description.upper()
        if any(x in desc for x in ["CH340", "ARDUINO", "USB SERIAL", "FT232", "CP210X"]):
            return p.device
    return None

# Membaca log/output dari proses background dan mencetaknya ke terminal
def log_output(proc, label):
    try:
        for line in iter(proc.stdout.readline, ''):
            if line:
                print(f"[{label}] {line}", end='')
    except:
        pass

# Jalankan server FastAPI di background (proses terpisah)
def start_backend():
    if "backend" in processes:
        return
    print("Starting FastAPI Backend...")
    p = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    processes["backend"] = p
    threading.Thread(target=log_output, args=(p, "BACKEND"), daemon=True).start()

# Matikan semua proses background (kamera & backend) saat program dihentikan (Ctrl+C)
def cleanup(signum, frame):
    print("\nShutting down...")
    if "camera" in processes:
        processes["camera"].terminate()
    if "backend" in processes:
        processes["backend"].terminate()
    sys.exit(0)

signal.signal(signal.SIGINT, cleanup)
signal.signal(signal.SIGTERM, cleanup)

print("=" * 50)
print("Smart Fridge Controller")
print("Camera starts automatically when door opens")
print("=" * 50)

# 1. Memulai Backend
start_backend()
time.sleep(2)

# 2. Jalankan skrip AI kamera (test.py) sebagai proses background sejak awal
print("Starting AI Camera (runs forever)...")
p = subprocess.Popen(
    [sys.executable, "test.py"],
    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    text=True, bufsize=1
)
processes["camera"] = p
threading.Thread(target=log_output, args=(p, "CAMERA"), daemon=True).start()
send_door_state("OPEN") 

# 3. Loop utama: Menghubungkan & membaca data sensor pintu dari Arduino
ser = None
while True:
    # Coba hubungkan ulang jika koneksi ke Arduino terputus
    if ser is None or not ser.is_open:
        port = find_arduino()
        if not port:
            print("Arduino not found. Retrying in 3s...")
            time.sleep(3)
            continue
        try:
            ser = serial.Serial(port, 9600, timeout=1)
            time.sleep(2)  # Wait for Arduino reset
            print(f"Arduino connected on {port}")
        except Exception as e:
            print(f"Failed to connect: {e}")
            time.sleep(3)
            continue

    # Baca pesan dari Arduino (misal pesan berformat "~OPEN~" atau "~CLOSED~")
    try:
        if ser.in_waiting > 0:
            line = ser.readline().decode('utf-8').strip()
            
            if line.startswith("~"):
                new_state = line.split("~")[1]
                
                # Jika ada perubahan status pintu, update ke server backend
                if new_state != door_state:
                    door_state = new_state
                    print(f"Door state changed: {door_state}")
                    
                    send_door_state(door_state)

    except Exception as e:
        print(f"Serial error: {e}")
        ser.close()
        ser = None
        time.sleep(2)