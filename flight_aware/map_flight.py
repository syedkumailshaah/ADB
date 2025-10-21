import folium
import requests
import random

# ======== CONFIG =========
BASE_URL = "http://127.0.0.1:5000"
OUTPUT_FILE = "all_flights_map.html"
# ==========================

def get_active_flights():
    """Fetch all active flights from FastAPI."""
    resp = requests.get(f"{BASE_URL}/api/active")
    if resp.status_code != 200:
        print("❌ Error fetching active flights:", resp.text)
        return []
    data = resp.json().get("active_flights", [])
    return data

def get_flight_path(flight_id):
    """Fetch the tracking path for a specific flight."""
    resp = requests.get(f"{BASE_URL}/api/track/{flight_id}")
    if resp.status_code != 200:
        return None
    data = resp.json()
    return data.get("path", [])

# ==========================
# MAIN MAP GENERATION
# ==========================

flights = get_active_flights()
if not flights:
    print("⚠️ No active flights found in database.")
    exit()

print(f"🛫 Found {len(flights)} active flights. Generating map...")

# Center map around first flight (fallback coordinates)
first_flight = flights[0]
center = [first_flight["current_position"]["lat"], first_flight["current_position"]["lon"]]
m = folium.Map(location=center, zoom_start=5, tiles="CartoDB positron")

# Generate distinct colors for each flight
def random_color():
    return "#{:06x}".format(random.randint(0, 0xFFFFFF))

for flight in flights:
    flight_id = flight["flight_id"]
    print(f"  ✈️ Plotting {flight_id} ...")
    path = get_flight_path(flight_id)
    if not path:
        print(f"    ⚠️ No path data for {flight_id}. Skipping.")
        continue

    color = random_color()
    coordinates = [(p["lat"], p["lon"]) for p in path]

    # Draw polyline for the flight path
    folium.PolyLine(
        coordinates,
        color=color,
        weight=3,
        opacity=0.8,
        tooltip=f"Flight {flight_id}"
    ).add_to(m)

    # Add start and end markers
    folium.Marker(
        location=[path[0]["lat"], path[0]["lon"]],
        popup=f"{flight_id} (Start)",
        icon=folium.Icon(color="green", icon="plane", prefix="fa")
    ).add_to(m)

    folium.Marker(
        location=[path[-1]["lat"], path[-1]["lon"]],
        popup=f"{flight_id} (End)",
        icon=folium.Icon(color="red", icon="flag", prefix="fa")
    ).add_to(m)

# ==========================
# SAVE OUTPUT
# ==========================
m.save(OUTPUT_FILE)
print(f"Map saved as: {OUTPUT_FILE}")
