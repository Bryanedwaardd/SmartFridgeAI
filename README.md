# 🥗 Smart Fridge AI System

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![YOLOv11](https://img.shields.io/badge/YOLOv11-Ultralytics-00FFFF?style=flat)](https://docs.ultralytics.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Sistem inventaris kulkas pintar berbasis AI dan Computer Vision. Sistem ini melacak bahan makanan masuk dan keluar secara *real-time* menggunakan pendeteksian objek dan visual line crossing tracking, mengelola stok di database, serta memberikan rekomendasi resep masakan berbasis AI.

---

## 🚀 Fitur Utama

- **Real-Time Object Detection & Tracking:** Menggunakan model **YOLO11m** dan **ByteTrack** untuk mendeteksi serta melacak pergerakan bahan makanan yang dimasukkan atau dikeluarkan dari kulkas (*virtual line crossing*).
- **Backend API & Data Management:** Dibangun menggunakan **FastAPI** dan **SQLAlchemy (SQLite)** untuk mengelola *state* inventaris barang dan riwayat transaksi secara efisien.
- **AI Recipe Recommendation:** Menganalisis ketersediaan bahan makanan di dalam kulkas untuk merekomendasikan resep masakan secara otomatis menggunakan integrasi **Gemini API**.
- **Hardware Integration:** Terhubung dengan sensor pintu dan kontroler **Arduino** untuk memicu sesi pemindaian kamera secara otomatis saat pintu kulkas dibuka/ditutup.

---

## 🛠️ Tech Stack

- **Core & Logic:** Python 3.10+
- **Computer Vision:** OpenCV, Ultralytics YOLO11, ByteTrack
- **Backend Framework:** FastAPI, Uvicorn
- **Database & ORM:** SQLite, SQLAlchemy
- **AI Integration:** Google GenAI / Gemini API
- **Hardware Interfacing:** PySerial, Arduino (Door Sensor)

---

## 🏗️ Arsitektur Sistem

```text
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
