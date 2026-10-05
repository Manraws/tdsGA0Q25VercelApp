from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import json
import math
import os

app = FastAPI()

# Allow POST requests from any origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["POST", "OPTIONS"],
    allow_headers=["*"],
)

# Load the telemetry data.
# Put q-vercel-latency.json in the project root.
DATA_FILE = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "q-vercel-latency.json"
)

with open(DATA_FILE, "r") as f:
    telemetry = json.load(f)


class RequestBody(BaseModel):
    regions: list[str]
    threshold_ms: float


def percentile(values, percentile):
    """Calculate percentile using linear interpolation."""
    values = sorted(values)

    if len(values) == 1:
        return values[0]

    position = (len(values) - 1) * percentile
    lower = math.floor(position)
    upper = math.ceil(position)

    if lower == upper:
        return values[lower]

    return (
        values[lower]
        + (values[upper] - values[lower]) * (position - lower)
    )


@app.get("/")
def root():
    return {"message": "eShopCo latency API is running"}


@app.post("/")
def calculate_metrics(request: RequestBody):
    results = {}

    for region in request.regions:
        records = [
            record
            for record in telemetry
            if record["region"] == region
        ]

        if not records:
            continue

        latencies = [
            record["latency_ms"]
            for record in records
        ]

        uptimes = [
            record["uptime_pct"]
            for record in records
        ]

        results[region] = {
            "avg_latency": sum(latencies) / len(latencies),
            "p95_latency": percentile(latencies, 0.95),
            "avg_uptime": sum(uptimes) / len(uptimes),
            "breaches": sum(
                1
                for latency in latencies
                if latency > request.threshold_ms
            ),
        }

    return results
