import json
import time
import random
from pathlib import Path

OUTPUT_FILE = Path("output/spaces.json")

TOTAL_SPOTS = 58

# Load existing JSON or create a clean structure if not present
def load_current_data():
    if OUTPUT_FILE.exists():
        try:
            return json.loads(OUTPUT_FILE.read_text())
        except:
            pass

    # Fallback if file missing or invalid
    return {"LotA": {f"spot{i}": "open" for i in range(1, TOTAL_SPOTS + 1)}}

# Return a random new state
def random_state():
    return "occupied" if random.random() > 0.5 else "open"

# Pick 5 random spots and assign new random states
def update_five_random_spots(data):
    all_spots = list(data["LotA"].keys())
    picks = random.sample(all_spots, 5)

    for spot in picks:
        data["LotA"][spot] = random_state()

    return picks

if __name__ == "__main__":
    while True:
        data = load_current_data()
        changed = update_five_random_spots(data)

        OUTPUT_FILE.write_text(json.dumps(data, indent=2))
        print("Updated:", ", ".join(changed))

        # Change every 10 seconds
        time.sleep(10)