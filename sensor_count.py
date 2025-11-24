import spidev
import time

spi = spidev.SpiDev()
spi.open(0, 0)
spi.max_speed_hz = 1350000

def read_adc(channel):
    adc = spi.xfer2([1, (8 + channel) << 4, 0])
    raw = ((adc[1] & 3) << 8) + adc[2]
    return raw

THRESHOLD = 200
MERGE_WINDOW = 1.0  # 1 second window merges wheel hits

# Channels
CH_IN = 0
CH_OUT = 1
CH_MID_OUT = 2
CH_MID_IN = 3

def triggered(v):
    return v > THRESHOLD

# Track last time each gate fired
last_in_time = 0
last_out_time = 0

# For the MID directional gate
mid_sequence = []
car_count = 0

print("Starting count:", car_count)

try:
    while True:

        now = time.time()

        s_in  = triggered(read_adc(CH_IN))
        s_out = triggered(read_adc(CH_OUT))
        s_mo  = triggered(read_adc(CH_MID_OUT))
        s_mi  = triggered(read_adc(CH_MID_IN))

        # ---------------------------------
        # IN GATE (single sensor)
        # ---------------------------------
        if s_in:
            if now - last_in_time > MERGE_WINDOW:
                car_count += 1
                print("Car ENTERED (IN). Count:", car_count)
                last_in_time = now  # reset timer
            # else: ignore second wheel

        # ---------------------------------
        # OUT GATE (single sensor)
        # ---------------------------------
        if s_out:
            if now - last_out_time > MERGE_WINDOW:
                car_count -= 1
                print("Car EXITED (OUT). Count:", car_count)
                last_out_time = now
            # else: ignore second wheel

        # ---------------------------------
        # MID GATE (two-sensor directional)
        # ---------------------------------
        if s_mo and (len(mid_sequence) == 0 or mid_sequence[-1] != "MID_OUT"):
            mid_sequence.append("MID_OUT")

        if s_mi and (len(mid_sequence) == 0 or mid_sequence[-1] != "MID_IN"):
            mid_sequence.append("MID_IN")

        # Direction detection
        if len(mid_sequence) >= 2:
            a, b = mid_sequence[0], mid_sequence[1]

            if a == "MID_OUT" and b == "MID_IN":
                car_count += 1
                print("Car ENTERED (MID). Count:", car_count)

            elif a == "MID_IN" and b == "MID_OUT":
                car_count -= 1
                print("Car EXITED (MID). Count:", car_count)

            mid_sequence.clear()

        # Clear MID if sensors not active & too old
        if not s_mo and not s_mi and len(mid_sequence) > 2:
            mid_sequence.clear()

        time.sleep(0.02)

except KeyboardInterrupt:
    print("\nExiting…")
    spi.close()


