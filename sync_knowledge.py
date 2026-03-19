#!/usr/bin/env python3
"""Sync the AI TA knowledge base from live Canvas course content.

Pulls all pages, assignments, discussions, modules, and syllabus from Canvas
and writes a condensed knowledge file that the chatbot loads on startup.

Usage:
    # Manual run (from chatbot/ directory)
    python sync_knowledge.py

    # Runs automatically via GitHub Actions every Monday at 6 AM MT

Requires CANVAS_API_TOKEN env var (or reads from template/.env).
"""

import os
import re
import sys
from pathlib import Path

import requests

CANVAS_URL = "https://uvu.instructure.com"
COURSE_ID = "644965"

def get_token():
    token = os.getenv("CANVAS_API_TOKEN")
    if token:
        return token
    env_path = Path(__file__).parent.parent.parent.parent.parent / "template" / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if line.startswith("CANVAS_API_TOKEN="):
                return line.split("=", 1)[1].strip()
    print("ERROR: No CANVAS_API_TOKEN found.")
    sys.exit(1)


def strip_html(html: str) -> str:
    text = re.sub(r"<[^>]+>", " ", html).strip()
    return re.sub(r"\s+", " ", text)


def sync():
    token = get_token()
    base = f"{CANVAS_URL}/api/v1"
    headers = {"Authorization": f"Bearer {token}"}
    content = []

    print("Syncing from Canvas...")

    # Syllabus
    r = requests.get(f"{base}/courses/{COURSE_ID}", headers=headers, params={"include[]": "syllabus_body"}, timeout=30)
    syl = strip_html(r.json().get("syllabus_body", ""))
    content.append(f"SYLLABUS:\n{syl[:5000]}")
    print(f"  Syllabus: {len(syl)} chars")

    # Assignments
    r = requests.get(f"{base}/courses/{COURSE_ID}/assignments?per_page=100", headers=headers, timeout=30)
    assignments = r.json()
    content.append("\nASSIGNMENTS:")
    for a in sorted(assignments, key=lambda x: x.get("due_at") or ""):
        desc = strip_html(a.get("description", "") or "")[:400]
        content.append(f"\n{a['name']} | {a.get('points_possible',0)} pts | due: {(a.get('due_at') or 'TBD')[:10]}\n{desc}")
    print(f"  Assignments: {len(assignments)}")

    # Modules with items
    r = requests.get(f"{base}/courses/{COURSE_ID}/modules?per_page=50", headers=headers, timeout=30)
    modules = r.json()
    content.append("\nMODULES:")
    for m in modules:
        r2 = requests.get(f"{base}/courses/{COURSE_ID}/modules/{m['id']}/items?per_page=20", headers=headers, timeout=30)
        items = r2.json()
        item_list = ", ".join(it.get("title", "")[:50] for it in items[:5])
        content.append(f"- {m['name']}: {item_list}")
    print(f"  Modules: {len(modules)}")

    # Discussions
    r = requests.get(f"{base}/courses/{COURSE_ID}/discussion_topics?per_page=50", headers=headers, timeout=30)
    discussions = r.json()
    content.append("\nDISCUSSIONS:")
    for d in sorted(discussions, key=lambda x: x["title"]):
        msg = strip_html(d.get("message", "") or "")[:200]
        content.append(f"- {d['title']}: {msg}")
    print(f"  Discussions: {len(discussions)}")

    # Key pages
    for slug in ["faq", "start-here", "technical-requirements", "instructor-information"]:
        r = requests.get(f"{base}/courses/{COURSE_ID}/pages/{slug}", headers=headers, timeout=30)
        if r.status_code == 200:
            text = strip_html(r.json().get("body", "") or "")[:2000]
            content.append(f"\n{slug.upper().replace('-', ' ')}:\n{text}")
    print("  Key pages: 4")

    # Announcements (latest 5)
    r = requests.get(f"{base}/courses/{COURSE_ID}/discussion_topics?only_announcements=true&per_page=5", headers=headers, timeout=30)
    announcements = r.json() if isinstance(r.json(), list) else []
    if announcements:
        content.append("\nRECENT ANNOUNCEMENTS:")
        for a in announcements:
            msg = strip_html(a.get("message", "") or "")[:300]
            posted = (a.get("posted_at") or "")[:10]
            content.append(f"- [{posted}] {a['title']}: {msg}")
        print(f"  Announcements: {len(announcements)}")

    # Assignment groups (grading weights)
    r = requests.get(f"{base}/courses/{COURSE_ID}/assignment_groups?per_page=50", headers=headers, timeout=30)
    content.append("\nGRADING WEIGHTS:")
    for g in sorted(r.json(), key=lambda x: -x.get("group_weight", 0)):
        content.append(f"- {g['name']}: {g.get('group_weight', 0)}%")

    # Schedule from local file
    schedule_path = Path(__file__).parent.parent / "SCHEDULE.md"
    if schedule_path.exists():
        content.append(f"\nSCHEDULE:\n{schedule_path.read_text()[:5000]}")
        print("  Schedule: loaded from SCHEDULE.md")

    # Policies
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

    result = "\n".join(content)
    out_path = Path(__file__).parent / "knowledge_condensed.txt"
    out_path.write_text(result, encoding="utf-8")

    print(f"\nKnowledge base updated: {len(result)} chars ({len(result.split())} words)")
    print(f"Saved to: {out_path}")
    return result


if __name__ == "__main__":
    sync()
