import os
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
import psycopg

BASE = Path(__file__).resolve().parent
DATABASE_URL = os.getenv("DATABASE_URL")
app = FastAPI(title="Nafas Kitchen Minute")

def get_conn():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not configured.")
    return psycopg.connect(DATABASE_URL.replace("postgres://", "postgresql://", 1))

def init_db():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS scores (
                    id BIGINT PRIMARY KEY,
                    name VARCHAR(22) NOT NULL,
                    score INTEGER NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
            """)

try:
    init_db()
except Exception:
    pass

class Score(BaseModel):
    id: int
    name: str
    score: int

def get_scores():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, name, score FROM scores
                ORDER BY score DESC, created_at ASC
            """)
            return [{"id": r[0], "name": r[1], "score": r[2]} for r in cur.fetchall()]

@app.get("/")
def home():
    return FileResponse(BASE / "index.html")

@app.get("/health")
def health():
    return {"ok": True}

@app.get("/api/scores")
def scores():
    init_db()
    return get_scores()

@app.post("/api/scores")
def add_score(s: Score):
    init_db()
    name = s.name.strip()[:22]
    if not name:
        raise HTTPException(status_code=400, detail="Name is required")
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO scores (id, name, score)
                VALUES (%s, %s, %s)
                ON CONFLICT (id)
                DO UPDATE SET name=EXCLUDED.name, score=EXCLUDED.score
            """, (s.id, name, s.score))
    return get_scores()

@app.delete("/api/scores")
def clear_scores():
    init_db()
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM scores")
    return {"ok": True}
