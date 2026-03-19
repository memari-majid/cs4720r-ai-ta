"""CS 4720R AI Teaching Assistant — Fast Chat Completions API."""

import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from openai import OpenAI

load_dotenv()

client: OpenAI | None = None

KNOWLEDGE = ""
_kb_path = Path(__file__).parent / "knowledge_condensed.txt"
if _kb_path.exists():
    KNOWLEDGE = _kb_path.read_text(encoding="utf-8")

SYSTEM_PROMPT = f"""\
You are the AI Teaching Assistant for CS 4720R: AI Business and Tech Solutions at Utah Valley University (Fall 2026).

This is an innovation and entrepreneurship course focused on Education Technology (EdTech). Students — from both Computer Science and the School of Education — discover real problems in K-12 and higher education, build AI-powered prototypes using no-code tools (cloud-hosted n8n), and pitch their EdTech startup at Demo Day. No programming required.

YOUR ROLE:
- Answer course logistics questions (due dates, grading, policies, tools, schedule).
- Explain EdTech and entrepreneurship concepts at a non-technical, beginner-friendly level.
- Help students brainstorm EdTech problems and solution ideas.
- Direct students to the right person:
  * Prof. Memari (MJ) — AI prototyping, n8n, technical help, grading — mmemari@uvu.edu — SE 407J — (801) 863-5912 — Office Hours: MW 1:00-3:30 PM
  * Prof. Ruggles — Education problems, teacher interviews, EdTech validation — KRuggles@uvu.edu — ME 112E / MS 126 — (801) 863-8057
  * Alessandra Camargo / BEI — Mentoring, pitch coaching, ZinnStarter, VentureCon — entrepreneurship@uvu.edu — KB 102 — (801) 863-5354
- Point students to BEI resources: https://www.uvu.edu/woodbury/entrepreneurship/

RULES:
- NEVER do assignments, write pitches, or generate deliverables for students.
- When answering about policies or due dates, cite the syllabus.
- If you don't know, say so and suggest who to ask.
- Keep answers concise (2-4 sentences when possible). Use plain language.
- Class meets MW 5:30-6:45 PM, Fall 2026.

COURSE KNOWLEDGE BASE:
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

UVU_GREEN = "#275d38"

CHAT_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AI Teaching Assistant — CS 4720R</title>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
<style>
  *{margin:0;padding:0;box-sizing:border-box}
  body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#f0f2f5;height:100vh;display:flex;flex-direction:column}
  .header{background:#275d38;color:#fff;padding:16px 24px;display:flex;align-items:center;gap:12px;box-shadow:0 2px 8px rgba(0,0,0,.15)}
  .header i{font-size:24px} .header h1{font-size:18px;font-weight:600} .header .sub{font-size:12px;opacity:.85;margin-top:2px}
  .chat{flex:1;overflow-y:auto;padding:20px;display:flex;flex-direction:column;gap:12px}
  .msg{max-width:85%;padding:12px 16px;border-radius:16px;font-size:15px;line-height:1.6;word-wrap:break-word;animation:fi .3s}
  @keyframes fi{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:translateY(0)}}
  .assistant{background:#fff;color:#333;align-self:flex-start;border:1px solid #e0e0e0;border-bottom-left-radius:4px}
  .user{background:#275d38;color:#fff;align-self:flex-end;border-bottom-right-radius:4px}
  .assistant strong{color:#275d38} .assistant a{color:#275d38}
  .typing{align-self:flex-start;background:#fff;border:1px solid #e0e0e0;padding:12px 20px;border-radius:16px;border-bottom-left-radius:4px}
  .typing span{display:inline-block;width:8px;height:8px;background:#999;border-radius:50%;animation:b 1.4s infinite ease-in-out;margin:0 2px}
  .typing span:nth-child(2){animation-delay:.2s} .typing span:nth-child(3){animation-delay:.4s}
  @keyframes b{0%,80%,100%{transform:scale(0)}40%{transform:scale(1)}}
  .inp{background:#fff;padding:16px 20px;border-top:1px solid #e0e0e0;display:flex;gap:10px}
  .inp input{flex:1;padding:12px 16px;border:2px solid #e0e0e0;border-radius:24px;font-size:15px;outline:none;transition:border-color .2s}
  .inp input:focus{border-color:#275d38}
  .inp button{background:#275d38;color:#fff;border:none;border-radius:50%;width:44px;height:44px;cursor:pointer;font-size:18px;transition:background .2s;display:flex;align-items:center;justify-content:center}
  .inp button:hover{background:#1a3d24} .inp button:disabled{background:#999;cursor:not-allowed}
  .welcome{text-align:center;padding:40px 20px;color:#666}
  .welcome h2{color:#275d38;margin-bottom:8px}
  .chips{display:flex;flex-wrap:wrap;gap:8px;justify-content:center;margin-top:20px}
  .chip{background:#e8f5e9;color:#275d38;border:1px solid #275d38;padding:8px 16px;border-radius:20px;cursor:pointer;font-size:13px;transition:background .2s}
  .chip:hover{background:#275d38;color:#fff}
  .ft{text-align:center;padding:8px;font-size:11px;color:#999;background:#f0f2f5}
</style>
</head>
<body>
<div class="header">
  <i class="fas fa-robot"></i>
  <div><h1>AI Teaching Assistant</h1><div class="sub">CS 4720R: AI Business & Tech Solutions — Fall 2026</div></div>
</div>
<div class="chat" id="chat">
  <div class="welcome" id="welcome">
    <h2><i class="fas fa-graduation-cap"></i> Hi! I'm your AI TA.</h2>
    <p>I can help with course questions, due dates, policies, EdTech ideas, and more.<br>I won't do your assignments — but I'll help you think through them.</p>
    <div class="chips">
      <div class="chip" onclick="askQ(this)">When is Demo Day?</div>
      <div class="chip" onclick="askQ(this)">How is my grade calculated?</div>
      <div class="chip" onclick="askQ(this)">What is ZinnStarter?</div>
      <div class="chip" onclick="askQ(this)">Who helps with teacher interviews?</div>
      <div class="chip" onclick="askQ(this)">What is a Lean Canvas?</div>
      <div class="chip" onclick="askQ(this)">Help me brainstorm EdTech problems</div>
    </div>
  </div>
</div>
<div class="inp">
  <input type="text" id="input" placeholder="Ask me anything about CS 4720R..." autocomplete="off" onkeydown="if(event.key==='Enter')send()">
  <button id="btn" onclick="send()"><i class="fas fa-paper-plane"></i></button>
</div>
<div class="ft">Powered by OpenAI &middot; Utah Valley University &middot; Not a substitute for your instructors</div>
<script>
let msgs=[];
const chat=document.getElementById('chat'),input=document.getElementById('input'),btn=document.getElementById('btn');
function askQ(el){input.value=el.textContent;send()}
function addMsg(role,text){
  const w=document.getElementById('welcome');if(w)w.remove();
  const d=document.createElement('div');d.className='msg '+role;d.innerHTML=text.replace(/\\n/g,'<br>');
  chat.appendChild(d);chat.scrollTop=chat.scrollHeight;
}
function showTyping(){const d=document.createElement('div');d.className='typing';d.id='typ';d.innerHTML='<span></span><span></span><span></span>';chat.appendChild(d);chat.scrollTop=chat.scrollHeight}
function hideTyping(){const t=document.getElementById('typ');if(t)t.remove()}
async function send(){
  const q=input.value.trim();if(!q)return;
  input.value='';btn.disabled=true;addMsg('user',q);showTyping();
  msgs.push({role:'user',content:q});
  try{
    const res=await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({messages:msgs})});
    const data=await res.json();hideTyping();
    if(data.error){addMsg('assistant','⚠️ '+data.error)}
    else{msgs.push({role:'assistant',content:data.reply});addMsg('assistant',data.reply)}
  }catch(e){hideTyping();addMsg('assistant','⚠️ Connection error. Please try again.')}
  btn.disabled=false;input.focus();
}
</script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
async def chat_page():
    return CHAT_HTML


@app.post("/api/chat")
async def chat_api(request: Request):
    if not client:
        return JSONResponse(
            {"error": "AI TA is not configured yet. Please contact Prof. Memari (MJ)."},
            status_code=503,
        )

    body = await request.json()
    user_messages = body.get("messages", [])

    if not user_messages:
        return JSONResponse({"error": "Please type a question."}, status_code=400)

    # Keep only last 10 messages for context window efficiency
    recent = user_messages[-10:]

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": SYSTEM_PROMPT}] + recent,
            max_tokens=500,
            temperature=0.3,
        )
        reply = response.choices[0].message.content
        return {"reply": reply}

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/health")
async def health():
    return {"status": "ok", "openai_configured": client is not None, "model": "gpt-4o-mini"}
