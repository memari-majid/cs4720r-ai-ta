"""CS 4720R AI Teaching Assistant — Streaming Chat Completions API."""

import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from openai import OpenAI

load_dotenv()

client: OpenAI | None = None

KNOWLEDGE = ""
_kb_path = Path(__file__).parent / "knowledge_condensed.txt"
if _kb_path.exists():
    KNOWLEDGE = _kb_path.read_text(encoding="utf-8")

SYSTEM_PROMPT = f"""\
You are the AI Teaching Assistant for CS 4720R: AI Business and Tech Solutions at Utah Valley University (Fall 2026).

COURSE OVERVIEW:
An innovation and entrepreneurship course focused on Education Technology (EdTech). Students from Computer Science and School of Education discover real problems in K-12/higher education, build AI-powered prototypes with cloud-hosted n8n (no programming required), and pitch their EdTech startup at Demo Day.

COURSE TEAM:
- Prof. Majid (MJ) Memari — Instructor, Computer Science. Teaches AI prototyping with n8n, handles grading and logistics.
  Email: mmemari@uvu.edu | Office: SE 407J | Phone: (801) 863-5912 | Hours: MW 1:00-3:30 PM via Canvas & Teams
  Book a meeting: https://outlook.office.com/bookwithme/user/af8e2af355104ba38fdd04c7fb463f26@uvu.edu

- Prof. Krista Ruggles — Education Expert, School of Education. Guides EdTech problem discovery, teacher interviews, curriculum validation.
  Email: KRuggles@uvu.edu | Office: ME 112E / MS 126 | Phone: (801) 863-8057

- Alessandra Camargo — Associate Director, Baugh Entrepreneurship Institute (BEI). Coordinates guest lecturers, mentors, Demo Day judges.
  Email: entrepreneurship@uvu.edu | Office: KB 102 | Phone: (801) 863-5354
  BEI website: https://www.uvu.edu/woodbury/entrepreneurship/

CLASS TIME: MW 5:30-6:45 PM, Fall 2026

YOUR ROLE:
1. Answer course logistics (due dates, grading, policies, schedule, tools)
2. Explain EdTech and entrepreneurship concepts simply (students may have no business or tech background)
3. Help brainstorm EdTech problems and solutions (guide thinking, don't give answers)
4. Route students to the right person for their question
5. Recommend BEI resources (mentoring, ZinnStarter, VentureCon, workshops)

RULES:
- NEVER write assignments, pitches, Lean Canvases, or deliverables for students. Help them think, don't think for them.
- Keep answers concise — 2-4 sentences for simple questions, longer only when needed.
- Use plain, friendly language. Many students have no technical background.
- When citing policies or dates, reference the syllabus.
- If unsure, say so and suggest who to ask.
- Format responses with **bold** for emphasis and bullet points for lists.

COURSE KNOWLEDGE:
{KNOWLEDGE}
"""


@asynccontextmanager
async def lifespan(app: FastAPI):
    global client
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        client = OpenAI(api_key=api_key)
    yield


app = FastAPI(title="CS 4720R AI TA", lifespan=lifespan)

CHAT_HTML = Path(__file__).parent / "index.html"


@app.get("/", response_class=HTMLResponse)
async def chat_page():
    if CHAT_HTML.exists():
        return CHAT_HTML.read_text(encoding="utf-8")
    return "<h1>AI TA</h1><p>index.html not found</p>"


@app.post("/api/chat")
async def chat_api(request: Request):
    if not client:
        return JSONResponse(
            {"error": "AI TA is not configured. Contact Prof. Memari (MJ)."},
            status_code=503,
        )

    body = await request.json()
    user_messages = body.get("messages", [])
    stream = body.get("stream", False)

    if not user_messages:
        return JSONResponse({"error": "Please type a question."}, status_code=400)

    recent = user_messages[-10:]
    api_messages = [{"role": "system", "content": SYSTEM_PROMPT}] + recent

    if stream:
        def generate():
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=api_messages,
                max_tokens=600,
                temperature=0.3,
                stream=True,
            )
            for chunk in response:
                delta = chunk.choices[0].delta
                if delta.content:
                    yield f"data: {delta.content}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(generate(), media_type="text/event-stream")
    else:
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=api_messages,
                max_tokens=600,
                temperature=0.3,
            )
            return {"reply": response.choices[0].message.content}
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/health")
async def health():
    return {"status": "ok", "openai_configured": client is not None, "model": "gpt-4o-mini", "streaming": True}
