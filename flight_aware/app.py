from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from pymongo import MongoClient

# DATABASE CONNECTION
client = MongoClient("mongodb://localhost:27017/")
db = client["flightaware_lab"]
flights_col = db["flights"]
updates_col = db["flights_updates"]
logs_col = db["flight_logs"]


# FASTAPI APP
app = FastAPI(title="Flight Tracker API", version="1.0")


# SCHEMAS
class Position(BaseModel):
    lat: float
    lon: float
    altitude_ft: int
    heading: int
    speed_kts: Optional[int] = None

class FlightUpdate(BaseModel):
    flight_id: str
    timestamp: datetime
    lat: float
    lon: float
    altitude_ft: int
    heading: int
    speed_kts: Optional[int] = None


# ROUTES
@app.get("/")
def root():
    return {"message": "Flight Tracker API is running"}

#Ingest flight update
@app.post("/api/ingest")
def ingest_update(update: FlightUpdate):
    update_dict = update.dict()
    updates_col.insert_one(update_dict)

    flight = flights_col.find_one({"flight_id": update.flight_id})

    if flight:
        # Update current position of existing flight
        flights_col.update_one(
            {"flight_id": update.flight_id},
            {"$set": {
                "current_position": {
                    "lat": update.lat,
                    "lon": update.lon,
                    "altitude_ft": update.altitude_ft,
                    "heading": update.heading
                },
                "last_seen": update.timestamp,
                "last_update": datetime.utcnow().isoformat()
            }}
        )
    else:
        # Create new flight entry
        flights_col.insert_one({
            "flight_id": update.flight_id,
            "status": "enroute",
            "first_seen": update.timestamp,
            "last_seen": update.timestamp,
            "current_position": {
                "lat": update.lat,
                "lon": update.lon,
                "altitude_ft": update.altitude_ft,
                "heading": update.heading
            },
            "last_update": datetime.utcnow().isoformat()
        })

    return {"message": f"Update for flight {update.flight_id} stored successfully"}

#Get all active flights
@app.get("/api/active")
def get_active_flights():
    flights = list(flights_col.find({}, {"_id": 0}))
    return {"active_flights": flights}

#Track live flight path (updates)
@app.get("/api/track/{flight_id}")
def track_flight(flight_id: str):
    updates = list(updates_col.find({"flight_id": flight_id}, {"_id": 0}).sort("timestamp", 1))
    if not updates:
        raise HTTPException(status_code=404, detail="No updates found for this flight")
    return {"flight_id": flight_id, "path": updates}

#Mark flight complete and move to logs
@app.post("/api/complete/{flight_id}")
def complete_flight(flight_id: str):
    updates = list(updates_col.find({"flight_id": flight_id}, {"_id": 0}).sort("timestamp", 1))
    flight = flights_col.find_one({"flight_id": flight_id}, {"_id": 0})

    if not flight:
        raise HTTPException(status_code=404, detail="Flight not found")

    if not updates:
        raise HTTPException(status_code=404, detail="No tracking data available for this flight")

    # Calculate duration (in minutes)
    duration_min = int((updates[-1]["timestamp"] - updates[0]["timestamp"]).total_seconds() / 60)

    # Build log document
    flight_log = {
        **flight,
        "path": updates,
        "duration_min": duration_min,
        "status": "completed"
    }

    # Move to logs
    logs_col.insert_one(flight_log)
    flights_col.delete_one({"flight_id": flight_id})
    updates_col.delete_many({"flight_id": flight_id})

    return {"message": f"Flight {flight_id} archived successfully", "duration_min": duration_min}
