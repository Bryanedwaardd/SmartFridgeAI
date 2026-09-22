🥗 Smart Fridge AI System
  Sistem inventaris kulkas pintar berbasis AI dan Computer Vision. Sistem ini melacak bahan makanan masuk dan keluar secara real-time menggunakan pendeteksian objek dan visual line crossing tracking, mengelola stok di database, serta memberikan rekomendasi resep masakan berbasis AI.
🚀 Fitur Utama
  Real-Time Object Detection & Tracking: Menggunakan model YOLO11m dan ByteTrack untuk mendeteksi serta melacak pergerakan bahan makanan yang dimasukkan atau dikeluarkan dari kulkas (virtual line crossing).
  Backend API & Data Management: Dibangun menggunakan FastAPI dan SQLAlchemy (SQLite) untuk mengelola state inventaris barang dan riwayat transaksi secara efisien.
  AI Recipe Recommendation: Menganalisis ketersediaan bahan makanan di dalam kulkas untuk merekomendasikan resep masakan secara otomatis menggunakan integrasi Gemini API.
  Hardware Integration: Terhubung dengan sensor pintu dan kontroler Arduino untuk memicu sesi pemindaian kamera secara otomatis saat pintu kulkas dibuka/ditutup.
  🛠️ Tech Stack
  Core & Logic: Python 3.10+
  Computer Vision: OpenCV, Ultralytics YOLO11, ByteTrack
  Backend Framework: FastAPI, Uvicorn
  Database & ORM: SQLite, SQLAlchemy
  AI Integration: Google GenAI / Gemini API
  Hardware Interfacing: PySerial, Arduino (Door Sensor)
🏗️ Arsitektur Sistem
[ Sensor Pintu Arduino ]
          │ (Trigger Open/Close)
          ▼
[ Pipeline Computer Vision ] ───► (YOLO11m + ByteTrack) ───► Track In/Out Line
          │
          ▼
[ FastAPI Backend Engine ]  ───► (SQLAlchemy / SQLite)   ───► Auto Inventory Update
          │
          ▼
[ AI Recipe Generator ]     ───► (Gemini API)            ───► Rekomendasi Resep


📦 Instalasi & Persiapan
  Prasyarat
  Python 3.10 atau versi yang lebih baru
  Webcam / Kamera terhubung ke sistem
  Board Arduino dengan sensor pintu (opsional untuk simulasi lokal)
  Langkah-Langkah
  Clone repositori ini:
  git clone https://github.com/username/smart-fridge-ai.git
  cd smart-fridge-ai


Buat dan aktifkan Virtual Environment:
  python -m venv venv
  # macOS/Linux:
  source venv/bin/activate
  # Windows:
  venv\Scripts\activate


Instal dependensi:
  pip install -r requirements.txt


Konfigurasi Environment Variables:
  Buat file .env di root direktori dan tambahkan API Key kamu:
  GEMINI_API_KEY=your_gemini_api_key_here
  CAMERA_INDEX=0
  SERIAL_PORT=COM3 # Sesuaikan dengan port Arduino


⚙️ Cara Menjalankan
  Jalankan Backend Server (FastAPI):
  uvicorn main:app --reload
  
  Dokumentasi API Swaggernya dapat diakses di http://localhost:8000/docs.
  Jalankan Main Pipeline (Vision & Tracking):
  python run.py


📄 Lisensi
Proyek ini dilindungi di bawah lisensi MIT.
