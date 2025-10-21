import requests
import random
import time
from datetime import datetime, timedelta


# CONFIGURATION
API_URL = "http://127.0.0.1:5000/api/ingest"
NUM_FLIGHTS = 10           # how many flights to simulate
UPDATES_PER_FLIGHT = 12    # how many updates per flight
UPDATE_INTERVAL = 2        # seconds between updates (for simulation speed)

# Sample airports (ICAO codes)
AIRPORTS = [
    ("OPKC", 24.8607, 67.0011),  # Karachi
    ("OPRN", 33.6844, 73.0479),  # Islamabad
    ("OPLA", 31.5204, 74.3587),  # Lahore
    ("OPQT", 25.3786, 68.3634),  # Hyderabad
    ("OPPS", 34.0151, 71.5249),  # Peshawar
]

def random_airports():
    """Pick random origin and destination airports (must be different)."""
    origin, dest = random.sample(AIRPORTS, 2)
    return origin, dest


# SIMULATION FUNCTION
def simulate_flight(flight_id):
    origin, dest = random_airports()
    print(f"🛫 Simulating {flight_id} from {origin[0]} → {dest[0]}")

    base_lat = origin[1]
    base_lon = origin[2]
    dest_lat = dest[1]
    dest_lon = dest[2]

    # Linear interpolation of path
    for step in range(UPDATES_PER_FLIGHT):
        frac = step / (UPDATES_PER_FLIGHT - 1)
        lat = base_lat + (dest_lat - base_lat) * frac + random.uniform(-0.05, 0.05)
        lon = base_lon + (dest_lon - base_lon) * frac + random.uniform(-0.05, 0.05)
        altitude = int(10000 + frac * 25000)  # climbing then cruise
        heading = random.randint(0, 360)
        speed = random.randint(300, 500)
        timestamp = (datetime.utcnow() + timedelta(minutes=step * 5)).isoformat()

        payload = {
            "flight_id": flight_id,
            "timestamp": timestamp,
            "lat": lat,
            "lon": lon,
            "altitude_ft": altitude,
            "heading": heading,
            "speed_kts": speed
        }

        try:
            r = requests.post(API_URL, json=payload)
            if r.status_code == 200:
                print(f"Update {step+1}/{UPDATES_PER_FLIGHT}")
            else:
                print(f"Failed ({r.status_code}): {r.text}")
        except Exception as e:
            print(f"Error: {e}")

        time.sleep(UPDATE_INTERVAL)

    print(f"Flight {flight_id} simulation complete\n")


# MAIN
if __name__ == "__main__":
    for i in range(NUM_FLIGHTS):
        flight_id = f"PK{300 + i}"
        simulate_flight(flight_id)
    print("Simulation finished for all flights.")
