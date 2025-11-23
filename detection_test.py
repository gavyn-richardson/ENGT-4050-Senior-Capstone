import cv2
import torch
import time
import json
import socket
from picamera2 import Picamera2

# Configuration
LOT_NAME = "LotA"
TOTAL_SPOTS = 50
SERVER_IP = "127.0.0.1"  # laptop or localhost
SERVER_PORT = 5000        # port your laptop server is listening on

# Load YOLOv5 model
model = torch.hub.load('ultralytics/yolov5', 'yolov5n', pretrained=True)
model.conf = 0.45
model.iou = 0.6

# Start PiCamera2
picam2 = Picamera2()
picam2.configure(picam2.create_preview_configuration(
    main={"format": "XRGB8888", "size": (640, 480)}
))
picam2.start()

vehicle_classes = [2, 3, 5, 7]  # car, motorcycle, bus, truck

# Setup socket
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect((SERVER_IP, SERVER_PORT))

while True:
    start_time = time.time()

    # Capture frame
    frame = picam2.capture_array()
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    # Run YOLO detection
    results = model(rgb)
    detections = results.pandas().xyxy[0]

    # Count vehicles
    count = 0
    for _, row in detections.iterrows():
        if row['class'] in vehicle_classes:
            x1, y1, x2, y2 = map(int, (row['xmin'], row['ymin'], row['xmax'], row['ymax']))
            w, h = x2 - x1, y2 - y1
            if w < 30 or h < 30:
                continue
            count += 1
            conf = row['confidence']
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(frame, f"{row['name']} {conf:.2f}",
                        (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX,
                        0.6, (0, 255, 0), 2)

    # Display count on frame
    cv2.putText(frame, f"Cars: {count}", (frame.shape[1] - 150, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

    # Prepare JSON
    data = {
        "lot": LOT_NAME,
        "total_spots": TOTAL_SPOTS,
        "occupied_spots": count
    }
    json_str = json.dumps(data)

    # Send JSON over socket
    sock.sendall(json_str.encode("utf-8"))

    # Show frame
    cv2.imshow("Vehicle Detection", frame)

    # Wait 15 seconds
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break
    elapsed = time.time() - start_time
    if elapsed < 15:
        time.sleep(15 - elapsed)

cv2.destroyAllWindows()
picam2.stop()
sock.close()
