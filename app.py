"""CS 4720R AI Teaching Assistant — FastAPI server with embedded chat UI."""

import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from openai import OpenAI

load_dotenv()

client: OpenAI | None = None
ASSISTANT_ID: str = ""


@asynccontextmanager
async def lifespan(app: FastAPI):
    global client, ASSISTANT_ID
    api_key = os.getenv("OPENAI_API_KEY")
    ASSISTANT_ID = os.getenv("ASSISTANT_ID", "")
    if api_key:
        client = OpenAI(api_key=api_key)
    yield


app = FastAPI(title="CS 4720R AI TA", lifespan=lifespan)

UVU_GREEN = "#275d38"

CHAT_HTML = f"""\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AI Teaching Assistant — CS 4720R</title>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f0f2f5; height: 100vh; display: flex; flex-direction: column; }}
  .header {{ background: {UVU_GREEN}; color: #fff; padding: 16px 24px; display: flex; align-items: center; gap: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.15); }}
  .header i {{ font-size: 24px; }}
  .header h1 {{ font-size: 18px; font-weight: 600; }}
  .header .subtitle {{ font-size: 12px; opacity: 0.85; margin-top: 2px; }}
  .chat-container {{ flex: 1; overflow-y: auto; padding: 20px; display: flex; flex-direction: column; gap: 12px; }}
  .message {{ max-width: 85%; padding: 12px 16px; border-radius: 16px; font-size: 15px; line-height: 1.6; word-wrap: break-word; animation: fadeIn 0.3s; }}
  @keyframes fadeIn {{ from {{ opacity: 0; transform: translateY(8px); }} to {{ opacity: 1; transform: translateY(0); }} }}
  .assistant {{ background: #fff; color: #333; align-self: flex-start; border: 1px solid #e0e0e0; border-bottom-left-radius: 4px; }}
  .user {{ background: {UVU_GREEN}; color: #fff; align-self: flex-end; border-bottom-right-radius: 4px; }}
  .assistant strong {{ color: {UVU_GREEN}; }}
  .assistant a {{ color: {UVU_GREEN}; }}
  .assistant code {{ background: #f0f0f0; padding: 2px 6px; border-radius: 4px; font-size: 13px; }}
  .typing {{ align-self: flex-start; background: #fff; border: 1px solid #e0e0e0; padding: 12px 20px; border-radius: 16px; border-bottom-left-radius: 4px; }}
  .typing span {{ display: inline-block; width: 8px; height: 8px; background: #999; border-radius: 50%; animation: bounce 1.4s infinite ease-in-out; margin: 0 2px; }}
  .typing span:nth-child(2) {{ animation-delay: 0.2s; }}
  .typing span:nth-child(3) {{ animation-delay: 0.4s; }}
  @keyframes bounce {{ 0%, 80%, 100% {{ transform: scale(0); }} 40% {{ transform: scale(1); }} }}
  .input-area {{ background: #fff; padding: 16px 20px; border-top: 1px solid #e0e0e0; display: flex; gap: 10px; }}
  .input-area input {{ flex: 1; padding: 12px 16px; border: 2px solid #e0e0e0; border-radius: 24px; font-size: 15px; outline: none; transition: border-color 0.2s; }}
  .input-area input:focus {{ border-color: {UVU_GREEN}; }}
  .input-area button {{ background: {UVU_GREEN}; color: #fff; border: none; border-radius: 50%; width: 44px; height: 44px; cursor: pointer; font-size: 18px; transition: background 0.2s; display: flex; align-items: center; justify-content: center; }}
  .input-area button:hover {{ background: #1a3d24; }}
  .input-area button:disabled {{ background: #999; cursor: not-allowed; }}
  .welcome {{ text-align: center; padding: 40px 20px; color: #666; }}
  .welcome h2 {{ color: {UVU_GREEN}; margin-bottom: 8px; }}
  .welcome .chips {{ display: flex; flex-wrap: wrap; gap: 8px; justify-content: center; margin-top: 20px; }}
  .welcome .chip {{ background: #e8f5e9; color: {UVU_GREEN}; border: 1px solid {UVU_GREEN}; padding: 8px 16px; border-radius: 20px; cursor: pointer; font-size: 13px; transition: background 0.2s; }}
  .welcome .chip:hover {{ background: {UVU_GREEN}; color: #fff; }}
  .footer {{ text-align: center; padding: 8px; font-size: 11px; color: #999; background: #f0f2f5; }}
</style>
</head>
<body>
<div class="header">
  <i class="fas fa-robot"></i>
  <div>
    <h1>AI Teaching Assistant</h1>
    <div class="subtitle">CS 4720R: AI Business &amp; Tech Solutions — Fall 2026</div>
  </div>
</div>

<div class="chat-container" id="chat">
  <div class="welcome" id="welcome">
    <h2><i class="fas fa-graduation-cap"></i> Hi! I'm your AI TA.</h2>
    <p>I can help with course questions, due dates, policies, EdTech ideas, and more.<br>I won't do your assignments — but I'll help you think through them.</p>
    <div class="chips">
      <div class="chip" onclick="askQ(this)">When is Demo Day?</div>
      <div class="chip" onclick="askQ(this)">How is my grade calculated?</div>
      <div class="chip" onclick="askQ(this)">What is ZinnStarter?</div>
      <div class="chip" onclick="askQ(this)">Who should I contact for help with teacher interviews?</div>
      <div class="chip" onclick="askQ(this)">What is a Lean Canvas?</div>
      <div class="chip" onclick="askQ(this)">Help me brainstorm EdTech problems</div>
    </div>
  </div>
</div>

<div class="input-area">
  <input type="text" id="input" placeholder="Ask me anything about CS 4720R..." autocomplete="off" onkeydown="if(event.key==='Enter')send()">
  <button id="btn" onclick="send()"><i class="fas fa-paper-plane"></i></button>
</div>

<div class="footer">
  Powered by OpenAI &middot; Utah Valley University &middot; Not a substitute for your instructors
</div>

<script>
let threadId = null;
const chat = document.getElementById('chat');
const input = document.getElementById('input');
const btn = document.getElementById('btn');

function askQ(el) {{ input.value = el.textContent; send(); }}

function addMsg(role, text) {{
  const w = document.getElementById('welcome');
  if (w) w.remove();
  const d = document.createElement('div');
  d.className = 'message ' + role;
  d.innerHTML = text.replace(/\\n/g, '<br>');
  chat.appendChild(d);
  chat.scrollTop = chat.scrollHeight;
}}

function showTyping() {{
  const d = document.createElement('div');
  d.className = 'typing';
  d.id = 'typing';
  d.innerHTML = '<span></span><span></span><span></span>';
  chat.appendChild(d);
  chat.scrollTop = chat.scrollHeight;
}}

function hideTyping() {{
  const t = document.getElementById('typing');
  if (t) t.remove();
}}

async function send() {{
  const q = input.value.trim();
  if (!q) return;
  input.value = '';
  btn.disabled = true;
  addMsg('user', q);
  showTyping();

  try {{
    const res = await fetch('/api/chat', {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{ message: q, thread_id: threadId }})
    }});
    const data = await res.json();
    hideTyping();
    if (data.error) {{
      addMsg('assistant', '⚠️ ' + data.error);
    }} else {{
      threadId = data.thread_id;
      addMsg('assistant', data.reply);
    }}
  }} catch(e) {{
    hideTyping();
    addMsg('assistant', '⚠️ Connection error. Please try again.');
  }}
  btn.disabled = false;
  input.focus();
}}
</script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
async def chat_page():
    return CHAT_HTML


@app.post("/api/chat")
async def chat_api(request: Request):
    if not client or not ASSISTANT_ID:
        return JSONResponse(
            {"error": "AI TA is not configured yet. Please contact Prof. Memari (MJ)."},
            status_code=503,
        )

    body = await request.json()
    user_msg = body.get("message", "").strip()
    thread_id = body.get("thread_id")

    if not user_msg:
        return JSONResponse({"error": "Please type a question."}, status_code=400)

    try:
        if thread_id:
            thread = client.beta.threads.retrieve(thread_id)
        else:
            thread = client.beta.threads.create()

        client.beta.threads.messages.create(
            thread_id=thread.id, role="user", content=user_msg
        )

        run = client.beta.threads.runs.create_and_poll(
            thread_id=thread.id, assistant_id=ASSISTANT_ID
        )

        if run.status == "completed":
            messages = client.beta.threads.messages.list(
                thread_id=thread.id, order="desc", limit=1
            )
            reply = messages.data[0].content[0].text.value

            import re
            reply = re.sub(r"【[^】]*】", "", reply)

            return {"reply": reply, "thread_id": thread.id}

        return JSONResponse(
            {"error": f"AI TA encountered an issue (status: {run.status}). Please try again."},
            status_code=500,
        )

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "assistant_configured": bool(ASSISTANT_ID),
        "openai_configured": client is not None,
    }
