from ultralytics import YOLO
import cv2
from collections import defaultdict
import requests

window_visible = False

# Load model AI YOLOv8 yang sudah ditraining
model = YOLO("best_fixed.pt")

# Garis batas virtual (posisi 50% dari tinggi layar)
LINE_Y = 0.5
cap = cv2.VideoCapture(0)

track_history = defaultdict(lambda: {"prev_cy": None})

API_URL = "http://127.0.0.1:8000/api/inventory"

# Cek apakah pintu kulkas terbuka atau tertutup via API backend
def read_door_state():
    try:
        r = requests.get("http://127.0.0.1:8000/api/door-state", timeout=0.5)
        return r.json().get("state", "UNKNOWN")
    except:
        return "UNKNOWN"

while True:
    ret, frame = cap.read()
    if not ret:
        break

    door_state = read_door_state()

    # Kamera & AI cuma aktif pas pintu terbuka (hemat resource/CPU)
    if door_state == "OPEN":
        if not window_visible:
            cv2.namedWindow("Smart Fridge Camera (AI)", cv2.WINDOW_NORMAL)
            window_visible = True

        h, w = frame.shape[:2]
        line_px = int(h * LINE_Y)

        cv2.line(frame, (0, line_px), (w, line_px), (0, 255, 255), 2)
        cv2.putText(frame, "LINE", (10, line_px - 8),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)

        # Deteksi + Melacak (tracking) barang dengan ByteTrack biar ID barang konsisten
        results = model.track(
            frame,
            conf=0.25,
            iou=0.45,
            tracker="bytetrack.yaml",
            persist=True,
            verbose=False
        )

        if results[0].boxes is not None and results[0].boxes.id is not None:
            boxes = results[0].boxes
            for box, track_id, cls_idx in zip(
                boxes.xyxy.tolist(),
                boxes.id.tolist(),
                boxes.cls.tolist()
            ):
                track_id = int(track_id)
                class_name = model.names[int(cls_idx)]
                x1, y1, x2, y2 = box
                
                # Hitung koordinat titik tengah (center-Y) dari barang
                cy = int((y1 + y2) / 2)

                state = track_history[track_id]
                prev_cy = state["prev_cy"]

                # Logika utama: Deteksi barang lewat garis (Atas->Bawah = MASUK, Bawah->Atas = KELUAR)
                if prev_cy is not None:
                    if prev_cy < line_px and cy >= line_px:
                        print(f"[AI] {class_name} MASUK! Mengirim data ke server...")
                        try:
                            requests.post(API_URL, json={"item_name": class_name, "action": "MASUK"})
                        except Exception as e:
                            print("Gagal kirim ke backend:", e)

                    elif prev_cy >= line_px and cy < line_px:
                        print(f"[AI] {class_name} KELUAR! Mengirim data ke server...")
                        try:
                            requests.post(API_URL, json={"item_name": class_name, "action": "KELUAR"})
                        except Exception as e:
                            print("Gagal kirim ke backend:", e)

                # Simpan posisi Y sekarang untuk dibandingkan di frame selanjutnya
                state["prev_cy"] = cy

                # Gambar kotak & label barang di layar
                cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 200, 100), 2)
                cv2.putText(frame, f"{class_name} #{track_id}",
                            (int(x1), int(y1) - 8),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 200, 100), 1)
                cv2.circle(frame, (int((x1+x2)/2), cy), 4, (0, 255, 255), -1)

        cv2.imshow("Smart Fridge Camera (AI)", frame)

    # Kalau pintu tertutup, tutup jendela kamera
    else: 
        if window_visible:
            cv2.destroyWindow("Smart Fridge Camera (AI)")
            window_visible = False
            
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()