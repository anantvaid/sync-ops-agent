<p align="center">
  <img width="392" height="393" alt="Screenshot 2026-04-04 at 9 50 07 PM" src="https://github.com/user-attachments/assets/d125e7fe-8e62-4a8c-9f9f-05f96c67164e" />
</p>

# SyncOps Agent — AI Meeting Intelligence Agent

> No more post-meeting admin work. Turn raw transcripts into structured summaries, assigned action items, and live Linear tickets in under 60 seconds.

Built with **GCP ADK**, **Gemini 2.5 Pro**, **Gemini 2.5 Flash**, **Cloud Run**, and **Firestore** for the Gen AI Academy APAC Hackathon 2026.

---

## The Problem (And How We Fix It)

Let’s be honest: nobody likes taking meeting notes, and manually transferring action items into issue trackers is pure operational toil. 

**SyncOps** acts as an autonomous AI Technical Program Manager. You just paste in a meeting transcript, and a pipeline of four specialized AI agents takes over. It doesn't just summarize; it actively executes tool calls to provision real, assigned tickets in your Linear workspace. 

* **The Benchmark:** In testing, SyncOps processed a messy 45-minute sprint planning transcript and successfully generated 15 assigned Linear tickets in under a minute.

---

## How It Works (The Architecture)

Under the hood, this uses the GCP Agent Development Kit (`SequentialAgent`) to chain specialized tasks.

```
User Input (ADK UI / REST API)
        │
        ▼
┌─────────────────────────────────────────┐
│         GCP ADK SequentialAgent         │
│                                         │
│  ┌─────────────┐                        │
│  │  Summarizer │ Gemini 2.5 Pro         │
│  │    Agent    │ → structured JSON      │
│  └──────┬──────┘                        │
│         │                               │
│  ┌──────▼──────┐                        │
│  │   Ticket    │ Gemini 2.5 Flash       │
│  │  Creator    │ → Linear GraphQL API   │
│  │    Agent    │ → Firestore save       │
│  └──────┬──────┘                        │
│         │                               │
│  ┌──────▼──────┐                        │
│  │  Formatter  │ Gemini 2.5 Flash       │
│  │    Agent    │ → Slack-ready digest   │
│  └─────────────┘                        │
└─────────────────────────────────────────┘
        │
        ▼
┌───────────────┐    ┌──────────────────┐
│   Firestore   │    │ Linear Workspace │
│  (History)    │    │  (Live tickets)  │
└───────────────┘    └──────────────────┘

*Note: A separate `history_agent` lives alongside this pipeline to query Firestore and answer questions about past meetings.*
```

---

## Meet the Agents

Instead of one massive prompt, SyncOps delegates tasks to specialized agents to reduce hallucinations and improve formatting:

| Agent | Model | Responsibility | Tools |
|-------|-------|---------------|-------|
| `summarizer` | Gemini 2.5 Pro | Reads the transcript, cuts the noise, and extracts concrete decisions and action items | — |
| `ticket_creator` | Gemini 2.5 Flash | The "hands" of the operation. Creates real Linear tickets for every action item | `create_linear_ticket`, `save_meeting_to_firestore` |
| `formatter` | Gemini 2.5 Flash | Produces Slack-ready digest with ticket URLs | — |
| `history_agent` | Gemini 2.5 Flash | Answers queries about past meetings | `get_meetings_from_firestore` |

---

## Tech Stack

I chose this stack specifically for speed, scalability, and native integration with the Google Cloud ecosystem:

- AI Orchestration: GCP ADK (Provides the native multi-agent pipeline and built-in UI).

- The Brains: Gemini 2.5 Pro and Gemini 2.5 Flash via Vertex AI (Powerful model that accurately answers).

- Infrastructure: Google Cloud Run (Serverless, scales to zero, perfectly hosts the ADK UI).

- Database: Firestore Native Mode (No schema migrations needed, perfect for document-shaped JSON meeting data).

- Integrations: Linear GraphQL API.

- Backend: Python 3.12 & FastAPI.

---

## Project Structure

```
meeting-summarizer/
├── meeting_agent/
│   ├── __init__.py        # Exposes agent module to ADK
│   ├── agent.py           # All 4 agents + tools + SequentialAgent root
│   └── .env               # Vertex AI + Linear credentials
├── history_agent/
│   ├── __init__.py
│   ├── agent.py           # History agent with Firestore query tool
│   └── .env
├── main.py                # FastAPI REST layer (GET /meetings)
└── requirements.txt
```

---

## Get It Running Locally

Want to spin this up yourself? Here is how to get the agents running on your machine.

### Prerequisites

- Python 3.12+
- GCP project with billing enabled
- Firestore database (Native mode, us-central1)
- Linear account with a team and personal API key
- `gcloud` CLI installed and authenticated

### 1. Clone and install

```bash
git clone [https://github.com/anantvaid/sync-ops-agent](https://github.com/anantvaid/sync-ops-agent)
cd sync-ops-agent

python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
```

### 2. Configure your environment

```bash
touch meeting_agent/.env
```

Edit `meeting_agent/.env`:

```env
GOOGLE_GENAI_USE_VERTEXAI=TRUE
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=us-central1
LINEAR_API_KEY=lin_api_xxxxxxxxxxxx
LINEAR_TEAM_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
```

Get your Linear team ID:

```bash
curl -X POST https://api.linear.app/graphql \
  -H "Authorization: YOUR_LINEAR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ teams { nodes { id name } } }"}'
```

Copy `.env` to `history_agent/` as well:

```bash
cp meeting_agent/.env history_agent/.env
```

### 3. Authenticate with GCP

```bash
gcloud auth application-default login
gcloud config set project your-project-id
```

### 4. Run locally with ADK UI

```bash
adk web
```

Open the Cloud Shell web preview on port 8000 (or `http://localhost:8000`).
Select `meeting_agent` from the dropdown and paste a transcript.

---

## Deploy to Cloud Run

```bash
adk deploy cloud_run \
  --project=your-project-id \
  --region=us-central1 \
  --with_ui \
  meeting_agent
```

The `--with_ui` flag bundles the ADK visual interface with the deployment.
After deploy, open the public Cloud Run URL in your browser to access the ADK UI.

---

## API Endpoints

Once deployed or running locally via `main.py`:

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Service health check |
| `GET` | `/meetings` | List all past meetings from Firestore |
| `GET` | `/meetings/{id}` | Get a single meeting by Firestore document ID |

```bash
# Health check
curl https://your-cloud-run-url/health

# Get meeting history
curl https://your-cloud-run-url/meetings
```

---

## Demo Transcript

Paste this into the ADK UI to test the full pipeline:

```
Attendees: Rahul, Priya, Sam
We decided to launch the beta on April 15th. Rahul will set up the staging
environment by end of week. Priya needs to write the onboarding docs before
April 10th. Sam will reach out to 5 pilot customers by Monday. We also
agreed to use Linear for task tracking going forward.
```

Expected output: 3 Linear tickets created, structured summary, Slack-ready digest.

---

## Roadmap

This is a prototype built in 7 days. Planned additions for the refinement phase:

- **Linear User ID Mapping** — Action items correctly extract assignee names, but the Linear API requires internal UUIDs for assignment. Implementing a one-time team roster sync to map `String Name` -> `Linear User ID`.
- **Slack webhook** — post digest directly to a Slack channel after every meeting
- **Parallel ticket creation** — switch to ADK ParallelAgent to create all tickets simultaneously (estimated 6x speed improvement)
- **Confidence scoring** — flag action items as high/medium/low confidence based on how explicitly they were stated
- **Vertex AI embeddings** — semantic search across meeting history ("find meetings where we discussed latency")
- **Audio transcript support** — accept audio files, transcribe via Gemini multimodal, pipe through the same pipeline
- **Google Calendar integration** — auto-schedule follow-up meetings from action items with deadlines
- **Jira support** — alternative ticket destination alongside Linear

---

## Hackathon

**Event:** Gen AI Academy APAC Edition 2026
**Team:** Sync-Ops Labs
**Phase:** Prototype Submission (Apr 1–8)

---

## License

MIT
