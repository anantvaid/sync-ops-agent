from google.adk.agents import Agent, SequentialAgent
from google.adk.tools import FunctionTool
from google.cloud import firestore
import requests, os, json, datetime, logging

logger = logging.getLogger(__name__)

db = firestore.Client()

def save_meeting_to_firestore(summary: str, action_items: list) -> dict:
    """Saves meeting summary and action items to Firestore."""
    try:
        doc = {
            "summary": summary,
            "action_items": action_items,
            "created_at": datetime.datetime.utcnow().isoformat()
        }
        ref = db.collection("meetings").add(doc)
        doc_id = ref[1].id
        logger.info(f"Saved meeting {doc_id} to Firestore")
        return {"saved": True, "id": doc_id}
    except Exception as e:
        logger.error(f"Firestore save failed: {e}")
        return {"saved": False, "error": str(e)}

def get_meetings_from_firestore(limit: int = 10) -> dict:
    """Retrieves the most recent meeting summaries from Firestore.
    Use this when the user asks about past meetings or history.
    Args:
        limit: number of meetings to return (default 10, max 50)
    """
    try:
        limit = min(limit, 50)
        docs = (
            db.collection("meetings")
            .order_by("created_at", direction="DESCENDING")
            .limit(limit)
            .stream()
        )
        meetings = []
        for doc in docs:
            data = doc.to_dict()
            data["id"] = doc.id
            meetings.append(data)

        return {"meetings": meetings, "count": len(meetings)}
    except Exception as e:
        logger.error(f"Firestore read failed: {e}")
        return {"meetings": [], "count": 0, "error": str(e)}

def create_linear_ticket(title: str, description: str, assignee_name: str) -> dict:
    """Creates a Linear ticket for a single action item.
    Args:
        title: short ticket title, max 80 characters
        description: detailed description of the task
        assignee_name: full name of the person responsible
    """
    api_key = os.environ.get("LINEAR_API_KEY", "")
    team_id = os.environ.get("LINEAR_TEAM_ID", "")

    if not api_key:
        logger.warning("LINEAR_API_KEY not set — skipping ticket creation")
        return {"success": False, "error": "LINEAR_API_KEY not configured", "title": title}

    if not team_id:
        logger.warning("LINEAR_TEAM_ID not set — skipping ticket creation")
        return {"success": False, "error": "LINEAR_TEAM_ID not configured", "title": title}

    query = """
    mutation CreateIssue($title: String!, $description: String, $teamId: String!) {
      issueCreate(input: {
        title: $title,
        description: $description,
        teamId: $teamId
      }) {
        success
        issue { id title url }
      }
    }
    """
    try:
        response = requests.post(
            "https://api.linear.app/graphql",
            headers={
                "Authorization": api_key,
                "Content-Type": "application/json"
            },
            json={
                "query": query,
                "variables": {
                    "title": title[:80],
                    "description": f"Assigned to: {assignee_name}\n\n{description}",
                    "teamId": team_id
                }
            },
            timeout=10
        )
        response.raise_for_status()
        data = response.json()

        if "errors" in data:
            return {"success": False, "error": data["errors"][0]["message"], "title": title}

        result = data.get("data", {}).get("issueCreate", {})
        return {
            "success": result.get("success", False),
            "title": title,
            "url": result.get("issue", {}).get("url", ""),
            "id": result.get("issue", {}).get("id", "")
        }
    except requests.exceptions.Timeout:
        return {"success": False, "error": "Linear API timed out", "title": title}
    except requests.exceptions.RequestException as e:
        logger.error(f"Linear API error: {e}")
        return {"success": False, "error": str(e), "title": title}

summarizer_agent = Agent(
    name="summarizer",
    model=os.environ.get("MODEL_NAME_PRO", ""),
    instruction="""You are a meeting summarizer. Analyze the transcript carefully.

    If the transcript is too short (under 20 words) or clearly not a meeting, respond:
    {"error": "Transcript too short or invalid", "summary": null, "action_items": []}

    Otherwise extract:
    1. A concise summary (3-5 sentences) covering key decisions and outcomes.
    2. Action items — each must have: task, assignee (use "Unassigned" if unclear), priority (high/medium/low).

    Respond ONLY with valid JSON, no markdown, no explanation:
    {
        "summary": "...",
        "action_items": [
            {"task": "...", "assignee": "...", "priority": "high"}
        ]
    }""",
    generate_content_config={"temperature": 0}
)

ticket_creator_agent = Agent(
    name="ticket_creator",
    model=os.environ.get("MODEL_NAME_FLASH", ""),
    instruction="""You receive structured meeting data with a summary and action items.

For each action item, call create_linear_ticket with:
- title: a clear, concise ticket title (under 80 chars)
- description: the full task detail
- assignee_name: the person's name (or "Unassigned")

After creating all tickets, call save_meeting_to_firestore with the summary and full action items list.

If an action item fails to create a ticket, continue with the rest — do not stop.
Report how many tickets succeeded and how many failed at the end.""",
    tools=[
        FunctionTool(create_linear_ticket),
        FunctionTool(save_meeting_to_firestore),
    ],
)

formatter_agent = Agent(
    name="formatter",
    model=os.environ.get("MODEL_NAME_FLASH", ""),
    instruction="""You produce the final Slack-ready meeting digest.

Format it exactly like this:

*Meeting Summary*
<2-3 sentence summary>

*Action Items*
- [ ] <task> — <assignee> (<priority>) <ticket_url if available>

*Tickets Created*
<X of Y tickets created successfully>

---
_Processed by Meeting Summarizer · <today's date>_

Keep it clean and scannable. If no Linear tickets were created, omit the ticket URLs.""",
)

root_agent = SequentialAgent(
    name="meeting_summarizer",
    description="Summarizes meeting transcripts, extracts action items, creates Linear tickets, and formats a digest.",
    sub_agents=[summarizer_agent, ticket_creator_agent, formatter_agent],
)
