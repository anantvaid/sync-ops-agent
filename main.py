import os, json
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from google.cloud import firestore
from dotenv import load_dotenv

load_dotenv("meeting_agent/.env")

app = FastAPI(title="Meeting Summarizer API")
db = firestore.Client()

class MeetingRequest(BaseModel):
    transcript: str

@app.get("/health")
def health():
    return {"status": "ok", "service": "meeting-summarizer"}

@app.get("/meetings")
def get_meetings(limit: int = 10):
    try:
        limit = min(limit, 50)
        docs = (
            db.collection("meetings")
            .order_by("created_at", direction="DESCENDING")
            .limit(limit)
            .stream()
        )
        meetings = []
        for doc in docs:
            data = doc.to_dict()
            data["id"] = doc.id
            meetings.append(data)
        return {"meetings": meetings, "count": len(meetings)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/meetings/{meeting_id}")
def get_meeting(meeting_id: str):
    try:
        doc = db.collection("meetings").document(meeting_id).get()
        if not doc.exists:
            raise HTTPException(status_code=404, detail="Meeting not found")
        data = doc.to_dict()
        data["id"] = doc.id
        return data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))