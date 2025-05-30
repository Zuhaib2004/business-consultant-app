import os
import json
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import openai

# Configuration
openai.api_key = os.getenv("OPENAI_API_KEY", "").strip()
if not openai.api_key:
    raise RuntimeError("Set OPENAI_API_KEY in your environment")

# Load data
with open("business_data.json") as f:
    business_data = json.load(f)

# System prompt with instructions for chart/image output
system_prompt = (
    f"You are a business consultant. Here is the data for "
    f"{business_data['business_name']} during {business_data['period']}:\n"
    f"{json.dumps(business_data, indent=2)}\n\n"
    "When you want to show a chart, reply with:\n"
    "```chart {<valid Chart.js config JSON>} ```\n"
    "When you want to show an image, reply with:\n"
    "![alt text](<image-url>)"
)

sessions = {}
app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class ChatRequest(BaseModel):
    session_id: str
    message: str

class ChatResponse(BaseModel):
    session_id: str
    reply: str

@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    history = sessions.get(req.session_id) or [{"role":"system","content":system_prompt}]
    history.append({"role":"user","content":req.message})
    try:
        resp = openai.ChatCompletion.create(model="gpt-4o", messages=history)
    except Exception as e:
        raise HTTPException(500, detail=str(e))
    reply = resp.choices[0].message.content
    history.append({"role":"assistant","content":reply})
    sessions[req.session_id] = history
    return ChatResponse(session_id=req.session_id, reply=reply)

app.mount("/", StaticFiles(directory=".", html=True), name="static")
