"""CS 4720R AI Teaching Assistant — Streaming + Auto-Sync from Canvas."""

import asyncio
import os
import re
import threading
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

import requests as http_requests
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from openai import OpenAI

load_dotenv()

client: OpenAI | None = None

CANVAS_URL = "https://uvu.instructure.com"
COURSE_ID = "644965"
SYNC_INTERVAL_HOURS = int(os.getenv("SYNC_INTERVAL_HOURS", "12"))

knowledge_text = ""
last_sync = "never"
system_prompt = ""


def strip_html(html: str) -> str:
    text = re.sub(r"<[^>]+>", " ", html).strip()
    return re.sub(r"\s+", " ", text)


def sync_from_canvas() -> str:
    """Pull fresh content from Canvas and return condensed knowledge text."""
    token = os.getenv("CANVAS_API_TOKEN")
    if not token:
        return ""

    base = f"{CANVAS_URL}/api/v1"
    headers = {"Authorization": f"Bearer {token}"}
    content = []

    try:
        r = http_requests.get(f"{base}/courses/{COURSE_ID}", headers=headers,
                              params={"include[]": "syllabus_body"}, timeout=30)
        syl = strip_html(r.json().get("syllabus_body", ""))
        content.append(f"SYLLABUS:\n{syl[:5000]}")

        r = http_requests.get(f"{base}/courses/{COURSE_ID}/assignments?per_page=100",
                              headers=headers, timeout=30)
        content.append("\nASSIGNMENTS:")
        for a in sorted(r.json(), key=lambda x: x.get("due_at") or ""):
            desc = strip_html(a.get("description", "") or "")[:400]
            content.append(f"\n{a['name']} | {a.get('points_possible',0)} pts | due: {(a.get('due_at') or 'TBD')[:10]}\n{desc}")

        r = http_requests.get(f"{base}/courses/{COURSE_ID}/modules?per_page=50",
                              headers=headers, timeout=30)
        modules = r.json()
        content.append("\nMODULES:")
        for m in modules:
            r2 = http_requests.get(f"{base}/courses/{COURSE_ID}/modules/{m['id']}/items?per_page=20",
                                   headers=headers, timeout=30)
            items = r2.json() if isinstance(r2.json(), list) else []
            item_list = ", ".join(it.get("title", "")[:50] for it in items[:5])
            content.append(f"- {m['name']}: {item_list}")

        r = http_requests.get(f"{base}/courses/{COURSE_ID}/discussion_topics?per_page=50",
                              headers=headers, timeout=30)
        discussions = r.json() if isinstance(r.json(), list) else []
        content.append("\nDISCUSSIONS:")
        for d in sorted(discussions, key=lambda x: x.get("title", "")):
            msg = strip_html(d.get("message", "") or "")[:200]
            content.append(f"- {d['title']}: {msg}")

        # Pull ALL published pages (full content)
        r = http_requests.get(f"{base}/courses/{COURSE_ID}/pages?per_page=100",
                              headers=headers, timeout=30)
        all_pages = r.json() if isinstance(r.json(), list) else []
        all_links = set()
        content.append("\nALL COURSE PAGES:")
        for pg in all_pages:
            if not pg.get("published"):
                continue
            r2 = http_requests.get(f"{base}/courses/{COURSE_ID}/pages/{pg['url']}",
                                   headers=headers, timeout=30)
            if r2.status_code != 200:
                continue
            body_html = r2.json().get("body", "") or ""
            # Extract external links from page HTML
            import re as _re
            for href in _re.findall(r'href="(https?://[^"]+)"', body_html):
                if "instructure.com" not in href and "uvu.edu" in href:
                    all_links.add(href)
                elif "uvu.edu/woodbury" in href:
                    all_links.add(href)
            text = strip_html(body_html)[:1500]
            content.append(f"\nPAGE: {pg['title']}\n{text}")
        print(f"  Pages: {len(all_pages)}, External links found: {len(all_links)}")

        # Crawl external links for additional content
        if all_links:
            content.append("\nLINKED RESOURCES (crawled from course pages):")
            for link in sorted(all_links):
                try:
                    r3 = http_requests.get(link, timeout=10,
                                           headers={"User-Agent": "UVU-CS4720R-AI-TA/1.0"})
                    if r3.status_code == 200:
                        page_text = strip_html(r3.text)[:2000]
                        content.append(f"\nLINK: {link}\n{page_text}")
                except Exception:
                    pass
            print(f"  Crawled {len(all_links)} external links")

        r = http_requests.get(f"{base}/courses/{COURSE_ID}/discussion_topics?only_announcements=true&per_page=5",
                              headers=headers, timeout=30)
        announcements = r.json() if isinstance(r.json(), list) else []
        if announcements:
            content.append("\nRECENT ANNOUNCEMENTS:")
            for a in announcements:
                msg = strip_html(a.get("message", "") or "")[:300]
                posted = (a.get("posted_at") or "")[:10]
                content.append(f"- [{posted}] {a['title']}: {msg}")

        r = http_requests.get(f"{base}/courses/{COURSE_ID}/assignment_groups?per_page=50",
                              headers=headers, timeout=30)
        groups = r.json() if isinstance(r.json(), list) else []
        content.append("\nGRADING WEIGHTS:")
        for g in sorted(groups, key=lambda x: -x.get("group_weight", 0)):
            content.append(f"- {g['name']}: {g.get('group_weight', 0)}%")

    except Exception as e:
        content.append(f"\n[Sync error: {e}]")

    content.append("""
KEY POLICIES:
- Late work: Up to 3 days late with 10% penalty per day. After 3 days, no credit without prior arrangement.
- AI use: Encouraged. Must understand all work and disclose AI use.
- No programming required. Cloud-hosted n8n (browser-based).
- Class time: MW 5:30 PM - 6:45 PM, Fall 2026.
- BEI mentoring: Free at https://www.uvu.edu/woodbury/entrepreneurship/mentoring.php
- ZinnStarter: Pitch competition with equity-free seed funding.
- VentureCon: Student business trade show.
""")

    return "\n".join(content)


def build_system_prompt(knowledge: str) -> str:
    return f"""\
You are the AI Teaching Assistant for CS 4720R: AI Business and Tech Solutions at Utah Valley University (Fall 2026).

COURSE OVERVIEW:
An innovation and entrepreneurship course focused on Education Technology (EdTech). Students from Computer Science and School of Education discover real problems in K-12/higher education, build AI-powered prototypes with cloud-hosted n8n (no programming required), and pitch their EdTech startup at Demo Day.

COURSE TEAM:
- Dr. Majid (MJ) Memari — Instructor, Computer Science. Teaches AI prototyping with n8n, handles grading and logistics.
  Email: mmemari@uvu.edu | Office: SE 407J | Phone: (801) 863-5912 | Hours: MW 1:00-3:30 PM via Canvas & Teams
  Book a meeting: https://outlook.office.com/bookwithme/user/af8e2af355104ba38fdd04c7fb463f26@uvu.edu

- Dr. Krista Ruggles — Education Expert, School of Education. Guides EdTech problem discovery, teacher interviews, curriculum validation.
  Email: KRuggles@uvu.edu | Office: ME 112E / MS 126 | Phone: (801) 863-8057

- Alessandra Camargo — Associate Director, Baugh Entrepreneurship Institute (BEI). Coordinates guest lecturers, mentors, Demo Day judges.
  Email: entrepreneurship@uvu.edu | Office: KB 102 | Phone: (801) 863-5354
  BEI website: https://www.uvu.edu/woodbury/entrepreneurship/

CLASS TIME: MW 5:30-6:45 PM, Fall 2026

IMPORTANT COURSE LINKS (use ONLY these — never guess or invent URLs):
- Course home: https://uvu.instructure.com/courses/644965
- Syllabus: https://uvu.instructure.com/courses/644965/assignments/syllabus
- Modules: https://uvu.instructure.com/courses/644965/modules
- Assignments: https://uvu.instructure.com/courses/644965/assignments
- Discussions: https://uvu.instructure.com/courses/644965/discussion_topics
- Schedule: https://uvu.instructure.com/courses/644965/pages/course-schedule
- Instructor info: https://uvu.instructure.com/courses/644965/pages/instructor-information
- FAQ: https://uvu.instructure.com/courses/644965/pages/faq
- Tech requirements: https://uvu.instructure.com/courses/644965/pages/technical-requirements
- BEI mentoring: https://www.uvu.edu/woodbury/entrepreneurship/mentoring.php
- BEI website: https://www.uvu.edu/woodbury/entrepreneurship/
- Book meeting with Dr. Memari: https://outlook.office.com/bookwithme/user/af8e2af355104ba38fdd04c7fb463f26@uvu.edu

YOUR ROLE:
1. Answer course logistics (due dates, grading, policies, schedule, tools)
2. Explain EdTech and entrepreneurship concepts simply
3. Help brainstorm EdTech problems and solutions (guide thinking, don't give answers)
4. Route students to the right person for their question
5. Recommend BEI resources (mentoring, ZinnStarter, VentureCon, workshops)

RULES:
- ALWAYS include the matching link from IMPORTANT COURSE LINKS when your answer relates to one of those pages. For example, if a student asks about the syllabus, include the syllabus link. If they ask about grading, link to the syllabus. If they ask about the schedule, link to the schedule page.
- NEVER fabricate, guess, or invent URLs. Only use links from the IMPORTANT COURSE LINKS list above or from the COURSE KNOWLEDGE section below. If no matching link exists, say "check Canvas" instead of making one up.
- NEVER write assignments, pitches, Lean Canvases, or deliverables for students.
- Keep answers concise — 2-4 sentences for simple questions, longer for complex ones.
- Use plain, friendly language. Format with **bold**, bullet points, and tables when helpful.
- If unsure, say so and suggest who to ask.

FOLLOW-UP SUGGESTIONS:
After EVERY response, add exactly 3 follow-up question suggestions on the last line, formatted as:
[SUGGESTIONS]question one?|question two?|question three?[/SUGGESTIONS]
The suggestions should be natural next questions a student might ask based on:
1. What they just asked about (dig deeper)
2. A related course topic or resource
3. A practical next step they could take
Keep each suggestion under 8 words. Do NOT explain the suggestions — just append them silently.

COURSE KNOWLEDGE (auto-synced from Canvas):
{knowledge}
"""


def do_sync():
    """Run a sync and update the in-memory prompt."""
    global knowledge_text, system_prompt, last_sync
    print(f"[{datetime.now(timezone.utc).isoformat()}] Syncing from Canvas...")
    new_knowledge = sync_from_canvas()
    if new_knowledge:
        knowledge_text = new_knowledge
        system_prompt = build_system_prompt(knowledge_text)
        last_sync = datetime.now(timezone.utc).isoformat()
        print(f"  Synced: {len(knowledge_text)} chars, {len(knowledge_text.split())} words")
    else:
        print("  No Canvas token — using static knowledge base")


def sync_loop():
    """Background thread that syncs every SYNC_INTERVAL_HOURS."""
    while True:
        time.sleep(SYNC_INTERVAL_HOURS * 3600)
        try:
            do_sync()
        except Exception as e:
            print(f"  Sync error: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    global client, knowledge_text, system_prompt

    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        client = OpenAI(api_key=api_key)

    # Initial sync from Canvas (or fall back to static file)
    if os.getenv("CANVAS_API_TOKEN"):
        do_sync()
    else:
        kb_path = Path(__file__).parent / "knowledge_condensed.txt"
        if kb_path.exists():
            knowledge_text = kb_path.read_text(encoding="utf-8")
        system_prompt = build_system_prompt(knowledge_text)

    # Start background sync thread
    if os.getenv("CANVAS_API_TOKEN"):
        t = threading.Thread(target=sync_loop, daemon=True)
        t.start()
        print(f"Background sync: every {SYNC_INTERVAL_HOURS} hours")

    yield


app = FastAPI(title="CS 4720R AI TA", lifespan=lifespan)


@app.get("/", response_class=HTMLResponse)
async def chat_page():
    html_path = Path(__file__).parent / "index.html"
    if html_path.exists():
        return html_path.read_text(encoding="utf-8")
    return "<h1>AI TA</h1><p>index.html not found</p>"


@app.post("/api/chat")
async def chat_api(request: Request):
    if not client:
        return JSONResponse(
            {"error": "AI TA is not configured. Contact Dr. Memari (MJ)."},
            status_code=503,
        )

    body = await request.json()
    user_messages = body.get("messages", [])
    stream = body.get("stream", False)
    mode = body.get("mode", "fast")  # "fast" or "thinking"

    if not user_messages:
        return JSONResponse({"error": "Please type a question."}, status_code=400)

    recent = user_messages[-10:]
    api_messages = [{"role": "system", "content": system_prompt}] + recent

    if mode == "thinking":
        model = "gpt-4.1"
        max_tokens = 1600
        temperature = 0.4
    else:
        model = "gpt-4o-mini"
        max_tokens = 800
        temperature = 0.3

    if stream:
        def generate():
            import json as _json
            response = client.chat.completions.create(
                model=model,
                messages=api_messages,
                max_tokens=max_tokens,
                temperature=temperature,
                stream=True,
            )
            for chunk in response:
                delta = chunk.choices[0].delta
                if delta.content:
                    yield f"data: {_json.dumps(delta.content)}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(generate(), media_type="text/event-stream")
    else:
        try:
            response = client.chat.completions.create(
                model=model,
                messages=api_messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            return {"reply": response.choices[0].message.content}
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/api/sync")
async def manual_sync():
    """Trigger a manual sync (for instructors)."""
    do_sync()
    return {"status": "synced", "last_sync": last_sync, "knowledge_size": len(knowledge_text)}


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "openai_configured": client is not None,
        "canvas_sync": bool(os.getenv("CANVAS_API_TOKEN")),
        "last_sync": last_sync,
        "knowledge_words": len(knowledge_text.split()),
        "sync_interval_hours": SYNC_INTERVAL_HOURS,
        "model": "gpt-4o-mini",
    }
