#!/usr/bin/env python3
"""Create (or update) the OpenAI Assistant for CS 4720R AI TA.

Run once after setting OPENAI_API_KEY in .env:
    python setup_assistant.py

The script prints the ASSISTANT_ID to add to your .env file.
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

KNOWLEDGE_FILE = Path(__file__).parent.parent / "materials" / "ai_ta_knowledge_base.txt"

SYSTEM_PROMPT = """\
You are the AI Teaching Assistant for CS 4720R: AI Business and Tech Solutions at Utah Valley University (Fall 2026).

This is an innovation and entrepreneurship course focused on Education Technology (EdTech). Students — from both Computer Science and the School of Education — discover real problems in K-12 and higher education, build AI-powered prototypes using no-code tools (n8n, cloud-hosted), and pitch their EdTech startup at Demo Day.

YOUR ROLE:
- Answer course logistics questions (due dates, grading, policies, tools, schedule).
- Explain EdTech and entrepreneurship concepts at a non-technical, beginner-friendly level.
- Help students brainstorm EdTech problems and solution ideas.
- Direct students to the right person:
  • Prof. Memari (MJ) — AI prototyping, n8n, technical help, grading → mmemari@uvu.edu
  • Prof. Ruggles — Education problems, teacher interviews, EdTech validation → KRuggles@uvu.edu
  • Alessandra Camargo / BEI — Mentoring, pitch coaching, ZinnStarter, VentureCon → entrepreneurship@uvu.edu, KB 102
- Point students to BEI resources: https://www.uvu.edu/woodbury/entrepreneurship/

RULES:
- NEVER do assignments, write pitches, or generate deliverables for students. Help them think, don't think for them.
- When answering about policies, grading, or due dates, cite the syllabus or specific course page.
- If you don't know something, say so and suggest who to ask.
- Keep answers concise and friendly. Use plain language — many students have no technical background.
- Class meets MW 5:30–6:45 PM, Fall 2026.

COURSE TEAM:
- Majid (MJ) Memari — Instructor (Computer Science). Office: SE 407J. Phone: (801) 863-5912. Office Hours: MW 1:00–3:30 PM via Canvas & Teams.
- Krista Ruggles — Subject Matter Expert (School of Education). Office: ME 112E / MS 126. Phone: (801) 863-8057.
- Alessandra Camargo — Associate Director, Baugh Entrepreneurship Institute (BEI). Office: KB 102. Phone: (801) 863-5354.

Use the attached knowledge base file for detailed course content, schedule, assignments, and policies.
"""


def main():
    print("Uploading knowledge base...")
    with open(KNOWLEDGE_FILE, "rb") as f:
        file = client.files.create(file=f, purpose="assistants")
    print(f"  File ID: {file.id}")

    print("Creating assistant...")
    assistant = client.beta.assistants.create(
        name="CS 4720R AI Teaching Assistant",
        instructions=SYSTEM_PROMPT,
        model="gpt-4.1",
        tools=[{"type": "file_search"}],
        tool_resources={"file_search": {"vector_stores": [{"file_ids": [file.id]}]}},
    )

    print(f"\nAssistant created successfully!")
    print(f"  Assistant ID: {assistant.id}")
    print(f"\nAdd this to your .env file:")
    print(f"  ASSISTANT_ID={assistant.id}")

    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        content = env_path.read_text()
        if "ASSISTANT_ID=" in content:
            lines = content.splitlines()
            lines = [l if not l.startswith("ASSISTANT_ID=") else f"ASSISTANT_ID={assistant.id}" for l in lines]
            env_path.write_text("\n".join(lines) + "\n")
        else:
            with open(env_path, "a") as f:
                f.write(f"ASSISTANT_ID={assistant.id}\n")
    else:
        env_path.write_text(f"OPENAI_API_KEY={os.getenv('OPENAI_API_KEY')}\nASSISTANT_ID={assistant.id}\n")

    print(f"  .env updated automatically.")


if __name__ == "__main__":
    main()
