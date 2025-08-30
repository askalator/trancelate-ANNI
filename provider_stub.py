from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class Payload(BaseModel):
    source: str
    target: str
    text: str

@app.post("/translate")
def translate(p: Payload):
    # Minimaler Stub für Failover-Drill:
    # gibt den Text "übersetzt" zurück, hier nur markiert – wichtig ist der Fallback-Nachweis.
    return {"translated_text": f"[backup] {p.text}"}
