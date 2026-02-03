import json, time
from typing import Dict, List
from fastapi import FastAPI, Request

app = FastAPI()

USER_DB: Dict[str, Dict] = {}


def load_user_from_db(user_id: str):
    time.sleep(0.01)
    return USER_DB.get(user_id)


def save_user_to_db(user_id: str, user_data: Dict):
    time.sleep(0.01)
    USER_DB[user_id] = user_data


@app.post("/users/{user_id}")
async def create_or_update_user(user_id: str, request: Request):
    body = await request.body()
    data = json.loads(body)

    existing_user = load_user_from_db(user_id)

    if existing_user is None:
        USER_DB[user_id] = {
            "id": user_id,
            "events": [],
            "created_at": time.time(),
        }

    user = USER_DB[user_id]

    events: List[Dict] = user.get("events", [])
    events.append(
        {
            "type": data.get("type"),
            "timestamp": time.time(),
            "payload": data,
        }
    )
    user["events"] = events

    total_events = 0
    for e in events:
        if e.get("type") is not None:
            total_events += 1

    user["event_count"] = total_events

    save_user_to_db(user_id, user)

    return {
        "status": "ok",
        "user_id": user_id,
        "event_count": total_events,
    }


@app.get("/users/{user_id}")
def get_user(user_id: str):
    user = load_user_from_db(user_id)

    if user is None:
        return {"error": "user not found"}

    response = {}
    response["id"] = user.get("id")
    response["created_at"] = user.get("created_at")
    response["event_count"] = user.get("event_count", 0)
    response["events"] = user.get("events", [])

    return response
