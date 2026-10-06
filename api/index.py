from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import json
import math
import os

app = FastAPI()

# CORS: allow every origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["POST", "OPTIONS"],
    allow_headers=["*"],
)


DATA_FILE = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "q-vercel-latency.json"
)

with open(DATA_FILE, "r") as f:
    telemetry = json.load(f)


class RequestBody(BaseModel):
    regions: list[str]
    threshold_ms: float


def percentile(values, p):
    values = sorted(values)

    if len(values) == 1:
        return values[0]

    position = (len(values) - 1) * p
    lower = math.floor(position)
    upper = math.ceil(position)

    if lower == upper:
        return values[lower]

    return (
        values[lower]
        + (values[upper] - values[lower])
        * (position - lower)
    )


@app.get("/")
def root():
    return {"status": "ok"}


@app.post("/api/latency")
def latency(request: RequestBody):
    result = {}

    for region in request.regions:
        records = [
            r for r in telemetry
            if r["region"] == region
        ]

        if not records:
            continue

        latencies = [
            r["latency_ms"]
            for r in records
        ]

        uptimes = [
            r["uptime_pct"]
            for r in records
        ]

        result[region] = {
            "avg_latency": sum(latencies) / len(latencies),
            "p95_latency": percentile(latencies, 0.95),
            "avg_uptime": sum(uptimes) / len(uptimes),
            "breaches": sum(
                1
                for latency in latencies
                if latency > request.threshold_ms
            )
        }

    return result
