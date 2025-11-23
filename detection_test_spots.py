import cv2
import torch
import time
import json
from picamera2 import Picamera2

# --- Configuration ---
LOT_NAME = "LotA"
SERVER_IP = "127.0.0.1"
SERVER_PORT = 5000

# Load YOLOv5 model
model = torch.hub.load('ultralytics/yolov5', 'yolov5n', pretrained=True)
model.conf = 0.45
model.iou = 0.6

# Start camera
picam2 = Picamera2()
picam2.configure(picam2.create_preview_configuration(
    main={"format": "XRGB8888", "size": (640, 480)}
))
picam2.start()

vehicle_classes = [2, 3, 5, 7]  # car, motorcycle, bus, truck

# Define parking spots manually (x1, y1, x2, y2)
# Example: 5 spots
parking_spots = {
    "spot1": (50, 100, 120, 180),
    "spot2": (130, 100, 200, 180),
    "spot3": (210, 100, 280, 180),
    "spot4": (290, 100, 360, 180),
    "spot5": (370, 100, 440, 180)
}

# Socket setup (optional, if sending data)
import socket
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect((SERVER_IP, SERVER_PORT))

def is_occupied(spot_box, vehicle_boxes):
    """Check if any vehicle overlaps the parking spot."""
    x1s, y1s, x2s, y2s = spot_box
    for vb in vehicle_boxes:
        x1v, y1v, x2v, y2v = vb
        # Check if boxes overlap
        if x1v < x2s and x2v > x1s and y1v < y2s and y2v > y1s:
            return True
    return False

while True:
    start_time = time.time()

    # Capture frame
    frame = picam2.capture_array()
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    # Detect vehicles
    results = model(rgb)
    detections = results.pandas().xyxy[0]

    vehicle_boxes = []
    for _, row in detections.iterrows():
        if row['class'] in vehicle_classes:
            x1, y1, x2, y2 = map(int, (row['xmin'], row['ymin'], row['xmax'], row['ymax']))
            w, h = x2 - x1, y2 - y1
            if w < 30 or h < 30:
                continue
            vehicle_boxes.append((x1, y1, x2, y2))
            # Draw vehicle box
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0,255,0), 2)

    # Check each parking spot
    spot_status = {}
    for spot_name, spot_box in parking_spots.items():
        occupied = is_occupied(spot_box, vehicle_boxes)
        spot_status[spot_name] = "occupied" if occupied else "open"
        color = (0,0,255) if occupied else (0,255,0)
        x1, y1, x2, y2 = spot_box
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        cv2.putText(frame, spot_status[spot_name], (x1, y1 - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

    # Prepare JSON
    data = {
        "lot": LOT_NAME,
        "total_spots": len(parking_spots),
        "occupied_spots": sum(1 for s in spot_status.values() if s=="occupied"),
        "spots": spot_status
    }
    json_str = json.dumps(data)

    # Send JSON
    sock.sendall(json_str.encode("utf-8"))

    # Display
    cv2.imshow("Parking Detection", frame)

    # Wait 15 seconds
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break
    elapsed = time.time() - start_time
    if elapsed < 15:
        time.sleep(15 - elapsed)

cv2.destroyAllWindows()
picam2.stop()
sock.close()
