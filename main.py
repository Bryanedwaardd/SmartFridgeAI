from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base
import datetime
from collections import defaultdict

# 1. IMPORT LIBRARY UNTUK GEMINI
from google import genai
from google.genai import types
import os

# Variabel memori untuk menyimpan status pintu kulkas saat ini (OPEN/CLOSED)
_current_door_state = {"state": "UNKNOWN"}

# Berapa jam sebelum barang dianggap "sudah lama" di kulkas dan perlu dinotifikasi
NOTIFY_THRESHOLD_HOURS = 72  # 3 hari

# Skema validasi data penerimaan status pintu
class DoorStatePayload(BaseModel):
    state: str

# ==========================================
# SETUP DATABASE (SQLite)
# ==========================================
DATABASE_URL = "sqlite:///./fridge.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Tabel database untuk mencatat riwayat masuk/keluar barang
class FridgeLog(Base):
    __tablename__ = "fridge_logs"
    id = Column(Integer, primary_key=True, index=True)
    item_name = Column(String, index=True)
    action = Column(String)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

# Membuat tabel otomatis jika belum ada di database
Base.metadata.create_all(bind=engine)

# ==========================================
# SETUP FASTAPI SERVER
# ==========================================
app = FastAPI(title="Smart Fridge API Backend")

# Mengaktifkan CORS agar API bisa diakses dari frontend/aplikasi lain
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Skema data yang dikirim dari kamera AI saat barang masuk/keluar
class ItemPayload(BaseModel):
    item_name: str
    action: str

# Helper: Mengubah selisih detik menjadi format waktu yang mudah dibaca manusia
def humanize_duration(seconds: float) -> str:
    """Ubah durasi detik jadi teks singkat: '2 hari 3 jam', '4 jam 10 menit', dst."""
    seconds = max(0, int(seconds))
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, _ = divmod(rem, 60)
    if days > 0:
        return f"{days} hari {hours} jam"
    if hours > 0:
        return f"{hours} jam {minutes} menit"
    if minutes > 0:
        return f"{minutes} menit"
    return "baru saja"

# Helper: Menghitung total jumlah stok barang yang masih ada di kulkas
def calculate_current_inventory():
    db = SessionLocal()
    logs = db.query(FridgeLog).all()
    db.close()
    
    inventory = {}
    for log in logs:
        item = log.item_name
        if item not in inventory:
            inventory[item] = 0
        if log.action == "MASUK":
            inventory[item] += 1
        elif log.action == "KELUAR":
            inventory[item] = max(0, inventory[item] - 1)
            
    return {item: count for item, count in inventory.items() if count > 0}

# ==========================================
# ENDPOINTS API
# ==========================================

# 1. Endpoint menerima data barang masuk/keluar dari YOLO
@app.post("/api/inventory")
def log_item(payload: ItemPayload):
    action_upper = payload.action.upper()
    if action_upper not in ["MASUK", "KELUAR"]:
        raise HTTPException(status_code=400, detail="Action harus MASUK atau KELUAR")
    
    db = SessionLocal()
    try:
        new_log = FridgeLog(item_name=payload.item_name.lower(), action=action_upper)
        db.add(new_log)
        db.commit()
        return {"status": "success", "message": f"Berhasil mencatat {payload.item_name} {action_upper}"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

# 2. Endpoint mengambil total stok saat ini
@app.get("/api/inventory")
def get_inventory():
    return calculate_current_inventory()

# Helper: Menghitung umur/durasi simpan setiap unit barang dengan prinsip FIFO
def calculate_inventory_details():
    db = SessionLocal()
    try:
        logs = db.query(FridgeLog).order_by(FridgeLog.timestamp.asc()).all()
    finally:
        db.close()

    masuk_times = defaultdict(list)
    keluar_counts = defaultdict(int)
    for log in logs:
        item_name = log.item_name.lower()
        if log.action == "MASUK":
            masuk_times[item_name].append(log.timestamp)
        elif log.action == "KELUAR":
            keluar_counts[item_name] += 1

    now = datetime.datetime.utcnow()
    threshold_seconds = NOTIFY_THRESHOLD_HOURS * 3600
    details = {}
    for item_name, times in masuk_times.items():
        # Unit-unit yang paling lama sudah "dikeluarkan" (FIFO); sisanya masih di kulkas
        active_times = times[keluar_counts[item_name]:]
        if not active_times:
            continue
        items = []
        for t in sorted(active_times):
            duration_seconds = (now - t).total_seconds()
            items.append({
                "entered_at": t.isoformat() + "Z",
                "duration_seconds": int(duration_seconds),
                "duration_human": humanize_duration(duration_seconds),
                "is_stale": duration_seconds >= threshold_seconds,
            })
        details[item_name] = {"count": len(items), "items": items}

    return details

# 2b. Endpoint: Menampilkan rincian setiap unit barang beserta waktu masuknya
@app.get("/api/inventory/details")
def get_inventory_details():
    return calculate_inventory_details()

# 2c. Endpoint notifikasi: Menampilkan barang yang sudah terlalu lama disimpan
@app.get("/api/notifications")
def get_notifications(threshold_hours: float = NOTIFY_THRESHOLD_HOURS):
    threshold_seconds = threshold_hours * 3600
    details = calculate_inventory_details()

    stale_items = []
    for item_name, data in details.items():
        for unit in data["items"]:
            if unit["duration_seconds"] >= threshold_seconds:
                stale_items.append({"item_name": item_name, **unit})

    stale_items.sort(key=lambda x: x["duration_seconds"], reverse=True)
    return {"threshold_hours": threshold_hours, "count": len(stale_items), "items": stale_items}


# ====================================================
# 3. ENDPOINT BARU: GENERATE RESEP DENGAN GEMINI AI
# ====================================================

# Kunci API untuk otentikasi panggilan ke layanan Gemini AI
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Endpoint untuk meminta AI merekomendasikan resep berdasarkan stok bahan yang ada
@app.post("/api/recommend-recipe")
def recommend_recipe():
    # A. Ambil bahan makanan yang stoknya > 0 saat ini
    current_stock = calculate_current_inventory()
    
    if not current_stock:
        return {"recipe": "Kulkas kamu kosong nih! Masukkan beberapa bahan makanan terlebih dahulu lewat kamera agar AI bisa memberi resep."}
    
    # B. Gabungkan nama-nama bahan makanan menjadi satu teks string
    ingredients_list = ", ".join(current_stock.keys())
    
    # C. Buat prompt instruksi untuk Gemini — dibuat ketat & terstruktur biar output
    #    rapi dan pendek (= lebih cepat digenerate, tidak bertele-tele)
    prompt = (
        "Kamu adalah chef AI yang efisien. Bahan yang tersedia di kulkas: "
        f"{ingredients_list} (boleh tambah bumbu dapur umum: garam, gula, minyak, bawang).\n\n"
        "Beri TEPAT 2 rekomendasi resep yang HANYA memakai bahan di atas. "
        "Jawab LANGSUNG dengan format di bawah, TANPA kalimat pembuka/penutup/basa-basi apa pun:\n\n"
        "### 1. [Nama Resep]\n"
        "**Waktu:** [n] menit · **Porsi:** [n]\n"
        "**Bahan:**\n"
        "- [bahan] – [jumlah]\n"
        "**Langkah:**\n"
        "1. [langkah singkat, 1 kalimat]\n\n"
        "### 2. [Nama Resep]\n"
        "(format sama seperti resep 1)\n\n"
        "Aturan: maksimal 5 langkah per resep, tiap langkah 1 kalimat pendek dan langsung ke aksinya, "
        "bahasa Indonesia santai tapi jelas."
    )
    
    try:
        # D. Panggil API Gemini. thinking_budget=0 mematikan mode "berpikir" Gemini 2.5 Flash
        #    (fitur ini justru menambah latensi untuk tugas sederhana seperti ini),
        #    dan max_output_tokens dibatasi supaya respons tidak melebar dan tetap cepat.
        client = genai.Client(api_key=GEMINI_API_KEY)
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                thinking_config=types.ThinkingConfig(thinking_budget=0),
                max_output_tokens=700,
                temperature=0.4,
            ),
        )
        return {"recipe": response.text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal menghubungi Gemini AI: {str(e)}")

# Endpoint untuk membaca status pintu kulkas saat ini
@app.get("/api/door-state")
def get_door_state():
    return _current_door_state

# Endpoint untuk memperbarui status pintu kulkas dari Arduino
@app.post("/api/door-state")
def set_door_state(payload: DoorStatePayload):
    _current_door_state["state"] = payload.state.upper()
    return {"status": "ok"}