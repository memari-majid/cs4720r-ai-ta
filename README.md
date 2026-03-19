# CS 4720R AI Teaching Assistant

A chatbot that answers student questions about CS 4720R: AI Business and Tech Solutions using OpenAI's Assistants API, loaded with the full course knowledge base.

## Quick Start (Local)

```bash
cd chatbot/

# 1. Create .env with your OpenAI key
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY

# 2. Install dependencies
pip install -r requirements.txt

# 3. Create the OpenAI Assistant (run once)
python setup_assistant.py
# This prints the ASSISTANT_ID and saves it to .env

# 4. Run the server
uvicorn app:app --reload --port 8000

# 5. Open http://localhost:8000
```

## Deploy to Render (Free)

1. Push the `chatbot/` folder to a GitHub repo (or use the full repo)
2. Go to [render.com](https://render.com) and create a new Web Service
3. Connect the repo, set root directory to `courses/cs4720R/offerings/2026-fall-601/chatbot`
4. Add environment variables: `OPENAI_API_KEY` and `ASSISTANT_ID`
5. Deploy — Render uses the `render.yaml` config automatically

## Update Knowledge Base

If course content changes, re-run the export and update the assistant:

```bash
# From repo root
cd template
python -c "... (run the export script)"

# Then re-run setup to update the assistant
cd ../courses/cs4720R/offerings/2026-fall-601/chatbot
python setup_assistant.py
```

## Cost

Uses `gpt-4o-mini` — approximately $0.01-0.05 per student question.
