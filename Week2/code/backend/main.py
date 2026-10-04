from fastapi import FastAPI
from pydantic import BaseModel
import asyncpg
import os
from llm_service import analyze_symptoms

app = FastAPI()
DB_URL = os.getenv("DATABASE_URL")  # postgresql://user:pass@rds-endpoint:5432/mediassist

class SymptomRequest(BaseModel):
    symptoms: str

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/api/v1/analyze")
async def analyze(req: SymptomRequest):
    risk_result = await analyze_symptoms(req.symptoms)

    conn = await asyncpg.connect(DB_URL)
    doctor = await conn.fetchrow(
        """SELECT d.name, s.name as specialty, h.name as hospital
           FROM doctors d
           JOIN specialties s ON d.specialty_id = s.id
           JOIN hospitals h ON d.hospital_id = h.id
           WHERE s.name = $1 LIMIT 1""",
        risk_result["suggested_specialty"]
    )
    await conn.close()

    return {
        "risk_assessment": risk_result["risks"],
        "triage": risk_result["triage"],
        "suggested_doctor": dict(doctor) if doctor else None
    }