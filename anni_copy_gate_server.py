#!/usr/bin/env python3
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from anni_copy_gate import evaluate

app = FastAPI(title="ANNI Copy Gate")

@app.post("/gate")
async def gate(req: Request):
    payload = await req.json()
    return JSONResponse(evaluate(payload))

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8093)
